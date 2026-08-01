"""HTTP endpoints for savings deposits ("Gửi tiết kiệm")."""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Message
from app.schemas.savings import (
    SavingsDepositCreate,
    SavingsDepositRead,
    SavingsDepositUpdate,
    SavingsSummary,
)
from app.services import savings_service as service

router = APIRouter(prefix="/savings", tags=["savings"])


@router.get("", response_model=list[SavingsDepositRead])
def list_deposits(
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Deposits whose start_date (ngày gửi) falls in [start, end] - includes
    both active and settled deposits (see savings_repository.list_between)."""
    return service.list_between(db, start=start, end=end, user_id=user_id)


@router.get("/unsettled", response_model=list[SavingsDepositRead])
def list_unsettled(user_id: int | None = None, db: Session = Depends(get_db)):
    """Deposits still active (chưa tất toán) - not affected by any date filter."""
    return service.list_unsettled(db, user_id=user_id)


@router.get("/summary", response_model=SavingsSummary)
def savings_summary(
    year: int, user_id: int | None = None, db: Session = Depends(get_db)
):
    """Totals for the top of the "Gửi tiết kiệm" tab: current active
    total/count (not date-filtered) plus interest actually received in
    `year` (by settled_date)."""
    return service.summary(db, year=year, user_id=user_id)


@router.post("", response_model=SavingsDepositRead, status_code=201)
def add_deposit(
    payload: SavingsDepositCreate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Record a new savings deposit."""
    return service.create_deposit(db, payload, actor_id=current.id)


@router.put("/{deposit_id}", response_model=SavingsDepositRead)
def update_deposit(
    deposit_id: int, payload: SavingsDepositUpdate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Edit a savings deposit."""
    try:
        row = service.update_deposit(db, deposit_id, payload, actor_id=current.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản tiết kiệm")
    return row


@router.delete("/{deposit_id}", response_model=Message)
def delete_deposit(deposit_id: int, db: Session = Depends(get_db)):
    """Delete a savings deposit."""
    if not service.delete_deposit(db, deposit_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản tiết kiệm")
    return Message(detail="Đã xóa khoản tiết kiệm")
