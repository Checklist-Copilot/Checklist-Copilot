import base64
import copy
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.ai import (
    AiCreateFromTextRequest,
    AiEditChecklistRequest,
    AiGenerateRequest,
    AiObserveRequest,
    AiResponse,
    AiSkippedCall,
)
from app.schemas.checklist import ChecklistCreateRequest, ChecklistCreateResponse, ChecklistResponse
from app.services.ai.service import (
    edit_checklist_with_ai,
    generate_checklist_from_pdf,
    generate_checklist_from_text,
    observe_with_image,
)
from app.services.auth import get_current_user
from app.services.checklist_update.exceptions import ChecklistOperationError
from app.services.checklists import (
    apply_stats,
    create_checklist_for_user,
    get_checklist_for_user,
)
from app.services.files import (
    build_file_url,
    fetch_file_bytes,
    get_file_for_user,
    get_pdf_files_for_checklist,
)

logger = logging.getLogger(__name__)

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
    create_payload = ChecklistCreateRequest(
        title=payload.title or _infer_title(result.checklist, payload.prompt),
        description=payload.description,
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
        result = edit_checklist_with_ai(working_checklist, payload.instruction)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    # Snapshot for undo, then save the AI-modified JSON. If the model only replied
    # without applying a structural/value change, leave the DB row untouched.
    if result.checklist != original_checklist:
        checklist.checklist_prev = original_checklist
        checklist.checklist = result.checklist
        apply_stats(checklist)
        db.commit()
        db.refresh(checklist)

    return AiResponse(
        checklist=result.checklist,
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

    original_checklist = copy.deepcopy(checklist.checklist)
    working_checklist = copy.deepcopy(checklist.checklist)

    try:
        result = observe_with_image(
            working_checklist,
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

    # Persist only if the model actually changed the checklist.
    # Pure text replies don't mutate the checklist, so no need to snapshot.
    if result.checklist != original_checklist:
        checklist.checklist_prev = original_checklist
        checklist.checklist = result.checklist
        apply_stats(checklist)
        db.commit()
        db.refresh(checklist)

    return AiResponse(
        checklist=result.checklist,
        reply=result.reply,
        applied_calls=result.applied_calls,
        skipped=[AiSkippedCall(**s) for s in result.skipped_calls],
    )


@router.post("/{checklist_id}/generate", response_model=ChecklistResponse)
async def ai_generate_from_pdfs(
    checklist_id: uuid.UUID,
    payload: AiGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistResponse:
    """
    Generate checklist content for an existing (empty) checklist using the
    description as a prompt and any uploaded PDFs as context. Called right
    after checklist creation + PDF upload from the New Checklist page.
    """
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found."
        )

    pdf_files = get_pdf_files_for_checklist(db, checklist_id)
    logger.info("Starting PDF checklist generation for checklist=%s, %d PDF(s)", checklist_id, len(pdf_files))

    attachments: list[tuple[str, bytes]] = []
    for pdf_file in pdf_files:
        try:
            raw_bytes, _ = await fetch_file_bytes(pdf_file)
            attachments.append((pdf_file.file_name, raw_bytes))
        except Exception:
            logger.exception("Failed to fetch PDF bytes for file_id=%s", pdf_file.id)

    # Only run AI generation when at least one PDF was successfully fetched.
    # If no PDFs were uploaded (or all failed to fetch), leave the checklist empty.
    if not attachments:
        logger.info("No PDF attachments available — skipping generation")
        return ChecklistResponse.model_validate(checklist)

    try:
        result = generate_checklist_from_pdf(
            attachments,
            title=checklist.title,
            description=checklist.description,
            prompt=payload.prompt,
        )
    except (RuntimeError, ValueError, ChecklistOperationError) as exc:
        logger.exception("PDF checklist generation failed for checklist=%s", checklist_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    from sqlalchemy.orm.attributes import flag_modified
    checklist.checklist = result.checklist
    flag_modified(checklist, "checklist")
    apply_stats(checklist)
    db.commit()
    db.refresh(checklist)

    logger.info(
        "Saved generated checklist=%s with %d top-level children",
        checklist_id,
        len(result.checklist.get("children") or []),
    )
    return ChecklistResponse.model_validate(checklist)


def _infer_title(checklist: dict, prompt: str) -> str:
    """Pick a reasonable title if the user didn't supply one."""
    # First top-level section label, or a slug of the prompt.
    for child in checklist.get("children", []):
        if isinstance(child, dict) and child.get("type") == "section":
            label = child.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()
    return prompt[:60].strip() or "AI-generated checklist"
