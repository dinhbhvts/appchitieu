"""Data-access layer for AlbumPhoto (khung ảnh kỹ thuật số)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from app.models.album_photo import AlbumPhoto


def create(db: Session, data: dict) -> AlbumPhoto:
    row = AlbumPhoto(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, photo_id: int, with_data: bool = False) -> AlbumPhoto | None:
    stmt = select(AlbumPhoto).where(
        AlbumPhoto.id == photo_id, AlbumPhoto.is_deleted.is_(False),
    )
    if with_data:
        stmt = stmt.options(undefer(AlbumPhoto.image_data), undefer(AlbumPhoto.thumb_data))
    return db.scalars(stmt).first()


def list_all(db: Session) -> list[AlbumPhoto]:
    """Non-deleted photos, newest first. Image bytes are deferred columns,
    so this never loads them."""
    stmt = (
        select(AlbumPhoto)
        .where(AlbumPhoto.is_deleted.is_(False))
        .order_by(AlbumPhoto.created_at.desc(), AlbumPhoto.id.desc())
    )
    return list(db.scalars(stmt).all())


def update(db: Session, row: AlbumPhoto, changes: dict) -> AlbumPhoto:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: AlbumPhoto) -> None:
    row.is_deleted = True
    row.deleted_at = datetime.utcnow()
    db.commit()
