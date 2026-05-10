from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.checklists import repository
from app.db.models import Checklist, ChecklistSnapshot


def list_user_checklists(db: Session, user_id: int):
    return repository.list_checklists(db, owner_id=user_id)


def get_user_checklist(
    db: Session,
    checklist_id: int,
    user_id: int,
) -> Checklist:
    checklist = repository.get_checklist_by_id(
        db,
        checklist_id=checklist_id,
        owner_id=user_id,
    )

    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    return checklist


def create_user_checklist(
    db: Session,
    user_id: int,
    title: str,
    data: dict,
) -> Checklist:
    return repository.create_checklist(
        db,
        owner_id=user_id,
        title=title,
        data=data,
    )


def update_user_checklist(
    db: Session,
    checklist_id: int,
    user_id: int,
    title: str | None,
    data: dict | None,
) -> Checklist:
    checklist = get_user_checklist(db, checklist_id, user_id)

    if data is not None:
        snapshot = ChecklistSnapshot(
            checklist_id=checklist.id,
            data=checklist.data,
        )
        db.add(snapshot)

    return repository.update_checklist(
        db,
        checklist=checklist,
        title=title,
        data=data,
    )


def delete_user_checklist(
    db: Session,
    checklist_id: int,
    user_id: int,
) -> None:
    checklist = get_user_checklist(db, checklist_id, user_id)
    repository.delete_checklist(db, checklist)


def undo_last_change(
    db: Session,
    checklist_id: int,
    user_id: int,
) -> Checklist:
    checklist = get_user_checklist(db, checklist_id, user_id)

    snapshot = (
        db.query(ChecklistSnapshot)
        .filter(ChecklistSnapshot.checklist_id == checklist.id)
        .order_by(ChecklistSnapshot.created_at.desc())
        .first()
    )

    if not snapshot:
        raise HTTPException(status_code=400, detail="No snapshot available")

    checklist.data = snapshot.data

    db.delete(snapshot)
    db.commit()
    db.refresh(checklist)

    return checklist
