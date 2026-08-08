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
from app.repositories import user_repository
from app.schemas.stock import (
    CashFlowCreate,
    DividendCreate,
    DividendUpdate,
    HoldingCreate,
    HoldingUpdate,
    CashFlowUpdate,
    StockSummary,
    SymbolPosition,
    TradeCreate,
    TradeUpdate,
)


class CashHoldingLockedError(Exception):
    """Raised when the caller tries to edit/delete a system-managed field of
    the auto-computed "Tiền mặt" holding row (see StockHolding.is_cash)."""


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


# --- Dividends (co tuc) ----------------------------------------------------

def create_dividend(db: Session, payload: DividendCreate, actor_id=None):
    """Record a dividend payment. Symbol is normalised to upper-case, same
    as trades, so 'nkg' and 'NKG' are treated as the same ticker."""
    data = payload.model_dump()
    data["symbol"] = data["symbol"].strip().upper()
    data["updated_by"] = actor_id
    return repo.create_dividend(db, data)


def update_dividend(db: Session, did: int, payload: DividendUpdate, actor_id=None):
    row = repo.get_dividend(db, did)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "symbol" in changes and changes["symbol"]:
        changes["symbol"] = changes["symbol"].strip().upper()
    changes["updated_by"] = actor_id
    return repo.update_dividend(db, row, changes)


def delete_dividend(db: Session, did: int) -> bool:
    row = repo.get_dividend(db, did)
    if row is None:
        return False
    repo.delete_dividend(db, row)
    return True


def list_dividends(db: Session, user_id: int | None = None):
    """Dividends received, oldest first (optionally for one person)."""
    return repo.list_dividends(db, user_id=user_id)


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


import datetime as _dt


def _month_end(year: int, month: int) -> _dt.date:
    """Last calendar day of a month."""
    if month == 12:
        return _dt.date(year, 12, 31)
    return _dt.date(year, month + 1, 1) - _dt.timedelta(days=1)


def _cum_for_user(db: Session, user_id: int, year: int, month: int):
    """Cumulative (deposit, withdraw) for one person up to a month.

    Uses the authoritative "TỔNG HỢP CK" snapshot when available, extending it
    with later cash flows for months after the imported history.
    """
    snap = repo.latest_summary_before(db, user_id, year, month)
    if snap is None:
        # No snapshot: fall back to summing the recorded cash flows.
        end = _month_end(year, month)
        cfs = repo.list_cashflows(db, user_id=user_id)
        dep = sum(float(c.amount) for c in cfs
                  if c.type == CashFlowType.deposit and c.date <= end)
        wd = sum(float(c.amount) for c in cfs
                 if c.type == CashFlowType.withdraw and c.date <= end)
        return dep, wd
    if snap.year == year and snap.month == month:
        return float(snap.cum_deposit), float(snap.cum_withdraw)
    # Extend the snapshot with cash flows recorded after it.
    snap_end = _month_end(snap.year, snap.month)
    end = _month_end(year, month)
    cfs = repo.list_cashflows(db, user_id=user_id)
    extra_dep = sum(float(c.amount) for c in cfs
                    if c.type == CashFlowType.deposit and snap_end < c.date <= end)
    extra_wd = sum(float(c.amount) for c in cfs
                   if c.type == CashFlowType.withdraw and snap_end < c.date <= end)
    return float(snap.cum_deposit) + extra_dep, float(snap.cum_withdraw) + extra_wd


def _cum(db: Session, user_id: int | None, year: int, month: int):
    """Cumulative (deposit, withdraw) for a person or, if user_id is None, the
    sum across everyone with snapshots (combined view)."""
    if user_id is not None:
        return _cum_for_user(db, user_id, year, month)
    uids = repo.summary_user_ids(db)
    if not uids:
        # No snapshots at all: sum recorded cash flows for everyone.
        end = _month_end(year, month)
        cfs = repo.list_cashflows(db)
        dep = sum(float(c.amount) for c in cfs
                  if c.type == CashFlowType.deposit and c.date <= end)
        wd = sum(float(c.amount) for c in cfs
                 if c.type == CashFlowType.withdraw and c.date <= end)
        return dep, wd
    dep = wd = 0.0
    for u in uids:
        d, w = _cum_for_user(db, u, year, month)
        dep += d
        wd += w
    return dep, wd


