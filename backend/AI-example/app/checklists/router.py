from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import get_current_user
from app.checklists.schemas import (
    ChecklistCreateRequest,
    ChecklistUpdateRequest,
    ChecklistResponse,
)
from app.checklists.service import (
    list_user_checklists,
    get_user_checklist,
    create_user_checklist,
    update_user_checklist,
    delete_user_checklist,
    undo_last_change,
)
from app.db.models import User
from app.db.session import get_db


router = APIRouter()


@router.get("/", response_model=list[ChecklistResponse])
def list_checklists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_user_checklists(db, current_user.id)


@router.post("/", response_model=ChecklistResponse)
def create_checklist(
    payload: ChecklistCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_user_checklist(
        db,
        user_id=current_user.id,
        title=payload.title,
        data=payload.data,
    )


@router.get("/{checklist_id}", response_model=ChecklistResponse)
def get_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_checklist(db, checklist_id, current_user.id)


@router.put("/{checklist_id}", response_model=ChecklistResponse)
def update_checklist(
    checklist_id: int,
    payload: ChecklistUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_user_checklist(
        db,
        checklist_id=checklist_id,
        user_id=current_user.id,
        title=payload.title,
        data=payload.data,
    )


@router.delete("/{checklist_id}")
def delete_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_user_checklist(db, checklist_id, current_user.id)
    return {"status": "deleted"}


@router.post("/{checklist_id}/undo", response_model=ChecklistResponse)
def undo_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return undo_last_change(db, checklist_id, current_user.id)
