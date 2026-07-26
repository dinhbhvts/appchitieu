"""Pydantic schemas for stock cash flows, trades and the summary view."""

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import CashFlowType, TradeSide


class CashFlowCreate(BaseModel):
    date: date_type
    type: CashFlowType
    amount: float = Field(..., gt=0)
    user_id: int
    note: str | None = None


class CashFlowRead(CashFlowCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CashFlowUpdate(BaseModel):
    """Edit a deposit/withdrawal. All fields optional."""

    date: date_type | None = None
    type: CashFlowType | None = None
    amount: float | None = Field(default=None, gt=0)
    user_id: int | None = None
    note: str | None = None


class TradeCreate(BaseModel):
    date: date_type
    symbol: str
    side: TradeSide
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fee: float = Field(default=0, ge=0)
    user_id: int
    note: str | None = None


class TradeRead(TradeCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TradeUpdate(BaseModel):
    """Edit a buy/sell order. All fields optional."""

    date: date_type | None = None
    symbol: str | None = None
    side: TradeSide | None = None
    quantity: int | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)
    fee: float | None = Field(default=None, ge=0)
    user_id: int | None = None
    note: str | None = None


class SymbolPosition(BaseModel):
    """Aggregated position for one ticker, computed from its trades."""

    symbol: str
    quantity_held: int          # shares still held (buys - sells)
    average_cost: float         # average buy price of shares still held
    realised_pl: float          # profit/loss already locked in by selling


class StockSummary(BaseModel):
    """Top-of-screen totals for the stock module."""

    total_deposit: float        # nap trong ky (thang)
    total_withdraw: float       # rut trong ky (thang)
    cum_deposit: float = 0      # tong da nap luy ke den cuoi ky
    cum_withdraw: float = 0     # tong da rut luy ke den cuoi ky
    invested_capital: float     # cum_deposit - cum_withdraw (von rong)
    total_dividend: float = 0   # tong co tuc da nhan luy ke den cuoi ky
    total_realised_pl: float    # sum of realised profit/loss across symbols
    positions: list[SymbolPosition]


class HoldingCreate(BaseModel):
    """Add a manually-entered holding line."""

    user_id: int
    symbol: str
    quantity: int = Field(default=0, ge=0)
    value: float = Field(..., gt=0)
    note: str | None = None


class HoldingRead(HoldingCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class HoldingUpdate(BaseModel):
    """Edit a holding. All fields optional."""

    symbol: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    value: float | None = Field(default=None, gt=0)
    user_id: int | None = None
    note: str | None = None


class DividendCreate(BaseModel):
    """Record a dividend (cổ tức) payment - record-keeping only, NOT used to
    compute Lãi/lỗ (see StockDividend's docstring). The user may enter
    quantity, amount, or both - at least one is required."""

    date: date_type
    symbol: str
    quantity: int | None = Field(default=None, gt=0)
    amount: float | None = Field(default=None, gt=0)
    fee: float = Field(default=0, ge=0)
    user_id: int
    note: str | None = None

    @model_validator(mode="after")
    def _require_quantity_or_amount(self) -> "DividendCreate":
        if self.quantity is None and self.amount is None:
            raise ValueError("Nhập ít nhất số lượng hoặc số tiền cổ tức")
        return self


class DividendRead(BaseModel):
    id: int
    date: date_type
    symbol: str
    quantity: int | None = None
    amount: float | None = None
    fee: float
    user_id: int
    note: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DividendUpdate(BaseModel):
    """Edit a dividend record. All fields optional."""

    date: date_type | None = None
    symbol: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    amount: float | None = Field(default=None, gt=0)
    fee: float | None = Field(default=None, ge=0)
    user_id: int | None = None
    note: str | None = None
