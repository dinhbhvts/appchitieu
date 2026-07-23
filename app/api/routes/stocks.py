"""HTTP endpoints for the stock module."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import Message
from app.schemas.stock import (
    CashFlowCreate,
    CashFlowRead,
    CashFlowUpdate,
    StockSummary,
    TradeCreate,
    TradeRead,
    TradeUpdate,
)
from app.services import stock_service as service

router = APIRouter(prefix="/stocks", tags=["stocks"])


# --- Cash flows (deposits / withdrawals) ---------------------------------

@router.post("/cashflows", response_model=CashFlowRead, status_code=201)
def add_cashflow(payload: CashFlowCreate, db: Session = Depends(get_db)):
    """Record a deposit or withdrawal."""
    return service.create_cashflow(db, payload)


@router.get("/cashflows", response_model=list[CashFlowRead])
def list_cashflows(user_id: int | None = None, db: Session = Depends(get_db)):
    """List deposits/withdrawals, optionally for one person."""
    return service.list_cashflows(db, user_id=user_id)


@router.put("/cashflows/{cid}", response_model=CashFlowRead)
def update_cashflow(
    cid: int, payload: CashFlowUpdate, db: Session = Depends(get_db)
):
    """Edit a deposit/withdrawal."""
    row = service.update_cashflow(db, cid, payload)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản nạp/rút")
    return row


@router.delete("/cashflows/{cid}", response_model=Message)
def delete_cashflow(cid: int, db: Session = Depends(get_db)):
    """Delete a deposit/withdrawal."""
    if not service.delete_cashflow(db, cid):
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản nạp/rút")
    return Message(detail="Đã xóa khoản nạp/rút")


# --- Trades (buy / sell) --------------------------------------------------

@router.post("/trades", response_model=TradeRead, status_code=201)
def add_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    """Record a buy or sell order."""
    return service.create_trade(db, payload)


@router.get("/trades", response_model=list[TradeRead])
def list_trades(user_id: int | None = None, db: Session = Depends(get_db)):
    """List buy/sell orders, optionally for one person."""
    return service.list_trades(db, user_id=user_id)


@router.put("/trades/{tid}", response_model=TradeRead)
def update_trade(tid: int, payload: TradeUpdate, db: Session = Depends(get_db)):
    """Edit a buy/sell order."""
    row = service.update_trade(db, tid, payload)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lệnh")
    return row


@router.delete("/trades/{tid}", response_model=Message)
def delete_trade(tid: int, db: Session = Depends(get_db)):
    """Delete a buy/sell order."""
    if not service.delete_trade(db, tid):
        raise HTTPException(status_code=404, detail="Không tìm thấy lệnh")
    return Message(detail="Đã xóa lệnh")


# --- Summary --------------------------------------------------------------

@router.get("/summary", response_model=StockSummary)
def stock_summary(user_id: int | None = None, db: Session = Depends(get_db)):
    """Totals (deposit/withdraw/invested/realised P&L) plus per-ticker rows.

    Pass user_id for one person; omit for the combined view.
    """
    return service.summary(db, user_id=user_id)
