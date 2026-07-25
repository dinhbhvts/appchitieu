"""Data-access layer for the family notebook (NotebookItem)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.enums import NotebookItemType
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
    type: NotebookItemType | None = None,
    q: str | None = None,
) -> list[NotebookItem]:
    """List items, optionally filtered by type and/or a free-text search.

    The search is a simple case-insensitive "contains" match across every
    text field (title, relation, phone, address, tags, note) - approximate on
    purpose, per the "tìm tương đối" requirement (no need for exact spelling).
    """
    stmt = select(NotebookItem)
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
                NotebookItem.tags.ilike(like),
                NotebookItem.note.ilike(like),
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
    db.delete(row)
    db.commit()
