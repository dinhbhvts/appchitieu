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
    HoldingCreate,
    HoldingUpdate,
    CashFlowUpdate,
    StockSummary,
    SymbolPosition,
    TradeCreate,
    TradeUpdate,
)


def create_cashflow(db: Session, payload: CashFlowCreate, actor_id=None):
    """Record a deposit or withdrawal into the brokerage account."""
    data = payload.model_dump()
    data["updated_by"] = actor_id
    return repo.create_cashflow(db, data)


def create_trade(db: Session, payload: TradeCreate, actor_id=None):
    """Record a buy or sell order. Symbol is normalised to upper-case so
    'nkg' and 'NKG' are treated as the same ticker."""
    data = payload.model_dump()
    data["symbol"] = data["symbol"].strip().upper()
    data["updated_by"] = actor_id
    return repo.create_trade(db, data)


def update_cashflow(db: Session, cid: int, payload: CashFlowUpdate, actor_id=None):
    """Edit a deposit/withdrawal; returns None if the id does not exist."""
    row = repo.get_cashflow(db, cid)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_by"] = actor_id
    return repo.update_cashflow(db, row, changes)


def delete_cashflow(db: Session, cid: int) -> bool:
    row = repo.get_cashflow(db, cid)
    if row is None:
        return False
    repo.delete_cashflow(db, row)
    return True


def update_trade(db: Session, tid: int, payload: TradeUpdate, actor_id=None):
    """Edit a buy/sell order; returns None if the id does not exist."""
    row = repo.get_trade(db, tid)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "symbol" in changes and changes["symbol"]:
        changes["symbol"] = changes["symbol"].strip().upper()
    changes["updated_by"] = actor_id
    return repo.update_trade(db, row, changes)


def delete_trade(db: Session, tid: int) -> bool:
    row = repo.get_trade(db, tid)
    if row is None:
        return False
    repo.delete_trade(db, row)
    return True


def _positions(db: Session, user_id: int | None = None,
               end=None) -> list[SymbolPosition]:
    """Compute the aggregated position for every ticker from its trades.

    If `end` (a date) is given, only trades up to and including that date are
    counted (position/realised P&L "as of" that month).
    """
    trades = repo.list_trades(db, user_id=user_id)  # oldest-first
    if end is not None:
        trades = [t for t in trades if t.date <= end]

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


def summary(db: Session, user_id: int | None = None,
            start=None, end=None) -> StockSummary:
    """Top-of-screen totals plus the per-ticker breakdown.

    - total_deposit / total_withdraw: for the [start, end] period (that month)
      when given; otherwise all-time.
    - invested_capital: CUMULATIVE net money put in up to `end` (money currently
      in the account), not just the period.
    - total_realised_pl: CUMULATIVE realised profit/loss up to `end`.
    """
    cashflows = repo.list_cashflows(db, user_id=user_id)

    def in_period(d) -> bool:
        return (start is None or d >= start) and (end is None or d <= end)

    def up_to(d) -> bool:
        return end is None or d <= end

    period_deposit = sum(
        float(c.amount) for c in cashflows
        if c.type == CashFlowType.deposit and in_period(c.date)
    )
    period_withdraw = sum(
        float(c.amount) for c in cashflows
        if c.type == CashFlowType.withdraw and in_period(c.date)
    )
    cum_deposit = sum(
        float(c.amount) for c in cashflows
        if c.type == CashFlowType.deposit and up_to(c.date)
    )
    cum_withdraw = sum(
        float(c.amount) for c in cashflows
        if c.type == CashFlowType.withdraw and up_to(c.date)
    )

    positions = _positions(db, user_id=user_id, end=end)
    total_realised = sum(p.realised_pl for p in positions)

    return StockSummary(
        total_deposit=period_deposit,
        total_withdraw=period_withdraw,
        invested_capital=cum_deposit - cum_withdraw,
        total_realised_pl=round(total_realised, 0),
        positions=positions,
    )


def list_cashflows(db: Session, user_id: int | None = None):
    """Deposits/withdrawals, oldest first (optionally for one person)."""
    return repo.list_cashflows(db, user_id=user_id)


def list_trades(db: Session, user_id: int | None = None):
    """Buy/sell orders, oldest first (optionally for one person)."""
    return repo.list_trades(db, user_id=user_id)


# --- Manual holdings ------------------------------------------------------

def list_holdings(db: Session, user_id: int | None = None):
    """Manually-entered holdings (optionally for one person)."""
    return repo.list_holdings(db, user_id=user_id)


def create_holding(db: Session, payload: HoldingCreate, actor_id=None):
    data = payload.model_dump()
    data["symbol"] = data["symbol"].strip().upper()
    data["updated_by"] = actor_id
    return repo.create_holding(db, data)


def update_holding(db: Session, hid: int, payload: HoldingUpdate, actor_id=None):
    row = repo.get_holding(db, hid)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "symbol" in changes and changes["symbol"]:
        changes["symbol"] = changes["symbol"].strip().upper()
    changes["updated_by"] = actor_id
    return repo.update_holding(db, row, changes)


def delete_holding(db: Session, hid: int) -> bool:
    row = repo.get_holding(db, hid)
    if row is None:
        return False
    repo.delete_holding(db, row)
    return True
