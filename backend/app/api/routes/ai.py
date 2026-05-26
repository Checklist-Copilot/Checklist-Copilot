import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.ai import (
    AiCreateFromTextRequest,
    AiEditChecklistRequest,
    AiResponse,
    AiSkippedCall,
)
from app.schemas.checklist import ChecklistCreateRequest, ChecklistCreateResponse
from app.services.ai.service import (
    edit_checklist_with_ai,
    generate_checklist_from_text,
)
from app.services.auth import get_current_user
from app.services.checklists import (
    create_checklist_for_user,
    get_checklist_for_user,
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

    try:
        result = edit_checklist_with_ai(checklist.checklist, payload.instruction)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    # Snapshot for undo, then save the AI-modified JSON.
    checklist.checklist_prev = checklist.checklist
    checklist.checklist = result.checklist
    db.commit()
    db.refresh(checklist)

    return AiResponse(
        checklist=result.checklist,
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
