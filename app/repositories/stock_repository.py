"""Data-access layer for stock cash flows and trades."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import StockCashFlow, StockTrade


def create_cashflow(db: Session, data: dict) -> StockCashFlow:
    row = StockCashFlow(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_cashflows(db: Session) -> list[StockCashFlow]:
    stmt = select(StockCashFlow).order_by(StockCashFlow.date.asc())
    return list(db.scalars(stmt).all())


def create_trade(db: Session, data: dict) -> StockTrade:
    row = StockTrade(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_trades(db: Session, symbol: str | None = None) -> list[StockTrade]:
    """All trades, oldest-first, optionally filtered to one symbol.

    Oldest-first matters: the average-cost calculation processes buys and sells
    in chronological order.
    """
    stmt = select(StockTrade)
    if symbol is not None:
        stmt = stmt.where(StockTrade.symbol == symbol)
    stmt = stmt.order_by(StockTrade.date.asc(), StockTrade.id.asc())
    return list(db.scalars(stmt).all())
