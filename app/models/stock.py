"""Stock tracking models.

Two separate tables, all entered by hand (no live market prices):

1. StockCashFlow - money deposited into / withdrawn from the brokerage account.
2. StockTrade    - individual buy / sell orders per ticker symbol.

Realised profit/loss is computed from these manually-entered numbers and then
folded into the combined income/expense statistics.
"""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import CashFlowType, TradeSide


class StockCashFlow(Base):
    __tablename__ = "stock_cashflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    # deposit or withdraw.
    type: Mapped[CashFlowType] = mapped_column(
        Enum(CashFlowType), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(18, 0), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


class StockTrade(Base):
    __tablename__ = "stock_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    # Ticker symbol, e.g. "NKG", "GEX". Stored upper-case by the service layer.
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # buy or sell.
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=False)

    # Number of shares in this order.
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Price per share.
    price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)

    # Broker fee for this order (defaults to 0 if left blank).
    fee: Mapped[float] = mapped_column(Numeric(18, 0), default=0, nullable=False)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


class StockHolding(Base):
    """A manually-entered "currently held" line per person.

    Unlike the per-ticker positions computed from trades, this is a value the
    user types in directly (mã + current value in VND). It is NOT derived from
    the buy/sell log - the user maintains it by hand.
    """

    __tablename__ = "stock_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    # Ticker or free label, e.g. "NKG".
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    # Current value in VND (money), typed by the user.
    value: Mapped[float] = mapped_column(Numeric(18, 0), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
