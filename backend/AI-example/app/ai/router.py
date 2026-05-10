from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.schemas import AiEditChecklistRequest, AiCreateFromTextRequest
from app.ai.service import edit_checklist_with_ai, create_checklist_from_text
from app.auth.service import get_current_user
from app.db.models import User
from app.db.session import get_db


router = APIRouter()


@router.post("/checklists/{checklist_id}/edit")
def ai_edit_checklist(
    checklist_id: int,
    payload: AiEditChecklistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return edit_checklist_with_ai(
        db=db,
        checklist_id=checklist_id,
        user_id=current_user.id,
        instruction=payload.instruction,
    )


@router.post("/checklists/create-from-text")
def ai_create_checklist_from_text(
    payload: AiCreateFromTextRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_checklist_from_text(
        db=db,
        user_id=current_user.id,
        text=payload.text,
    )
