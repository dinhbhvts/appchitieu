"""Business logic for the stock module.

Everything is entered by hand; we never call an external price feed. From the
recorded buy/sell orders we compute, per ticker:

  * quantity_held  - shares still owned
  * average_cost   - average purchase price of the shares still owned
  * realised_pl    - profit/loss already locked in by selling

Method: weighted average cost. When shares are sold, the profit is the sale
proceeds (minus fee) less the average cost of the shares sold. This mirrors how
the old CK spreadsheet reasoned about each lot, but the maths is automatic.
"""

from sqlalchemy.orm import Session

from app.models.enums import CashFlowType, TradeSide
from app.repositories import stock_repository as repo
from app.schemas.stock import (
    CashFlowCreate,
    CashFlowUpdate,
    StockSummary,
    SymbolPosition,
    TradeCreate,
    TradeUpdate,
)


def create_cashflow(db: Session, payload: CashFlowCreate):
    """Record a deposit or withdrawal into the brokerage account."""
    return repo.create_cashflow(db, payload.model_dump())


def create_trade(db: Session, payload: TradeCreate):
    """Record a buy or sell order. Symbol is normalised to upper-case so
    'nkg' and 'NKG' are treated as the same ticker."""
    data = payload.model_dump()
    data["symbol"] = data["symbol"].strip().upper()
    return repo.create_trade(db, data)


def update_cashflow(db: Session, cid: int, payload: CashFlowUpdate):
    """Edit a deposit/withdrawal; returns None if the id does not exist."""
    row = repo.get_cashflow(db, cid)
    if row is None:
        return None
    return repo.update_cashflow(db, row, payload.model_dump(exclude_unset=True))


def delete_cashflow(db: Session, cid: int) -> bool:
    row = repo.get_cashflow(db, cid)
    if row is None:
        return False
    repo.delete_cashflow(db, row)
    return True


def update_trade(db: Session, tid: int, payload: TradeUpdate):
    """Edit a buy/sell order; returns None if the id does not exist."""
    row = repo.get_trade(db, tid)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "symbol" in changes and changes["symbol"]:
        changes["symbol"] = changes["symbol"].strip().upper()
    return repo.update_trade(db, row, changes)


def delete_trade(db: Session, tid: int) -> bool:
    row = repo.get_trade(db, tid)
    if row is None:
        return False
    repo.delete_trade(db, row)
    return True


def _positions(db: Session, user_id: int | None = None) -> list[SymbolPosition]:
    """Compute the aggregated position for every ticker from its trades."""
    trades = repo.list_trades(db, user_id=user_id)  # oldest-first

    # Group trades by symbol while preserving chronological order.
    by_symbol: dict[str, list] = {}
    for t in trades:
        by_symbol.setdefault(t.symbol, []).append(t)

    positions: list[SymbolPosition] = []
    for symbol, symbol_trades in by_symbol.items():
        held = 0                 # shares currently owned
        cost_basis = 0.0         # total cost of the shares currently owned
        realised = 0.0           # locked-in profit/loss so far

        for t in symbol_trades:
            qty = int(t.quantity)
            price = float(t.price)
            fee = float(t.fee)

            if t.side == TradeSide.buy:
                # Buying increases holdings and their total cost (fee included).
                cost_basis += qty * price + fee
                held += qty
            else:  # sell
                # Average cost per share of what we currently hold.
                avg = cost_basis / held if held > 0 else 0.0
                proceeds = qty * price - fee          # cash received, net of fee
                cost_of_sold = avg * qty              # what those shares cost us
                realised += proceeds - cost_of_sold   # profit or loss on this sale
                # Remove the sold shares and their share of the cost basis.
                held -= qty
                cost_basis -= cost_of_sold

        average_cost = cost_basis / held if held > 0 else 0.0
        positions.append(
            SymbolPosition(
                symbol=symbol,
                quantity_held=held,
                average_cost=round(average_cost, 2),
                realised_pl=round(realised, 0),
            )
        )
    return positions


def summary(db: Session, user_id: int | None = None) -> StockSummary:
    """Top-of-screen totals plus the per-ticker breakdown.

    Pass user_id to get one person's figures; omit for the combined view.
    """
    cashflows = repo.list_cashflows(db, user_id=user_id)
    total_deposit = sum(
        float(c.amount) for c in cashflows if c.type == CashFlowType.deposit
    )
    total_withdraw = sum(
        float(c.amount) for c in cashflows if c.type == CashFlowType.withdraw
    )

    positions = _positions(db, user_id=user_id)
    total_realised = sum(p.realised_pl for p in positions)

    return StockSummary(
        total_deposit=total_deposit,
        total_withdraw=total_withdraw,
        invested_capital=total_deposit - total_withdraw,
        total_realised_pl=round(total_realised, 0),
        positions=positions,
    )


def list_cashflows(db: Session, user_id: int | None = None):
    """Deposits/withdrawals, oldest first (optionally for one person)."""
    return repo.list_cashflows(db, user_id=user_id)


def list_trades(db: Session, user_id: int | None = None):
    """Buy/sell orders, oldest first (optionally for one person)."""
    return repo.list_trades(db, user_id=user_id)
