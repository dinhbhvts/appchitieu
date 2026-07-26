"""Data-access layer for asset snapshots."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetSnapshot


def create(db: Session, data: dict) -> AssetSnapshot:
    row = AssetSnapshot(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, item_id: int) -> AssetSnapshot | None:
    return db.get(AssetSnapshot, item_id)


def list_month(db: Session, year: int, month: int) -> list[AssetSnapshot]:
    stmt = (
        select(AssetSnapshot)
        .where(
            AssetSnapshot.year == year,
            AssetSnapshot.month == month,
            AssetSnapshot.is_deleted.is_(False),
        )
        .order_by(AssetSnapshot.id.asc())
    )
    return list(db.scalars(stmt).all())


def list_all(db: Session) -> list[AssetSnapshot]:
    """Every snapshot, oldest month first - used to build the trend."""
    stmt = (
        select(AssetSnapshot)
        .where(AssetSnapshot.is_deleted.is_(False))
        .order_by(AssetSnapshot.year.asc(), AssetSnapshot.month.asc())
    )
    return list(db.scalars(stmt).all())


def update(db: Session, row: AssetSnapshot, changes: dict) -> AssetSnapshot:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: AssetSnapshot) -> None:
    """Soft-delete (see the app-wide note in app/models/transaction.py)."""
    row.is_deleted = True
    row.deleted_at = datetime.utcnow()
    db.commit()
