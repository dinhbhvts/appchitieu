"""HTTP endpoints for transactions."""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Message
from app.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    TransactionWithBalance,
)
from app.services import transaction_service as service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionWithBalance])
def list_transactions(
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    """List transactions with a running balance.

    Query parameters (all optional):
      * start, end : date range, format YYYY-MM-DD
      * user_id    : limit to one person; omit for the combined view
    """
    return service.list_with_running_balance(
        db, start=start, end=end, user_id=user_id
    )


@router.post("", response_model=TransactionRead, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Create a transaction (the main daily action)."""
    return service.create_transaction(db, payload, actor_id=current.id)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Edit an existing transaction."""
    row = service.update_transaction(
        db, transaction_id, payload, actor_id=current.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")
    return row


@router.delete("/{transaction_id}", response_model=Message)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction."""
    ok = service.delete_transaction(db, transaction_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")
    return Message(detail="Đã xóa giao dịch")
