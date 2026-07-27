"""Data-access layer for NotebookAttachment ("Hồ sơ đính kèm")."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notebook_attachment import NotebookAttachment


def create(db: Session, data: dict) -> NotebookAttachment:
    row = NotebookAttachment(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, attachment_id: int) -> NotebookAttachment | None:
    return db.get(NotebookAttachment, attachment_id)


def list_for_item(db: Session, notebook_item_id: int) -> list[NotebookAttachment]:
    stmt = (
        select(NotebookAttachment)
        .where(
            NotebookAttachment.notebook_item_id == notebook_item_id,
            NotebookAttachment.is_deleted.is_(False),
        )
        .order_by(NotebookAttachment.uploaded_at.asc())
    )
    return list(db.scalars(stmt).all())


def update(db: Session, row: NotebookAttachment, changes: dict) -> NotebookAttachment:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: NotebookAttachment) -> None:
    """Soft-delete the DB row (the service also deletes the real Drive file
    alongside this - see the comment on NotebookAttachment.is_deleted)."""
    row.is_deleted = True
    row.deleted_at = datetime.utcnow()
    db.commit()
