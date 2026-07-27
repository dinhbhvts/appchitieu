"""Business logic for asset snapshots (monthly net worth).

Net worth of a month = sum of that month's asset values. The month-by-month
trend ("thong ke luy ke") = the same sum grouped by month. A convenience
"copy from previous month" lets the user start from last month's list and just
edit the numbers, since assets usually change only a little each month.

Starting the 8/2026 cycle, 4 rows are no longer freely edited: Tài khoản
vợ/chồng and Chứng khoán vợ/chồng are pinned to the top and auto-computed
every time the month is viewed - see SYSTEM_ITEMS and _ensure_system_items().
"""

import calendar
from datetime import date as date_type

from sqlalchemy.orm import Session

from app.models.asset import AssetSnapshot
from app.repositories import asset_repository as repo
from app.repositories import user_repository
from app.schemas.asset import (
    AssetHistoryItem,
    AssetItemCreate,
    AssetItemUpdate,
    AssetMonth,
    AssetYearlyItem,
)
from app.services import report_service, stock_service


class SystemItemLockedError(Exception):
    """Raised when the caller tries to edit or delete one of the 4 pinned,
    auto-computed rows (Tài khoản/Chứng khoán vợ/chồng) by hand."""


# The 4 pinned rows and the formula each one uses:
#   - "account": prev month's own closing value + this month's "số dư" for
#     that person (report_service.period_summary(...).net_held already nets
#     out transfers between spouses exactly the way the user described it -
#     see the docstring there).
#   - "stock": current sum of that person's manually-maintained holdings
#     (StockHolding.value), not date-filtered - matches how the Stock screen
#     already treats "Đang giữ" as a hand-adjusted current-state number.
SYSTEM_ITEMS: dict[str, dict[str, str]] = {
    "vo_taikhoan": {"name": "Tài khoản vợ", "user_name": "Vợ", "kind": "account"},
    "chong_taikhoan": {"name": "Tài khoản chồng", "user_name": "Chồng", "kind": "account"},
    "vo_ck": {"name": "Chứng khoán vợ", "user_name": "Vợ", "kind": "stock"},
    "chong_ck": {"name": "Chứng khoán chồng", "user_name": "Chồng", "kind": "stock"},
}

# (year, month) from which the 4 rows above are pinned/auto-computed/locked.
# Months before this stay exactly as before: plain, free-form, user-entered
# rows (no system_key, fully editable/deletable).
_SYSTEM_START = (2026, 8)


def _prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _month_bounds(year: int, month: int) -> tuple[date_type, date_type]:
    last_day = calendar.monthrange(year, month)[1]
    return date_type(year, month, 1), date_type(year, month, last_day)


def _closing_value(db: Session, year: int, month: int, key: str) -> float:
    """The "chốt tháng" value of system row `key` at (year, month) - the
    starting point for the next month's formula.

    For months already on the system (>= _SYSTEM_START) this is the computed
    system row. For the one anchor month right before the cutover (7/2026),
    there is no system_key yet, so we fall back to the plain, hand-entered
    row matching the same display name.
    """
    if (year, month) >= _SYSTEM_START:
        row = repo.get_by_system_key(db, year, month, key)
        return float(row.value) if row else 0.0
    row = repo.get_by_name(db, year, month, SYSTEM_ITEMS[key]["name"])
    return float(row.value) if row else 0.0


def _ensure_system_items(db: Session, year: int, month: int) -> None:
    """Compute/refresh the 4 pinned rows for (year, month), recursing onto
    the previous month first so each month's formula always has an
    up-to-date "chốt tháng" figure to build on. No-ops before 8/2026."""
    if (year, month) < _SYSTEM_START:
        return

    py, pm = _prev_month(year, month)
    if (py, pm) >= _SYSTEM_START:
        _ensure_system_items(db, py, pm)

    users = {u.name: u for u in user_repository.list_all(db)}
    start, end = _month_bounds(year, month)

    for key, meta in SYSTEM_ITEMS.items():
        user = users.get(meta["user_name"])
        if meta["kind"] == "account":
            prev_closing = _closing_value(db, py, pm, key)
            net_held = 0.0
            if user is not None:
                net_held = report_service.period_summary(
                    db, start=start, end=end, user_id=user.id
                ).net_held or 0.0
            value = prev_closing + net_held
        else:  # "stock"
            value = 0.0
            if user is not None:
                value = sum(
                    float(h.value)
                    for h in stock_service.list_holdings(db, user_id=user.id)
                )

        existing = repo.get_by_system_key(db, year, month, key)
        if existing is None:
            repo.create(db, {
                "year": year, "month": month, "name": meta["name"],
                "value": value, "system_key": key,
            })
        else:
            repo.update(db, existing, {"name": meta["name"], "value": value})


# Display names of the 4 system rows - a PLAIN row with one of these exact
# names can only be the pre-cutover "anchor" row (_closing_value's name
# lookup reads it for the very first system month) and must never also be
# carried forward as an independent, unlocked duplicate - see
# _carry_forward_plain_items.
_SYSTEM_ITEM_NAMES = {meta["name"] for meta in SYSTEM_ITEMS.values()}


