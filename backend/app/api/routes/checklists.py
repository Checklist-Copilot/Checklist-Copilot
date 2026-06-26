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
    ChecklistJsonRestoreRequest,
    ChecklistListResponse,
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
    list_checklist_file_counts_for_user,
    list_checklists_for_user,
)
from app.services.files import delete_file_for_user, get_files_for_checklist


router = APIRouter(prefix="/checklists")


@router.get("", response_model=ChecklistListResponse)
def list_checklists_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistListResponse:
    checklists = list_checklists_for_user(db, current_user.id)
    file_counts = list_checklist_file_counts_for_user(db, current_user.id)
    summaries: list[ChecklistSummaryResponse] = []

    for item in checklists:
        summary = ChecklistSummaryResponse.model_validate(item)
        counts = file_counts.get(item.id, {"file_count": 0, "pdf_count": 0, "image_count": 0})
        summaries.append(summary.model_copy(update=counts))

    return ChecklistListResponse(checklists=summaries)


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

    # Work on detached copies because the update helpers mutate nested
    # dicts/lists in place. This keeps checklist_prev as a real undo snapshot
    # and avoids relying on SQLAlchemy detecting JSONB in-place mutations.
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


@router.post("/{checklist_id}/restore-previous", response_model=ChecklistUpdateResponse)
def restore_previous_checklist_route(
    checklist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistUpdateResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")
    if checklist.checklist_prev is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No previous checklist version available.")

    checklist.checklist = copy.deepcopy(checklist.checklist_prev)
    checklist.checklist_prev = None
    apply_stats(checklist)
    db.commit()
    db.refresh(checklist)

    return ChecklistUpdateResponse.model_validate(checklist)


@router.post("/{checklist_id}/restore-json", response_model=ChecklistUpdateResponse)
def restore_checklist_json_route(
    checklist_id: uuid.UUID,
    payload: ChecklistJsonRestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistUpdateResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")

    checklist.checklist = copy.deepcopy(payload.checklist)
    checklist.checklist_prev = None
    apply_stats(checklist)
    db.commit()
    db.refresh(checklist)

    return ChecklistUpdateResponse.model_validate(checklist)


@router.delete("/delete/{checklist_id}", response_model=ChecklistDeleteResponse)
async def delete_checklist_route(
    checklist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChecklistDeleteResponse:
    checklist = get_checklist_for_user(db, checklist_id, current_user.id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found.")

    linked_files = get_files_for_checklist(db, checklist_id, current_user.id)

    deletion_errors: list[str] = []
    for file_row in linked_files:
        try:
            await delete_file_for_user(db, file_row)
        except Exception as exc:  # noqa: BLE001 - collect all cleanup failures before reporting.
            deletion_errors.append(f"{file_row.id}: {exc}")

    if deletion_errors:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Checklist files could not be deleted from storage. Checklist was not deleted.",
        )

    delete_checklist(db, checklist)
    return ChecklistDeleteResponse(message="Checklist deleted successfully.")
