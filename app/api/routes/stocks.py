"""HTTP endpoints for the stock module."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.stock import (
    CashFlowCreate,
    CashFlowRead,
    StockSummary,
    TradeCreate,
    TradeRead,
)
from app.services import stock_service as service

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.post("/cashflows", response_model=CashFlowRead, status_code=201)
def add_cashflow(payload: CashFlowCreate, db: Session = Depends(get_db)):
    """Record a deposit or withdrawal."""
    return service.create_cashflow(db, payload)


@router.post("/trades", response_model=TradeRead, status_code=201)
def add_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    """Record a buy or sell order."""
    return service.create_trade(db, payload)


@router.get("/cashflows", response_model=list[CashFlowRead])
def list_cashflows(db: Session = Depends(get_db)):
    """List all deposits/withdrawals (history)."""
    return service.list_cashflows(db)


@router.get("/trades", response_model=list[TradeRead])
def list_trades(db: Session = Depends(get_db)):
    """List all buy/sell orders (history)."""
    return service.list_trades(db)


@router.get("/summary", response_model=StockSummary)
def stock_summary(db: Session = Depends(get_db)):
    """Totals (deposit/withdraw/invested/realised P&L) plus per-ticker rows."""
    return service.summary(db)
