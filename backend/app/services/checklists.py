import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, load_only

from app.db.models import Checklist
from app.db.models import File as FileModel
from app.schemas.checklist import ChecklistCreateRequest, ChecklistUpdateRequest
from app.services.checklist_update.stats import recount


def apply_stats(checklist: Checklist) -> None:
    """
    Recompute total/edited/completed item counts from the in-memory `checklist`
    JSON and write them onto the row. Caller is responsible for committing.

    Call this anywhere `checklist.checklist` is mutated before commit:
      - on create (so a brand-new row has accurate totals)
      - on manual edit (PUT/PATCH)
      - on AI edit
    """
    counts = recount(checklist.checklist or {})
    checklist.total_items = counts["total"]
    checklist.edited_items = counts["edited"]
    checklist.completed_items = counts["completed"]


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
                # Pulled for the dashboard summary — these are cheap ints, the
                # heavy `checklist` JSON column is still NOT loaded.
                Checklist.total_items,
                Checklist.edited_items,
                Checklist.completed_items,
            )
        )
        .where(Checklist.user_id == user_id)
        .order_by(Checklist.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


def list_checklist_file_counts_for_user(db: Session, user_id: uuid.UUID) -> dict[uuid.UUID, dict[str, int]]:
    stmt = (
        select(FileModel.checklist_id, FileModel.file_type, func.count(FileModel.id))
        .where(FileModel.user_id == user_id, FileModel.checklist_id.is_not(None))
        .group_by(FileModel.checklist_id, FileModel.file_type)
    )

    counts: dict[uuid.UUID, dict[str, int]] = {}
    for checklist_id, file_type, count in db.execute(stmt):
        if checklist_id is None:
            continue

        checklist_counts = counts.setdefault(checklist_id, {"file_count": 0, "pdf_count": 0, "image_count": 0})
        checklist_counts["file_count"] += count
        if file_type == "pdf":
            checklist_counts["pdf_count"] += count
        elif file_type == "image":
            checklist_counts["image_count"] += count

    return counts


def create_checklist_for_user(db: Session, user_id: uuid.UUID, payload: ChecklistCreateRequest) -> Checklist:
    checklist = Checklist(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        checklist=payload.checklist,
        checklist_prev=None,
    )
    apply_stats(checklist)
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

    apply_stats(checklist)
    db.commit()
    db.refresh(checklist)
    return checklist


def delete_checklist(db: Session, checklist: Checklist) -> None:
    db.delete(checklist)
    db.commit()
