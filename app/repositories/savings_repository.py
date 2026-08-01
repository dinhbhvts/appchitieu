"""Data-access layer for savings deposits ("Gửi tiết kiệm")."""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SavingsStatus
from app.models.savings import SavingsDeposit


def create(db: Session, data: dict) -> SavingsDeposit:
    row = SavingsDeposit(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, deposit_id: int) -> SavingsDeposit | None:
    return db.get(SavingsDeposit, deposit_id)


def list_between(
    db: Session,
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
) -> list[SavingsDeposit]:
    """Deposits whose start_date falls in [start, end] (both optional),
    newest first - powers the "Các khoản tiền gửi theo khoảng thời gian"
    card, which deliberately includes both active and settled deposits."""
    stmt = select(SavingsDeposit).where(SavingsDeposit.is_deleted.is_(False))
    if start is not None:
        stmt = stmt.where(SavingsDeposit.start_date >= start)
    if end is not None:
        stmt = stmt.where(SavingsDeposit.start_date <= end)
    if user_id is not None:
        stmt = stmt.where(SavingsDeposit.user_id == user_id)
    stmt = stmt.order_by(SavingsDeposit.start_date.desc(), SavingsDeposit.id.desc())
    return list(db.scalars(stmt).all())


def list_unsettled(db: Session, user_id: int | None = None) -> list[SavingsDeposit]:
    """Deposits still active (chưa tất toán) - NOT filtered by any date range,
    per the "Các khoản tiết kiệm chưa tất toán" card's spec."""
    stmt = select(SavingsDeposit).where(
        SavingsDeposit.is_deleted.is_(False),
        SavingsDeposit.status == SavingsStatus.active,
    )
    if user_id is not None:
        stmt = stmt.where(SavingsDeposit.user_id == user_id)
    stmt = stmt.order_by(SavingsDeposit.start_date.asc(), SavingsDeposit.id.asc())
    return list(db.scalars(stmt).all())


def list_all(db: Session) -> list[SavingsDeposit]:
    """Every non-deleted deposit - used for summary/formula aggregation."""
    stmt = select(SavingsDeposit).where(SavingsDeposit.is_deleted.is_(False))
    return list(db.scalars(stmt).all())


def update(db: Session, row: SavingsDeposit, changes: dict) -> SavingsDeposit:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: SavingsDeposit) -> None:
    """Soft-delete (see the app-wide note in app/models/transaction.py)."""
    row.is_deleted = True
    row.deleted_at = datetime.utcnow()
    db.commit()
