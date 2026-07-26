"""Data-access layer for transactions.

A "repository" is the only place that knows how to read/write a given table.
Services call these functions instead of writing SQLAlchemy queries themselves,
which keeps business logic free of database details and easy to test.
"""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def create(db: Session, data: dict) -> Transaction:
    """Insert one transaction row from a plain dict of column values."""
    row = Transaction(**data)
    db.add(row)
    db.commit()
    db.refresh(row)  # reload so auto-generated id/created_at are populated
    return row


def get(db: Session, transaction_id: int) -> Transaction | None:
    """Fetch a single transaction by id, or None if it does not exist."""
    return db.get(Transaction, transaction_id)


def list_between(
    db: Session,
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
) -> list[Transaction]:
    """Return transactions in a date range, optionally for one user.

    Results are ordered oldest-first so the caller can walk through them and
    accumulate a running balance. All filters are optional. Soft-deleted rows
    are always excluded.
    """
    stmt = select(Transaction).where(Transaction.is_deleted.is_(False))
    if start is not None:
        stmt = stmt.where(Transaction.date >= start)
    if end is not None:
        stmt = stmt.where(Transaction.date <= end)
    if user_id is not None:
        stmt = stmt.where(Transaction.user_id == user_id)
    stmt = stmt.order_by(Transaction.date.asc(), Transaction.id.asc())
    return list(db.scalars(stmt).all())


def update(db: Session, row: Transaction, changes: dict) -> Transaction:
    """Apply only the provided fields to an existing row, then save."""
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete(db: Session, row: Transaction) -> None:
    """Soft-delete: mark the row hidden instead of removing it (see the
    app-wide soft-delete note in app/models/transaction.py)."""
    row.is_deleted = True
    row.deleted_at = datetime.utcnow()
    db.commit()
