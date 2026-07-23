"""Data-access layer for stock cash flows and trades."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import (
    StockCashFlow,
    StockHolding,
    StockMonthSummary,
    StockTrade,
)


def create_cashflow(db: Session, data: dict) -> StockCashFlow:
    row = StockCashFlow(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_cashflow(db: Session, cid: int) -> StockCashFlow | None:
    return db.get(StockCashFlow, cid)


def list_cashflows(
    db: Session, user_id: int | None = None
) -> list[StockCashFlow]:
    """Deposits/withdrawals, oldest-first, optionally for one person."""
    stmt = select(StockCashFlow)
    if user_id is not None:
        stmt = stmt.where(StockCashFlow.user_id == user_id)
    stmt = stmt.order_by(StockCashFlow.date.asc(), StockCashFlow.id.asc())
    return list(db.scalars(stmt).all())


def update_cashflow(
    db: Session, row: StockCashFlow, changes: dict
) -> StockCashFlow:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_cashflow(db: Session, row: StockCashFlow) -> None:
    db.delete(row)
    db.commit()


def create_trade(db: Session, data: dict) -> StockTrade:
    row = StockTrade(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_trade(db: Session, tid: int) -> StockTrade | None:
    return db.get(StockTrade, tid)


def list_trades(
    db: Session, symbol: str | None = None, user_id: int | None = None
) -> list[StockTrade]:
    """All trades, oldest-first, optionally filtered by symbol and/or person.

    Oldest-first matters: the average-cost calculation processes buys and sells
    in chronological order.
    """
    stmt = select(StockTrade)
    if symbol is not None:
        stmt = stmt.where(StockTrade.symbol == symbol)
    if user_id is not None:
        stmt = stmt.where(StockTrade.user_id == user_id)
    stmt = stmt.order_by(StockTrade.date.asc(), StockTrade.id.asc())
    return list(db.scalars(stmt).all())


def update_trade(db: Session, row: StockTrade, changes: dict) -> StockTrade:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_trade(db: Session, row: StockTrade) -> None:
    db.delete(row)
    db.commit()


# --- Manual holdings ------------------------------------------------------


def create_holding(db: Session, data: dict) -> StockHolding:
    row = StockHolding(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_holding(db: Session, hid: int) -> StockHolding | None:
    return db.get(StockHolding, hid)


def list_holdings(db: Session, user_id: int | None = None) -> list[StockHolding]:
    stmt = select(StockHolding)
    if user_id is not None:
        stmt = stmt.where(StockHolding.user_id == user_id)
    stmt = stmt.order_by(StockHolding.symbol.asc())
    return list(db.scalars(stmt).all())


def update_holding(db: Session, row: StockHolding, changes: dict) -> StockHolding:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def delete_holding(db: Session, row: StockHolding) -> None:
    db.delete(row)
    db.commit()


# --- Monthly cumulative snapshots (TONG HOP CK) --------------------------

def latest_summary_before(db: Session, user_id: int, year: int, month: int):
    """The most recent StockMonthSummary for a user with (year, month) <= given."""
    key = year * 100 + month
    stmt = (
        select(StockMonthSummary)
        .where(
            StockMonthSummary.user_id == user_id,
            (StockMonthSummary.year * 100 + StockMonthSummary.month) <= key,
        )
        .order_by((StockMonthSummary.year * 100 + StockMonthSummary.month).desc())
    )
    return db.scalars(stmt).first()


def summary_user_ids(db: Session) -> list[int]:
    """Distinct user ids that have any monthly summary."""
    stmt = select(StockMonthSummary.user_id).distinct()
    return list(db.scalars(stmt).all())
