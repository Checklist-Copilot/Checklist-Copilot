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
from app.services.checklists import (
    apply_stats,
    create_checklist_for_user,
    get_checklist_for_user,
)
from app.services.files import (
    build_file_url,
    extract_pdf_text,
    fetch_file_bytes,
    get_file_for_user,
    get_pdf_files_for_checklist,
)


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
    print(f"\n{'='*60}")
    print(f"[PDF PIPELINE] START — checklist: {checklist_id}")
    print(f"[PDF PIPELINE] Found {len(pdf_files)} PDF file(s)")
    print(f"{'='*60}")
    pdf_texts: list[str] = []
    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            raw_bytes, _ = await fetch_file_bytes(pdf_file)
            text = extract_pdf_text(raw_bytes)
            print(f"\n[STEP 1 — PDF {i}/{len(pdf_files)}] file_id={pdf_file.id} | {len(text)} chars")
            print(f"[STEP 1 — PDF {i}/{len(pdf_files)}] --- TEXT START ---")
            print(text)
            print(f"[STEP 1 — PDF {i}/{len(pdf_files)}] ---- TEXT END ----")
            if text.strip():
                pdf_texts.append(f"[Document {i}]\n{text}")
        except Exception as exc:
            print(f"[STEP 1 — PDF {i}/{len(pdf_files)}] ERROR for {pdf_file.id}: {exc}")

    combined_pdf_text = "\n\n---\n\n".join(pdf_texts)
    print(f"\n[PDF PIPELINE] Combined: {len(combined_pdf_text)} chars from {len(pdf_texts)} document(s)")

    # Only run AI generation when PDF text was actually extracted.
    # If no PDFs were uploaded (or all failed to extract), leave the checklist empty.
    if not combined_pdf_text.strip():
        print("[PDF PIPELINE] No PDF text available — skipping generation")
        return ChecklistResponse.model_validate(checklist)

    try:
        result = generate_checklist_from_pdf(
            combined_pdf_text,
            title=checklist.title,
            description=checklist.description,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    from sqlalchemy.orm.attributes import flag_modified
    checklist.checklist = result.checklist
    flag_modified(checklist, "checklist")
    apply_stats(checklist)
    db.commit()
    db.refresh(checklist)

    print(f"[PDF PIPELINE] Saved checklist with {len(result.checklist.get('children') or [])} top-level children")
    return ChecklistResponse.model_validate(checklist)


@router.post("/{checklist_id}/debug-pdf", response_model=dict)
async def ai_debug_pdf_pipeline(
    checklist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    TEMPORARY DEBUG endpoint. Shows every step of the PDF pipeline:
    1. Raw extracted PDF text
    2. Phase-1 JSON (sections + items from AI)
    3. Phase-2 result (final checklist tree + applied/skipped calls)
    """
    from app.services.ai.service import extract_checklist_structure_from_pdf

    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")

    pdf_files = get_pdf_files_for_checklist(db, checklist_id)
    if not pdf_files:
        return {"error": "No PDF files found for this checklist."}

    pdf_texts: list[str] = []
    pdf_meta: list[dict] = []
    for pdf_file in pdf_files:
        try:
            raw_bytes, _ = await fetch_file_bytes(pdf_file)
            text = extract_pdf_text(raw_bytes)
            pdf_texts.append(text)
            pdf_meta.append({"file_id": str(pdf_file.id), "chars": len(text), "preview": text[:500]})
        except Exception as exc:
            pdf_meta.append({"file_id": str(pdf_file.id), "error": str(exc)})

    combined_pdf_text = "\n\n---\n\n".join(pdf_texts)

    phase1 = extract_checklist_structure_from_pdf(combined_pdf_text) if combined_pdf_text.strip() else {}

    from app.services.ai.service import generate_checklist_from_pdf
    result = generate_checklist_from_pdf(
        combined_pdf_text,
        title=checklist.title,
        description=checklist.description,
    ) if combined_pdf_text.strip() else None

    return {
        "step1_pdf_extraction": pdf_meta,
        "step2_phase1_ai_structure": phase1,
        "step3_phase2_result": {
            "applied_calls": result.applied_calls if result else 0,
            "skipped_calls": result.skipped_calls if result else [],
            "checklist_children_count": len((result.checklist.get("children") or [])) if result else 0,
            "checklist": result.checklist if result else {},
        },
    }


def _infer_title(checklist: dict, prompt: str) -> str:
    """Pick a reasonable title if the user didn't supply one."""
    # First top-level section label, or a slug of the prompt.
    for child in checklist.get("children", []):
        if isinstance(child, dict) and child.get("type") == "section":
            label = child.get("label")
            if isinstance(label, str) and label.strip():
                return label.strip()
    return prompt[:60].strip() or "AI-generated checklist"