def _carry_forward_plain_items(db: Session, year: int, month: int) -> None:
    """Auto-copy the latest earlier month's PLAIN (non-system) asset rows
    into (year, month) the first time this month is viewed, so the user only
    has to tweak numbers instead of re-entering the whole list every month -
    same convenience "Chép từ tháng trước" used to require a manual tap for.
    The 4 pinned system rows are handled separately by _ensure_system_items
    and are never touched here (skipped both as source and as a reason to
    consider the month "already has data").

    No-ops once the month already has at least one PLAIN row (whether from
    an earlier carry-forward or the user's own manual entry/edit), so this
    is safe and idempotent to call on every get_month().
    """
    if any(i.system_key is None for i in repo.list_month(db, year, month)):
        return

    # Find the latest month that is strictly before the target month.
    target_key = (year, month)
    latest_key: tuple[int, int] | None = None
    for row in repo.list_all(db):
        key = (row.year, row.month)
        if key < target_key and (latest_key is None or key > latest_key):
            latest_key = key
    if latest_key is None:
        return

    for src in repo.list_month(db, latest_key[0], latest_key[1]):
        if src.system_key is not None or src.name in _SYSTEM_ITEM_NAMES:
            continue
        repo.create(db, {
            "year": year, "month": month,
            "name": src.name, "value": float(src.value), "note": src.note,
        })


def get_month(db: Session, year: int, month: int) -> AssetMonth:
    """Return every asset line for a month, the total (net worth), and the
    change versus the previous month (amount and %)."""
    _ensure_system_items(db, year, month)
    _carry_forward_plain_items(db, year, month)
    items = repo.list_month(db, year, month)
    total = sum(float(i.value) for i in items)

    # Previous month's total, for the up/down comparison.
    py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_items = repo.list_month(db, py, pm)
    prev_total = sum(float(i.value) for i in prev_items)

    change_amount = total - prev_total
    # % change only makes sense when the previous month had data.
    change_pct = (
        round(change_amount / prev_total * 100, 1) if prev_total > 0 else None
    )

    return AssetMonth(
        year=year, month=month, total=total, items=items,
        prev_total=prev_total, change_amount=change_amount,
        change_pct=change_pct,
    )


def add_item(
    db: Session, payload: AssetItemCreate, actor_id: int | None = None
) -> AssetSnapshot:
    """Add one asset line to a month."""
    data = payload.model_dump()
    data["updated_by"] = actor_id
    return repo.create(db, data)


def update_item(
    db: Session, item_id: int, payload: AssetItemUpdate,
    actor_id: int | None = None,
) -> AssetSnapshot | None:
    """Edit an asset line; returns None if the id does not exist."""
    row = repo.get(db, item_id)
    if row is None:
        return None
    if row.system_key is not None:
        raise SystemItemLockedError(
            "Mục này do hệ thống tự động tính (Tài khoản/Chứng khoán vợ/chồng), "
            "không thể sửa thủ công."
        )
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_by"] = actor_id
    return repo.update(db, row, changes)


def delete_item(db: Session, item_id: int) -> bool:
    """Delete an asset line; returns False if it did not exist."""
    row = repo.get(db, item_id)
    if row is None:
        return False
    if row.system_key is not None:
        raise SystemItemLockedError(
            "Mục này do hệ thống tự động tính (Tài khoản/Chứng khoán vợ/chồng), "
            "không thể xóa."
        )
    repo.delete(db, row)
    return True


def history(db: Session) -> list[AssetHistoryItem]:
    """Total net worth per month, oldest first, for the trend chart."""
    totals: dict[tuple[int, int], float] = {}
    for row in repo.list_all(db):
        key = (row.year, row.month)
        totals[key] = totals.get(key, 0.0) + float(row.value)
    return [
        AssetHistoryItem(year=y, month=m, total=t)
        for (y, m), t in sorted(totals.items())
    ]


def yearly_history(db: Session) -> list[AssetYearlyItem]:
    """Net worth "chốt năm" per year plus the year-over-year change.

    Always covers the full history (every year that has any asset data,
    typically starting 2022) - NOT affected by any date-range filter the
    Báo cáo screen might have active, since asset trends are a long-term view.

    For each year, the "chốt năm" value is the total of the LAST month that
    year which has any data (not necessarily December).
    """
    monthly = history(db)  # sorted oldest -> newest
    latest_per_year: dict[int, AssetHistoryItem] = {}
    for item in monthly:
        # monthly is sorted ascending, so the last write for a year is its
        # latest month - exactly the "chốt năm" value we want.
        latest_per_year[item.year] = item

    result: list[AssetYearlyItem] = []
    prev_total: float | None = None
    for year in sorted(latest_per_year.keys()):
        item = latest_per_year[year]
        change_amount = item.total - prev_total if prev_total is not None else 0.0
        change_pct = (
            round(change_amount / prev_total * 100, 1)
            if prev_total else None
        )
        result.append(AssetYearlyItem(
            year=year, closing_month=item.month, total=item.total,
            change_amount=change_amount, change_pct=change_pct,
        ))
        prev_total = item.total
    return result


def copy_from_previous(
    db: Session, year: int, month: int
) -> AssetMonth:
    """Seed the given month with a copy of the most recent earlier month's
    plain lines (names + values + notes), so the user only has to tweak
    numbers.

    Kept as an explicit endpoint for the rare case where a month truly has
    no data at all yet (nothing to carry forward from) - in the normal case
    this is now a harmless no-op, since get_month() already performs this
    exact carry-forward automatically the first time a month is viewed (see
    _carry_forward_plain_items).
    """
    return get_month(db, year, month)
