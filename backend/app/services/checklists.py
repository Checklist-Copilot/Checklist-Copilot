import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, load_only

from app.db.models import Checklist
from app.schemas.checklist import ChecklistCreateRequest, ChecklistUpdateRequest


def list_checklists_for_user(db: Session, user_id: uuid.UUID) -> list[Checklist]:
    stmt = (
        select(Checklist)
        .options(
            load_only(
                Checklist.id,
                Checklist.user_id,
                Checklist.title,
                Checklist.description,
                Checklist.created_at,
                Checklist.updated_at,
            )
        )
        .where(Checklist.user_id == user_id)
        .order_by(Checklist.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_checklist_for_user(db: Session, user_id: uuid.UUID, payload: ChecklistCreateRequest) -> Checklist:
    checklist = Checklist(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        checklist=payload.checklist,
        checklist_prev=None,
    )
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist


def get_checklist_for_user(db: Session, checklist_id: uuid.UUID, user_id: uuid.UUID) -> Checklist | None:
    stmt = select(Checklist).where(Checklist.id == checklist_id, Checklist.user_id == user_id)
    return db.scalar(stmt)


def update_checklist_for_user(db: Session, checklist: Checklist, payload: ChecklistUpdateRequest) -> Checklist:
    checklist.checklist_prev = checklist.checklist
    checklist.checklist = payload.checklist

    if payload.title is not None:
        checklist.title = payload.title
    if payload.description is not None:
        checklist.description = payload.description

    db.commit()
    db.refresh(checklist)
    return checklist


def delete_checklist(db: Session, checklist: Checklist) -> None:
    db.delete(checklist)
    db.commit()
