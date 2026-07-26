"""Data-access layer for notebook types (danh mục tiện ích)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notebook_type import NotebookType


def create(db: Session, data: dict) -> NotebookType:
    row = NotebookType(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, type_id: int) -> NotebookType | None:
    return db.get(NotebookType, type_id)


def get_by_key(db: Session, key: str) -> NotebookType | None:
    return db.scalar(select(NotebookType).where(NotebookType.key == key))


def list_all(db: Session, include_inactive: bool = False) -> list[NotebookType]:
    """Return notebook types in insertion order.

    By default only active ones are returned - what the "thêm mục sổ tay"
    type picker wants. Pass include_inactive=True for the settings screen.
    """
    stmt = select(NotebookType)
    if not include_inactive:
        stmt = stmt.where(NotebookType.is_active.is_(True))
    stmt = stmt.order_by(NotebookType.id)
    return list(db.scalars(stmt).all())


def update(db: Session, row: NotebookType, changes: dict) -> NotebookType:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
