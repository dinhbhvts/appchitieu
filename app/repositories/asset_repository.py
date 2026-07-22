"""Data-access layer for asset snapshots."""

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
        .where(AssetSnapshot.year == year, AssetSnapshot.month == month)
        .order_by(AssetSnapshot.id.asc())
    )
    return list(db.scalars(stmt).all())


def list_all(db: Session) -> list[AssetSnapshot]:
    """Every snapshot, oldest month first - used to build the trend."""
    stmt = select(AssetSnapshot).order_by(
        AssetSnapshot.year.asc(), AssetSnapshot.month.asc()
    )
    return list(db.scalars(stmt).all())


def update(db: Session, row: AssetSnapshot, changes: dict) -> AssetSnapshot:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: AssetSnapshot) -> None:
    db.delete(row)
    db.commit()
