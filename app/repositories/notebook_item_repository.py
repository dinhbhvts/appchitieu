"""Data-access layer for the family notebook (NotebookItem)."""

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.notebook_item import NotebookItem


def create(db: Session, data: dict) -> NotebookItem:
    row = NotebookItem(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, item_id: int) -> NotebookItem | None:
    return db.get(NotebookItem, item_id)


def list_all(
    db: Session,
    type: str | None = None,
    q: str | None = None,
) -> list[NotebookItem]:
    """List items, optionally filtered by type and/or a free-text search.

    The search is a simple case-insensitive "contains" match across every
    non-sensitive text field (title, relation, phone, address, system,
    username, info, tags, note, full_name, id_number, hometown,
    birth_cert_no, health_insurance_no) - approximate on purpose, per the
    "tìm tương đối" requirement. The encrypted password is never searched.
    """
    stmt = select(NotebookItem).where(NotebookItem.is_deleted.is_(False))
    if type is not None:
        stmt = stmt.where(NotebookItem.type == type)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                NotebookItem.title.ilike(like),
                NotebookItem.relation.ilike(like),
                NotebookItem.phone.ilike(like),
                NotebookItem.address.ilike(like),
                NotebookItem.system.ilike(like),
                NotebookItem.username.ilike(like),
                NotebookItem.info.ilike(like),
                NotebookItem.tags.ilike(like),
                NotebookItem.note.ilike(like),
                NotebookItem.full_name.ilike(like),
                NotebookItem.id_number.ilike(like),
                NotebookItem.hometown.ilike(like),
                NotebookItem.birth_cert_no.ilike(like),
                NotebookItem.health_insurance_no.ilike(like),
            )
        )
    stmt = stmt.order_by(NotebookItem.type, NotebookItem.title)
    return list(db.scalars(stmt).all())


def update(db: Session, row: NotebookItem, changes: dict) -> NotebookItem:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: NotebookItem) -> None:
    """Soft-delete (see the app-wide note in app/models/transaction.py)."""
    row.is_deleted = True
    row.deleted_at = datetime.utcnow()
    db.commit()
