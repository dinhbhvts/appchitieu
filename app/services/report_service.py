"""Business logic for reports.

All statistics are derived from the single transactions table by filtering on
the date column - there are no per-month tables to maintain.
"""

from datetime import date as date_type

from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.repositories import transaction_repository as repo
from app.schemas.report import CategoryBreakdownItem, PeriodSummary


def period_summary(
    db: Session,
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
) -> PeriodSummary:
    """Totals for a period, for the whole fund or for one person.

    We always fetch the range WITHOUT a user filter, then split in Python,
    because the per-person "money received" figure needs transfers owned by the
    OTHER person - which a user-filtered query would hide.
    """
    rows = repo.list_between(db, start=start, end=end, user_id=None)

    # --- Household (fund) figures: transfers never change the fund total ---
    if user_id is None:
        total_income = sum(
            float(r.amount) for r in rows if r.type == TransactionType.income
        )
        total_expense = sum(
            float(r.amount) for r in rows if r.type == TransactionType.expense
        )
        return PeriodSummary(
            total_income=total_income,
            total_expense=total_expense,
            balance=total_income - total_expense,
        )

    # --- Per-person figures ---
    income = sum(
        float(r.amount)
        for r in rows
        if r.type == TransactionType.income and r.user_id == user_id
    )
    expense = sum(
        float(r.amount)
        for r in rows
        if r.type == TransactionType.expense and r.user_id == user_id
    )
    # Money this person sent to the other, and money they received.
    transferred_out = sum(
        float(r.amount)
        for r in rows
        if r.type == TransactionType.transfer and r.user_id == user_id
    )
    transferred_in = sum(
        float(r.amount)
        for r in rows
        if r.type == TransactionType.transfer and r.user_id != user_id
    )
    return PeriodSummary(
        total_income=income,
        total_expense=expense,
        balance=income - expense,
        transferred_out=transferred_out,
        transferred_in=transferred_in,
        net_held=income - expense - transferred_out + transferred_in,
    )


def expense_by_category(
    db: Session,
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
) -> list[CategoryBreakdownItem]:
    """Sum expenses grouped by category, largest first (for the pie/bar chart).

    Transactions with no category are grouped under "Chua phan loai".
    """
    rows = repo.list_between(db, start=start, end=end, user_id=user_id)

    # Accumulate totals in a dict keyed by category id.
    totals: dict[int | None, float] = {}
    names: dict[int | None, str] = {}
    for r in rows:
        if r.type != TransactionType.expense:
            continue
        key = r.category_id
        totals[key] = totals.get(key, 0.0) + float(r.amount)
        names[key] = r.category.name if r.category is not None else "Chua phan loai"

    items = [
        CategoryBreakdownItem(
            category_id=key, category_name=names[key], total=value
        )
        for key, value in totals.items()
    ]
    # Sort so the biggest spending category appears first.
    items.sort(key=lambda i: i.total, reverse=True)
    return items
