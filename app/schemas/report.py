"""Pydantic schemas for the reporting endpoints."""

from pydantic import BaseModel


class PeriodSummary(BaseModel):
    """Totals for a chosen period, for the whole fund or for one person.

    Household view (no user filter): transfers net to zero, so transferred_out
    and transferred_in are 0 and `balance` = income - expense.

    Per-person view (one user): transferred_out is what this person sent to the
    other; transferred_in is what they received. `net_held` is what this person
    effectively has left = income - expense - transferred_out + transferred_in.
    """

    total_income: float
    total_expense: float
    balance: float  # income - expense (fund; transfers excluded)
    transferred_out: float = 0  # money this person sent to the other
    transferred_in: float = 0   # money this person received from the other
    net_held: float = 0         # income - expense - out + in (per person)


class CategoryBreakdownItem(BaseModel):
    """One slice of the 'spending by category' report."""

    category_id: int | None
    category_name: str
    total: float
