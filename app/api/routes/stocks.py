"""HTTP endpoints for the stock module."""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Message
from app.schemas.stock import (
    CashFlowCreate,
    CashFlowRead,
    CashFlowUpdate,
    HoldingCreate,
    HoldingRead,
    HoldingUpdate,
    StockSummary,
    TradeCreate,
    TradeRead,
    TradeUpdate,
)
from app.services import stock_service as service

router = APIRouter(prefix="/stocks", tags=["stocks"])


# --- Cash flows (deposits / withdrawals) ---------------------------------

@router.post("/cashflows", response_model=CashFlowRead, status_code=201)
def add_cashflow(payload: CashFlowCreate, db: Session = Depends(get_db),
                 current: User = Depends(get_current_user)):
    """Record a deposit or withdrawal."""
    return service.create_cashflow(db, payload, actor_id=current.id)


@router.get("/cashflows", response_model=list[CashFlowRead])
def list_cashflows(user_id: int | None = None, db: Session = Depends(get_db)):
    """List deposits/withdrawals, optionally for one person."""
    return service.list_cashflows(db, user_id=user_id)


@router.put("/cashflows/{cid}", response_model=CashFlowRead)
def update_cashflow(
    cid: int, payload: CashFlowUpdate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Edit a deposit/withdrawal."""
    row = service.update_cashflow(db, cid, payload, actor_id=current.id)
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
def add_trade(payload: TradeCreate, db: Session = Depends(get_db),
              current: User = Depends(get_current_user)):
    """Record a buy or sell order."""
    return service.create_trade(db, payload, actor_id=current.id)


@router.get("/trades", response_model=list[TradeRead])
def list_trades(user_id: int | None = None, db: Session = Depends(get_db)):
    """List buy/sell orders, optionally for one person."""
    return service.list_trades(db, user_id=user_id)


@router.put("/trades/{tid}", response_model=TradeRead)
def update_trade(tid: int, payload: TradeUpdate, db: Session = Depends(get_db),
                 current: User = Depends(get_current_user)):
    """Edit a buy/sell order."""
    row = service.update_trade(db, tid, payload, actor_id=current.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lệnh")
    return row


@router.delete("/trades/{tid}", response_model=Message)
def delete_trade(tid: int, db: Session = Depends(get_db)):
    """Delete a buy/sell order."""
    if not service.delete_trade(db, tid):
        raise HTTPException(status_code=404, detail="Không tìm thấy lệnh")
    return Message(detail="Đã xóa lệnh")


# --- Manual holdings (danh mục đang giữ, nhập tay) ------------------------

@router.get("/holdings", response_model=list[HoldingRead])
def list_holdings(user_id: int | None = None, db: Session = Depends(get_db)):
    """List manually-entered holdings, optionally for one person."""
    return service.list_holdings(db, user_id=user_id)


@router.post("/holdings", response_model=HoldingRead, status_code=201)
def add_holding(payload: HoldingCreate, db: Session = Depends(get_db),
                current: User = Depends(get_current_user)):
    """Add a manually-entered holding line."""
    return service.create_holding(db, payload, actor_id=current.id)


@router.put("/holdings/{hid}", response_model=HoldingRead)
def update_holding(hid: int, payload: HoldingUpdate, db: Session = Depends(get_db),
                   current: User = Depends(get_current_user)):
    """Edit a holding."""
    row = service.update_holding(db, hid, payload, actor_id=current.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản đang giữ")
    return row


@router.delete("/holdings/{hid}", response_model=Message)
def delete_holding(hid: int, db: Session = Depends(get_db)):
    """Delete a holding."""
    if not service.delete_holding(db, hid):
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản đang giữ")
    return Message(detail="Đã xóa khoản đang giữ")


# --- Summary --------------------------------------------------------------

@router.get("/summary", response_model=StockSummary)
def stock_summary(
    user_id: int | None = None,
    start: date_type | None = None,
    end: date_type | None = None,
    db: Session = Depends(get_db),
):
    """Totals (deposit/withdraw/invested/realised P&L) plus per-ticker rows.

    Pass user_id for one person; omit for the combined view. start/end limit the
    deposit/withdraw stats to that period (e.g. the selected month).
    """
    return service.summary(db, user_id=user_id, start=start, end=end)
