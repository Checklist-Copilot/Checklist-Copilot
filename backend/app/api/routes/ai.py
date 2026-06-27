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
    AiReviewResponse,
    AiSkippedCall,
)
from app.schemas.checklist import ChecklistCreateRequest, ChecklistCreateResponse, ChecklistResponse
from app.services.ai.service import (
    edit_checklist_with_ai,
    generate_checklist_from_text,
    generate_checklist_with_context,
    observe_with_image,
    review_checklist_with_ai,
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
    load_pdf_attachments_for_checklist,
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

    logger.info(
        "AI edit completed: checklist_id=%s applied_calls=%s skipped_calls=%s raw_tool_calls=%s reply=%r changed=%s",
        checklist_id,
        result.applied_calls,
        result.skipped_calls,
        result.raw_tool_calls,
        result.reply,
        result.checklist != original_checklist,
    )

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


@router.post("/{checklist_id}/review", response_model=AiReviewResponse)
async def ai_review_checklist(
    checklist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AiReviewResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found."
        )

    try:
        attachments = await load_pdf_attachments_for_checklist(db, checklist_id, current_user.id)
        reply = review_checklist_with_ai(checklist.checklist, pdf_files=attachments)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return AiReviewResponse(reply=reply or "I could not produce a review for this checklist.")


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

    image_ids = list(payload.image_ids or [])
    if payload.image_id is not None:
        image_ids.insert(0, payload.image_id)
    if not image_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image_id is required.",
        )

    prior = [m.model_dump() for m in (payload.prior_messages or [])]
    original_checklist = copy.deepcopy(checklist.checklist)
    working_checklist = copy.deepcopy(checklist.checklist)
    replies: list[str] = []
    applied_calls = 0
    skipped_calls: list[dict] = []

    try:
        for index, raw_image_id in enumerate(image_ids, start=1):
            try:
                image_uuid = uuid.UUID(str(raw_image_id))
            except (ValueError, TypeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"image_ids[{index - 1}] must be a UUID.",
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
            per_image_instruction = (
                f"Image {index} of {len(image_ids)}. {payload.instruction}"
                if len(image_ids) > 1
                else payload.instruction
            )

            result = observe_with_image(
                working_checklist,
                per_image_instruction,
                image_id=str(file_row.id),
                image_url=image_url,
                image_data_url=image_data_url,
                prior_messages=prior,
            )
            working_checklist = result.checklist
            applied_calls += result.applied_calls
            skipped_calls.extend(result.skipped_calls)
            if result.reply:
                replies.append(f"Image {index}: {result.reply}" if len(image_ids) > 1 else result.reply)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    # Persist only if the model actually changed the checklist.
    # Pure text replies don't mutate the checklist, so no need to snapshot.
    if working_checklist != original_checklist:
        checklist.checklist_prev = original_checklist
        checklist.checklist = working_checklist
        apply_stats(checklist)
        db.commit()
        db.refresh(checklist)

    return AiResponse(
        checklist=working_checklist,
        reply="\n\n".join(replies) or "Processed the uploaded image.",
        applied_calls=applied_calls,
        skipped=[AiSkippedCall(**s) for s in skipped_calls],
    )


@router.post("/{checklist_id}/generate", response_model=ChecklistResponse)
async def ai_generate_with_context(
    checklist_id: uuid.UUID,
    payload: AiGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistResponse:
    """
    Generate checklist content for an existing empty checklist using the user's
    prompt plus any uploaded PDFs as additional context.
    """
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found."
        )

    if checklist.checklist.get("children"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checklist generation can only run for an empty checklist.",
        )

    try:
        attachments = await load_pdf_attachments_for_checklist(db, checklist_id, current_user.id)
        logger.info("Starting checklist generation for checklist=%s, %d PDF(s)", checklist_id, len(attachments))
        result = generate_checklist_with_context(
            payload.prompt,
            title=checklist.title,
            description=checklist.description,
            pdf_files=attachments,
        )
    except (RuntimeError, ValueError, ChecklistOperationError) as exc:
        logger.exception("Checklist generation failed for checklist=%s", checklist_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    from sqlalchemy.orm.attributes import flag_modified
    checklist.checklist_prev = copy.deepcopy(checklist.checklist)
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
