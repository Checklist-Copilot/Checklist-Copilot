import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.checklist import (
    ChecklistCreateRequest,
    ChecklistCreateResponse,
    ChecklistDeleteResponse,
    ChecklistGetResponse,
    ChecklistListResponse,
    ChecklistResponse,
    ChecklistSummaryResponse,
    ChecklistUpdateRequest,
    ChecklistUpdateResponse,
)
from app.services.auth import get_current_user
from app.services.checklists import (
    create_checklist_for_user,
    delete_checklist,
    get_checklist_for_user,
    list_checklists_for_user,
    update_checklist_for_user,
)


router = APIRouter(prefix="/checklists")


@router.get("", response_model=ChecklistListResponse)
def list_checklists_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistListResponse:
    checklists = list_checklists_for_user(db, current_user.id)
    return ChecklistListResponse(checklists=[ChecklistSummaryResponse.model_validate(item) for item in checklists])


@router.get("/{checklist_id}", response_model=ChecklistGetResponse)
def get_checklist_route(
    checklist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistGetResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")
    return ChecklistGetResponse.model_validate(checklist)


@router.post("/create", response_model=ChecklistCreateResponse, status_code=status.HTTP_201_CREATED)
def create_checklist_route(
    payload: ChecklistCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistCreateResponse:
    checklist = create_checklist_for_user(db, current_user.id, payload)
    return ChecklistCreateResponse.model_validate(checklist)


@router.put("/update/{checklist_id}", response_model=ChecklistUpdateResponse)
def update_checklist_route(
    checklist_id: uuid.UUID,
    payload: ChecklistUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistUpdateResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")

    updated = update_checklist_for_user(db, checklist, payload)
    return ChecklistUpdateResponse.model_validate(updated)


@router.delete("/delete/{checklist_id}", response_model=ChecklistDeleteResponse)
def delete_checklist_route(
    checklist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistDeleteResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")

    delete_checklist(db, checklist)
    return ChecklistDeleteResponse(message="Checklist deleted successfully.")
