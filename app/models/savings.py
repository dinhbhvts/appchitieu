"""SavingsDeposit model - "Gửi tiết kiệm" (bank term deposits), entered by
hand like the rest of the app's financial data (no bank integration).

Each row is one deposit at one bank, from ngày gửi to (planned or actual)
ngày đáo hạn/tất toán. maturity_date is always DERIVED from
(start_date, term_value, term_unit) - never edited directly, so it can never
drift out of sync with the term - see savings_service._compute_maturity_date.
"""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import SavingsStatus, SavingsTermUnit


class SavingsDeposit(Base):
    __tablename__ = "savings_deposits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    content: Mapped[str | None] = mapped_column(String(255), nullable=True)

    start_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 0), nullable=False)

    # Kỳ hạn: a plain number + its unit (ngày/tháng) - kept as two columns
    # (not just a day-count) so the original "6 tháng" the bank quoted is
    # still shown back to the user, not a derived "180 ngày".
    term_value: Mapped[int] = mapped_column(Integer, nullable=False)
    term_unit: Mapped[SavingsTermUnit] = mapped_column(
        Enum(SavingsTermUnit), nullable=False, default=SavingsTermUnit.month,
    )

    # Always computed server-side from (start_date, term_value, term_unit) -
    # see savings_service._compute_maturity_date. Never accepted as raw input.
    maturity_date: Mapped[date_type] = mapped_column(
        Date, nullable=False, index=True,
        comment="Tự động tính = start_date + kỳ hạn, không cho nhập tay trực "
                "tiếp (tránh lệch với kỳ hạn thực tế đã nhập).",
    )

    interest_rate: Mapped[float] = mapped_column(
        Numeric(6, 3), nullable=False,
        comment="Lãi suất %/năm.",
    )
    # Suggested by the service layer (lãi đơn: amount * rate% * số ngày gửi /
    # 365) when the item is created/edited, but stored as a normal editable
    # value so the user can correct it to match the exact figure their bank
    # quoted.
    expected_interest: Mapped[float] = mapped_column(
        Numeric(18, 0), nullable=False, default=0,
        comment="Tiền lãi dự kiến - gợi ý tự động (lãi đơn theo số ngày gửi), "
                "người dùng có thể sửa lại cho khớp với số ngân hàng báo.",
    )

    bank: Mapped[str | None] = mapped_column(String(150), nullable=True)

    status: Mapped[SavingsStatus] = mapped_column(
        Enum(SavingsStatus), nullable=False, default=SavingsStatus.active,
        comment="active = đang gửi, settled = đã tất toán.",
    )
    # Only meaningful once status=settled - the actual interest paid out,
    # which is what the Tài sản screen's Tài khoản vợ/chồng formula reads
    # (see app/services/asset_service.py) and what "Lãi đã nhận trong năm"
    # on this screen's summary card totals.
    actual_interest: Mapped[float | None] = mapped_column(
        Numeric(18, 0), nullable=True,
        comment="Tiền lãi thực nhận - chỉ có ý nghĩa khi đã tất toán. Đây là "
                "số được cộng vào công thức tự động của Tài khoản vợ/chồng "
                "(tháng có settled_date) và vào thống kê 'lãi đã nhận trong "
                "năm' trên chính màn Gửi tiết kiệm.",
    )
    settled_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Soft delete, same app-wide convention as every other table.
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Xóa mềm: True = người dùng đã xóa từ UI. Hàng vẫn còn "
                "trong DB, chỉ bị ẩn khỏi mọi danh sách và tổng hợp.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
