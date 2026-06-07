import base64
import copy
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.ai import (
    AiCreateFromTextRequest,
    AiEditChecklistRequest,
    AiObserveRequest,
    AiResponse,
    AiSkippedCall,
)
from app.schemas.checklist import ChecklistCreateRequest, ChecklistCreateResponse
from app.services.ai.service import (
    edit_checklist_with_ai,
    generate_checklist_from_text,
    observe_with_image,
)
from app.services.auth import get_current_user
from app.services.checklists import (
    apply_stats,
    create_checklist_for_user,
    get_checklist_for_user,
)
from app.services.files import build_file_url, fetch_file_bytes, get_file_for_user


router = APIRouter(prefix="/ai/checklists")


@router.post(
    "/create-from-text",
    response_model=ChecklistCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def ai_create_from_text(
    payload: AiCreateFromTextRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistCreateResponse:
    try:
        result = generate_checklist_from_text(
            payload.prompt,
            title=payload.title,
            description=payload.description,
        )
    except RuntimeError as exc:
        # OPENAI_API_KEY missing, openai SDK missing, etc.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    # Persist via the normal checklist service so ownership + timestamps are consistent.
    # Title precedence: explicit request > AI-proposed > heuristic from tree/prompt.
    create_payload = ChecklistCreateRequest(
        title=(
            payload.title
            or result.proposed_title
            or _infer_title(result.checklist, payload.prompt)
        ),
        description=payload.description or result.proposed_description,
        checklist=result.checklist,
    )
    checklist = create_checklist_for_user(db, current_user.id, create_payload)
    return ChecklistCreateResponse.model_validate(checklist)


@router.post("/{checklist_id}/edit", response_model=AiResponse)
def ai_edit_checklist(
    checklist_id: uuid.UUID,
    payload: AiEditChecklistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found."
        )

    # Work on a detached copy. The checklist update helpers mutate nested dicts/lists
    # in place, and SQLAlchemy JSONB columns do not reliably detect those in-place
    # mutations. Keeping a separate original snapshot also makes undo correct.
    original_checklist = copy.deepcopy(checklist.checklist)
    working_checklist = copy.deepcopy(checklist.checklist)

    try:
        result = edit_checklist_with_ai(
            working_checklist,
            payload.instruction,
            current_title=checklist.title,
            current_description=checklist.description,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    # Snapshot for undo, then save the AI-modified JSON. We persist when EITHER
    # the tree changed OR the AI proposed metadata changes (e.g. setting a
    # title via `update_checklist_metadata`); pure text replies leave the row
    # untouched.
    tree_changed = result.checklist != original_checklist
    metadata_changed = (
        result.proposed_title is not None or result.proposed_description is not None
    )
    if tree_changed or metadata_changed:
        if tree_changed:
            checklist.checklist_prev = original_checklist
            checklist.checklist = result.checklist
        if result.proposed_title:
            checklist.title = result.proposed_title
        if result.proposed_description is not None:
            checklist.description = result.proposed_description or None
        # Recompute denormalized completion stats so the dashboard reflects the
        # post-edit state without re-reading the JSON.
        apply_stats(checklist)
        db.commit()
        db.refresh(checklist)

    return AiResponse(
        checklist=result.checklist,
        title=checklist.title,
        description=checklist.description,
        reply=result.reply,
        applied_calls=result.applied_calls,
        skipped=[AiSkippedCall(**s) for s in result.skipped_calls],
    )


@router.post("/{checklist_id}/observe", response_model=AiResponse)
async def ai_observe(
    checklist_id: uuid.UUID,
    payload: AiObserveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiResponse:
    """
    Vision flow. The user has already uploaded an image (POST /files/upload/image)
    and passes the resulting image_id here along with a natural-language
    instruction or question. The AI sees the image + the checklist and can:

    - reply in text only (e.g. "Yes, I see 4 screws installed"), OR
    - call `add_image_to_block` to attach the image to a specific imageBlock —
      the server appends the new entry to that block's `images` array and
      persists the checklist (with `checklist_prev` snapshotted for undo).

    If the user rejects the image afterwards, they call DELETE /api/files/{id}
    to remove the unused upload from Supabase Storage.
    """
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found."
        )

    # Resolve the uploaded image; enforces ownership via user_id.
    try:
        image_uuid = uuid.UUID(str(payload.image_id))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="image_id must be a UUID."
        ) from exc

    file_row = get_file_for_user(db, image_uuid, current_user.id)
    if file_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found."
        )
    if not (file_row.file_type or "").startswith("image"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referenced file is not an image.",
        )

    # Fetch bytes from Supabase and re-encode as a data URL for the OpenAI vision call.
    raw_bytes, content_type = await fetch_file_bytes(file_row)
    image_data_url = f"data:{content_type};base64,{base64.b64encode(raw_bytes).decode('ascii')}"
    image_url = build_file_url(file_row.id)

    prior = [m.model_dump() for m in (payload.prior_messages or [])]

    try:
        result = observe_with_image(
            checklist.checklist,
            payload.instruction,
            image_id=str(file_row.id),
            image_url=image_url,
            image_data_url=image_data_url,
            prior_messages=prior,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    # Persist only if the model actually changed something (an attach happened).
    # Pure text replies don't mutate the checklist, so no need to snapshot.
    if result.applied_calls > 0:
        checklist.checklist_prev = checklist.checklist
        checklist.checklist = result.checklist
        if result.proposed_title:
            checklist.title = result.proposed_title
        if result.proposed_description is not None:
            checklist.description = result.proposed_description or None
        apply_stats(checklist)
        db.commit()
        db.refresh(checklist)

    return AiResponse(
        checklist=result.checklist,
        title=checklist.title,
        description=checklist.description,
        reply=result.reply,
        applied_calls=result.applied_calls,
        skipped=[AiSkippedCall(**s) for s in result.skipped_calls],
    )


def _infer_title(checklist: dict, prompt: str) -> str:
    """Pick a reasonable title if the user didn't supply one."""
    # First top-level section label, or a slug of the prompt.
    for child in checklist.get("children", []):
        if isinstance(child, dict) and child.get("type") == "section":
            label = child.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()
    return prompt[:60].strip() or "AI-generated checklist"
