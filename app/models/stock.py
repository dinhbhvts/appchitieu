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
        Enum(CashFlowType), nullable=False,
        comment="deposit = nạp tiền vào tài khoản chứng khoán, "
                "withdraw = rút tiền ra. Không liên quan Transaction.type.",
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
    side: Mapped[TradeSide] = mapped_column(
        Enum(TradeSide), nullable=False,
        comment="buy = lệnh mua, sell = lệnh bán. Vị thế đang nắm giữ theo "
                "mã (SymbolPosition) được TÍNH từ các dòng buy/sell này, "
                "không lưu trực tiếp.",
    )

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
    # Number of shares held (typed by the user).
    quantity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Số lượng cổ phiếu đang nắm giữ - người dùng TỰ NHẬP TAY, "
                "không tự tính từ StockTrade (mã này có thể mua từ trước "
                "khi dùng app, hoặc muốn nhập giá trị chốt tay).",
    )
    # Current value in VND (money), typed by the user.
    value: Mapped[float] = mapped_column(
        Numeric(18, 0), nullable=False,
        comment="Giá trị hiện tại (VNĐ) của phần đang giữ - người dùng tự "
                "nhập tay theo giá thị trường, KHÔNG tự động cập nhật.",
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


class StockMonthSummary(Base):
    """Per-person cumulative deposit/withdraw for a month, taken from the
    "TỔNG HỢP CK" table in the Excel file (the authoritative running totals).

    For months in the imported history these are the file's numbers. For newer
    months the app extends the latest snapshot with subsequent cash flows.
    """

    __tablename__ = "stock_month_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    cum_deposit: Mapped[float] = mapped_column(
        Numeric(18, 0), default=0,
        comment="Tổng đã nạp LŨY KẾ tính đến hết tháng này (không phải số "
                "nạp riêng trong tháng) - lấy từ dữ liệu Excel gốc hoặc nối "
                "tiếp từ snapshot gần nhất.",
    )
    cum_withdraw: Mapped[float] = mapped_column(
        Numeric(18, 0), default=0,
        comment="Tổng đã rút LŨY KẾ tính đến hết tháng này (không phải số "
                "rút riêng trong tháng).",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
