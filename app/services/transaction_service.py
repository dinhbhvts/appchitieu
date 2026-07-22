"""Business logic for transactions.

The key job here is computing the running balance. The old spreadsheet kept a
DU CUOI column by hand; we recompute it from scratch every time so it is always
correct. Balance after a row = balance so far + income - expense.
"""

from datetime import date as date_type

from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.repositories import transaction_repository as repo
from app.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    TransactionWithBalance,
)


def create_transaction(db: Session, payload: TransactionCreate) -> Transaction:
    """Validate-then-store a new transaction. Pydantic already checked types
    and amount > 0, so we can trust the payload here."""
    return repo.create(db, payload.model_dump())


def list_with_running_balance(
    db: Session,
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
) -> list[TransactionWithBalance]:
    """Return transactions plus the accumulated balance after each one.

    We walk the rows oldest-first, adding income and subtracting expense, so the
    last row's running_balance equals the closing balance for the range.
    """
    rows = repo.list_between(db, start=start, end=end, user_id=user_id)

    result: list[TransactionWithBalance] = []
    balance = 0.0
    for row in rows:
        amount = float(row.amount)
        # Only income/expense change the fund balance. A transfer is an internal
        # move between the two people, so it leaves the fund balance unchanged.
        if row.type == TransactionType.income:
            balance += amount
        elif row.type == TransactionType.expense:
            balance -= amount
        # First convert the ORM row to the base response schema, then add the
        # computed running_balance to produce the richer response object.
        base = TransactionRead.model_validate(row, from_attributes=True)
        item = TransactionWithBalance(
            **base.model_dump(), running_balance=balance
        )
        result.append(item)
    return result


def update_transaction(
    db: Session, transaction_id: int, payload: TransactionUpdate
) -> Transaction | None:
    """Update an existing transaction; returns None if the id is unknown."""
    row = repo.get(db, transaction_id)
    if row is None:
        return None
    # exclude_unset=True => only fields the client actually sent are changed.
    changes = payload.model_dump(exclude_unset=True)
    return repo.update(db, row, changes)


def delete_transaction(db: Session, transaction_id: int) -> bool:
    """Delete a transaction; returns False if it did not exist."""
    row = repo.get(db, transaction_id)
    if row is None:
        return False
    repo.delete(db, row)
    return True