def summary(db: Session, user_id: int | None = None,
            start=None, end=None) -> StockSummary:
    """Top-of-screen totals plus the per-ticker breakdown.

    - total_deposit / total_withdraw: for the selected month (= cumulative this
      month minus cumulative previous month).
    - cum_deposit / cum_withdraw: cumulative to the end of the month (from the
      file's TỔNG HỢP CK snapshots, extended for newer months).
    - invested_capital: cum_deposit - cum_withdraw.
    - total_realised_pl: cumulative realised profit/loss up to `end`.
    """
    if end is None:
        # No period given (all-time): compute straight from the cash flows.
        cashflows = repo.list_cashflows(db, user_id=user_id)
        cum_deposit = sum(float(c.amount) for c in cashflows
                          if c.type == CashFlowType.deposit)
        cum_withdraw = sum(float(c.amount) for c in cashflows
                           if c.type == CashFlowType.withdraw)
        period_deposit, period_withdraw = cum_deposit, cum_withdraw
    else:
        year, month = end.year, end.month
        py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
        cum_deposit, cum_withdraw = _cum(db, user_id, year, month)
        prev_deposit, prev_withdraw = _cum(db, user_id, py, pm)
        period_deposit = cum_deposit - prev_deposit
        period_withdraw = cum_withdraw - prev_withdraw

    # Profit/loss (realised + unrealised), the way the Excel file computes it:
    #   lãi/lỗ = giá trị đang giữ + tổng đã rút − tổng đã nạp
    # This is additive, so the combined view equals husband + wife, and it does
    # not depend on the (incomplete) buy/sell log.
    #
    # Dividends (cổ tức) are DELIBERATELY NOT part of this formula for
    # STOCK holdings - the user manually adjusts non-cash "Đang giữ" rows at
    # month-end, and that hand-entered number already accounts for any
    # dividend received, so folding dividends into the P&L formula again
    # would double-count them. The auto "Tiền mặt" row is the one exception:
    # it DOES fold dividends straight in (see _cash_delta), because nobody
    # hand-adjusts it - that is exactly what makes it auto-computed.
    # total_dividend below is still a record-keeping stat for display, not a
    # second input to the P&L on top of what's already inside holdings_value.
    holdings_value = sum(
        float(h.value) for h in list_holdings(db, user_id=user_id)
    )
    dividends = repo.list_dividends(db, user_id=user_id)
    if end is not None:
        dividends = [d for d in dividends if d.date <= end]
    cum_dividend = sum(float(d.amount) for d in dividends if d.amount is not None)
    total_pl = holdings_value + cum_withdraw - cum_deposit

    return StockSummary(
        total_deposit=period_deposit,
        total_withdraw=period_withdraw,
        cum_deposit=cum_deposit,
        cum_withdraw=cum_withdraw,
        invested_capital=cum_deposit - cum_withdraw,
        total_dividend=round(cum_dividend, 0),
        total_realised_pl=round(total_pl, 0),
        total_holdings_value=round(holdings_value, 0),
        positions=[],
    )


def list_cashflows(db: Session, user_id: int | None = None):
    """Deposits/withdrawals, oldest first (optionally for one person)."""
    return repo.list_cashflows(db, user_id=user_id)


def list_trades(db: Session, user_id: int | None = None):
    """Buy/sell orders, oldest first (optionally for one person)."""
    return repo.list_trades(db, user_id=user_id)


# --- Manual holdings + the auto "Tiền mặt" row -----------------------------
#
# "Tiền mặt" (is_cash=True) is the account's un-invested cash balance - money
# that has been nạp but not yet mua, or rút but not yet withdrawn from the
# holdings total. Before this existed, that money simply had no home in the
# Đang giữ list, so a user who deposited 100tr but only bought 80tr of stock
# would show 20tr as if it had vanished from total_realised_pl. The row is
# entirely system-computed except for one seed number the user may type in
# by hand (cash_base_value - e.g. cash they already held before adopting the
# app); see the StockHolding model docstring for the exact formula.

