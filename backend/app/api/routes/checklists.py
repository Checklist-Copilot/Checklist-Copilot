import copy
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
    ChecklistMetadataUpdateRequest,
    ChecklistSummaryResponse,
    ChecklistUpdateResponse,
)
from app.schemas.checklist_operations import ChecklistOperationsPatchRequest
from app.services.auth import get_current_user
from app.services.checklist_update.exceptions import (
    CannotDeleteRootError,
    ChecklistOperationError,
    ComponentNotFoundError,
    InvalidTargetContainerError,
    UnsupportedComponentTypeError,
    UnsupportedOperationError,
)
from app.services.checklist_update.service import apply_checklist_operations
from app.services.checklists import (
    apply_stats,
    create_checklist_for_user,
    delete_checklist,
    get_checklist_for_user,
    list_checklists_for_user,
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


@router.patch("/{checklist_id}", response_model=ChecklistUpdateResponse)
def patch_checklist_route(
    checklist_id: uuid.UUID,
    payload: ChecklistOperationsPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistUpdateResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")

    # Deep-copy before mutating. `apply_checklist_operations` calls dict.update
    # on the loaded JSONB in place, and SQLAlchemy does NOT detect in-place
    # mutations of JSONB columns. Without the copy the tree never writes to
    # disk — only the int stats columns persist — which gives the very
    # confusing "tick a box, stats jump to 1/N, refresh resets everything"
    # pattern. The AI edit route already does the same dance for the same
    # reason; keep them aligned.
    original_checklist = copy.deepcopy(checklist.checklist)
    working_checklist = copy.deepcopy(checklist.checklist)
    try:
        updated_json = apply_checklist_operations(working_checklist, payload.operations)
    except ComponentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (
        UnsupportedOperationError,
        UnsupportedComponentTypeError,
        InvalidTargetContainerError,
        CannotDeleteRootError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except ChecklistOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    checklist.checklist_prev = original_checklist
    checklist.checklist = updated_json
    apply_stats(checklist)
    db.commit()
    db.refresh(checklist)

    return ChecklistUpdateResponse.model_validate(checklist)


@router.patch("/{checklist_id}/metadata", response_model=ChecklistGetResponse)
def update_checklist_metadata_route(
    checklist_id: uuid.UUID,
    payload: ChecklistMetadataUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistGetResponse:
    """Edit ONLY the title/description — the JSON tree is untouched."""
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")

    if payload.title is not None:
        # Treat empty/whitespace as "no change" to avoid blanking the title accidentally.
        cleaned = payload.title.strip()
        if cleaned:
            checklist.title = cleaned
    if payload.description is not None:
        # Empty string is a valid "clear description"; preserve null vs "" distinction.
        checklist.description = payload.description or None

    db.commit()
    db.refresh(checklist)
    return ChecklistGetResponse.model_validate(checklist)


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
