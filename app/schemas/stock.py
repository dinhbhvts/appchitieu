"""Pydantic schemas for stock cash flows, trades and the summary view."""

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field

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

    total_deposit: float        # tong da nap
    total_withdraw: float       # tong da rut
    invested_capital: float     # nap - rut (net money put in)
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
