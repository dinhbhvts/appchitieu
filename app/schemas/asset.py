"""Pydantic schemas for asset snapshots and the net-worth views."""

from pydantic import BaseModel, ConfigDict, Field


class AssetItemBase(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    name: str
    value: float
    note: str | None = None


class AssetItemCreate(AssetItemBase):
    """Payload to add one asset line to a month."""


class AssetItemUpdate(BaseModel):
    """Edit an asset line. Every field optional so the client sends only
    what changed (e.g. just the value)."""

    name: str | None = None
    value: float | None = None
    note: str | None = None


class AssetItemRead(AssetItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AssetMonth(BaseModel):
    """All asset lines for one month plus their total (net worth) and the
    change compared with the previous month."""

    year: int
    month: int
    total: float
    items: list[AssetItemRead]
    prev_total: float = 0            # net worth of the previous month
    change_amount: float = 0         # total - prev_total
    change_pct: float | None = None  # % change; None if no previous month data


class AssetHistoryItem(BaseModel):
    """Total net worth for one month - used to draw the month-by-month trend."""

    year: int
    month: int
    total: float


class AssetYearlyItem(BaseModel):
    """Net worth "chốt năm" (year-end closing balance) plus the year-over-year
    change - for the yearly trend chart in Báo cáo. Always covers the full
    history (not affected by any date-range filter).

    The closing balance for a year is the total of the LAST month that year
    which has any asset data (not necessarily December, if December was
    never filled in) - matching how "prev_total" already works for the
    month-by-month view.
    """

    year: int
    closing_month: int          # which month's total was used as the year-end value
    total: float                 # net worth at that closing month
    change_amount: float = 0     # total - previous year's total (0 for the first year)
    change_pct: float | None = None  # % change; None if no previous year data
