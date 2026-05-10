from sqlalchemy.orm import Session

from app.db.models import Checklist


def list_checklists(db: Session, owner_id: int) -> list[Checklist]:
    return (
        db.query(Checklist)
        .filter(Checklist.owner_id == owner_id)
        .order_by(Checklist.updated_at.desc())
        .all()
    )


def get_checklist_by_id(
    db: Session,
    checklist_id: int,
    owner_id: int,
) -> Checklist | None:
    return (
        db.query(Checklist)
        .filter(
            Checklist.id == checklist_id,
            Checklist.owner_id == owner_id,
        )
        .first()
    )


def create_checklist(
    db: Session,
    owner_id: int,
    title: str,
    data: dict,
) -> Checklist:
    checklist = Checklist(
        owner_id=owner_id,
        title=title,
        data=data,
    )

    db.add(checklist)
    db.commit()
    db.refresh(checklist)

    return checklist


def update_checklist(
    db: Session,
    checklist: Checklist,
    title: str | None = None,
    data: dict | None = None,
) -> Checklist:
    if title is not None:
        checklist.title = title

    if data is not None:
        checklist.data = data

    db.commit()
    db.refresh(checklist)

    return checklist


def delete_checklist(db: Session, checklist: Checklist) -> None:
    db.delete(checklist)
    db.commit()
