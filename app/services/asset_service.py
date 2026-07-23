"""Business logic for asset snapshots (monthly net worth).

Net worth of a month = sum of that month's asset values. The month-by-month
trend ("thong ke luy ke") = the same sum grouped by month. A convenience
"copy from previous month" lets the user start from last month's list and just
edit the numbers, since assets usually change only a little each month.
"""

from sqlalchemy.orm import Session

from app.models.asset import AssetSnapshot
from app.repositories import asset_repository as repo
from app.schemas.asset import (
    AssetHistoryItem,
    AssetItemCreate,
    AssetItemUpdate,
    AssetMonth,
)


def get_month(db: Session, year: int, month: int) -> AssetMonth:
    """Return every asset line for a month, the total (net worth), and the
    change versus the previous month (amount and %)."""
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


def add_item(db: Session, payload: AssetItemCreate) -> AssetSnapshot:
    """Add one asset line to a month."""
    return repo.create(db, payload.model_dump())


def update_item(
    db: Session, item_id: int, payload: AssetItemUpdate
) -> AssetSnapshot | None:
    """Edit an asset line; returns None if the id does not exist."""
    row = repo.get(db, item_id)
    if row is None:
        return None
    return repo.update(db, row, payload.model_dump(exclude_unset=True))


def delete_item(db: Session, item_id: int) -> bool:
    """Delete an asset line; returns False if it did not exist."""
    row = repo.get(db, item_id)
    if row is None:
        return False
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


def copy_from_previous(
    db: Session, year: int, month: int
) -> AssetMonth:
    """Seed the given month with a copy of the most recent earlier month's
    lines (names + values + notes), so the user only has to tweak numbers.

    Does nothing if the target month already has data, to avoid duplicates.
    """
    existing = repo.list_month(db, year, month)
    if existing:
        return get_month(db, year, month)

    # Find the latest month that is strictly before the target month.
    target_key = (year, month)
    previous_rows: list[AssetSnapshot] = []
    latest_key: tuple[int, int] | None = None
    for row in repo.list_all(db):
        key = (row.year, row.month)
        if key < target_key:
            if latest_key is None or key > latest_key:
                latest_key = key
    if latest_key is not None:
        previous_rows = repo.list_month(db, latest_key[0], latest_key[1])

    for src in previous_rows:
        repo.create(db, {
            "year": year, "month": month,
            "name": src.name, "value": float(src.value), "note": src.note,
        })
    return get_month(db, year, month)