def _cash_delta(db: Session, user_id: int) -> float:
    """Net cash effect of every deposit/withdraw/buy/sell/dividend recorded
    for one person, all-time (not date-filtered - matches how holdings_value
    itself is a current-state number, not scoped to a period)."""
    delta = 0.0
    for cf in repo.list_cashflows(db, user_id=user_id):
        amount = float(cf.amount)
        delta += amount if cf.type == CashFlowType.deposit else -amount
    for t in repo.list_trades(db, user_id=user_id):
        qty, price, fee = int(t.quantity), float(t.price), float(t.fee)
        if t.side == TradeSide.buy:
            delta -= qty * price + fee
        else:  # sell
            delta += qty * price - fee
    for d in repo.list_dividends(db, user_id=user_id):
        if d.amount is not None:
            delta += float(d.amount)
    return delta


def _ensure_cash_holding(db: Session, user_id: int):
    """Get-or-create the "Tiền mặt" row for one person and refresh its value
    to cash_base_value + _cash_delta(...). Called every time holdings are
    listed (see list_holdings), so it's always current - same "recompute on
    every read" convention as asset_service._ensure_system_items."""
    row = repo.get_cash_holding(db, user_id)
    if row is None:
        row = repo.create_holding(db, {
            "user_id": user_id, "symbol": "Tiền mặt", "quantity": 0,
            "value": 0, "is_cash": True, "cash_base_value": 0,
        })
    value = round(float(row.cash_base_value) + _cash_delta(db, user_id), 0)
    if float(row.value) != value:
        row = repo.update_holding(db, row, {"value": value})
    return row


def list_holdings(db: Session, user_id: int | None = None):
    """Manually-entered holdings (optionally for one person), plus the
    auto-computed "Tiền mặt" row(s) - refreshed first so callers always see
    an up-to-date value."""
    if user_id is not None:
        _ensure_cash_holding(db, user_id)
    else:
        for u in user_repository.list_all(db):
            _ensure_cash_holding(db, u.id)
    return repo.list_holdings(db, user_id=user_id)


def create_holding(db: Session, payload: HoldingCreate, actor_id=None):
    data = payload.model_dump()
    data["symbol"] = data["symbol"].strip().upper()
    data["updated_by"] = actor_id
    return repo.create_holding(db, data)


# Fields allowed to change on the auto "Tiền mặt" row - everything else
# (symbol/quantity/value/user_id) is system-managed.
_CASH_ROW_EDITABLE_FIELDS = {"cash_base_value", "note"}


def update_holding(db: Session, hid: int, payload: HoldingUpdate, actor_id=None):
    row = repo.get_holding(db, hid)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if row.is_cash:
        locked = set(changes) - _CASH_ROW_EDITABLE_FIELDS
        if locked:
            raise CashHoldingLockedError(
                "Dòng 'Tiền mặt' do hệ thống tự tính, chỉ có thể sửa 'Giá "
                "trị khởi tạo' hoặc ghi chú."
            )
        changes["updated_by"] = actor_id
        row = repo.update_holding(db, row, changes)
        # Re-apply the formula immediately so the response already reflects
        # the new base value, instead of waiting for the next list_holdings.
        value = round(float(row.cash_base_value) + _cash_delta(db, row.user_id), 0)
        if float(row.value) != value:
            row = repo.update_holding(db, row, {"value": value})
        return row
    if "symbol" in changes and changes["symbol"]:
        changes["symbol"] = changes["symbol"].strip().upper()
    changes["updated_by"] = actor_id
    return repo.update_holding(db, row, changes)


def delete_holding(db: Session, hid: int) -> bool:
    row = repo.get_holding(db, hid)
    if row is None:
        return False
    if row.is_cash:
        raise CashHoldingLockedError(
            "Không thể xóa dòng 'Tiền mặt' tự động."
        )
    repo.delete_holding(db, row)
    return True
