"""Data-access layer for asset snapshots."""

from datetime import datetime

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models.asset import AssetSnapshot

# Fixed display order for the 4 pinned system rows (see
# app/services/asset_service.py SYSTEM_ITEMS for what each key means) - lower
# number sorts first. Anything else (system_key is NULL) sorts after all of
# these, ordered by id like before.
_SYSTEM_ORDER = {"vo_taikhoan": 0, "chong_taikhoan": 1, "vo_ck": 2, "chong_ck": 3}


def create(db: Session, data: dict) -> AssetSnapshot:
    row = AssetSnapshot(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, item_id: int) -> AssetSnapshot | None:
    return db.get(AssetSnapshot, item_id)


def get_by_system_key(
    db: Session, year: int, month: int, system_key: str
) -> AssetSnapshot | None:
    """The one row for this month with this system_key, if it's been
    computed yet - used by asset_service to decide create-vs-update when
    (re)computing the 4 pinned system rows."""
    stmt = select(AssetSnapshot).where(
        AssetSnapshot.year == year,
        AssetSnapshot.month == month,
        AssetSnapshot.system_key == system_key,
        AssetSnapshot.is_deleted.is_(False),
    )
    return db.scalar(stmt)


def get_by_name(db: Session, year: int, month: int, name: str) -> AssetSnapshot | None:
    """Look up a row by its exact display name within one month - used to
    find the historical (pre-system, plain user-entered) closing value for
    the month immediately before the system formula kicks in."""
    stmt = select(AssetSnapshot).where(
        AssetSnapshot.year == year,
        AssetSnapshot.month == month,
        AssetSnapshot.name == name,
        AssetSnapshot.is_deleted.is_(False),
    )
    return db.scalar(stmt)


def list_month(db: Session, year: int, month: int) -> list[AssetSnapshot]:
    # System rows first (fixed order: Tài khoản vợ, Tài khoản chồng, Chứng
    # khoán vợ, Chứng khoán chồng), everything else after them by id - so
    # they're pinned to the top of the list the way the UI expects.
    order = case(_SYSTEM_ORDER, value=AssetSnapshot.system_key, else_=99)
    stmt = (
        select(AssetSnapshot)
        .where(
            AssetSnapshot.year == year,
            AssetSnapshot.month == month,
            AssetSnapshot.is_deleted.is_(False),
        )
        .order_by(order, AssetSnapshot.id.asc())
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
