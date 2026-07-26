"""Transaction model - the heart of the whole application.

Design decision (from the style guide): we do NOT create one table per month.
Every income/expense row lives in this single table. Month and year are derived
from the "date" column at query time. This removes the manual "create a new
sheet each month and carry the balance over" work the Excel workflow required -
the running balance is computed automatically instead.

Soft delete (app-wide convention): "Xóa" from any UI in this app never removes
a row. It only sets is_deleted=True + deleted_at, and every list/summary query
filters is_deleted=False. Reasoning: this is financial data for two people who
may want to double-check "did I really mean to delete that?" months later, and
an accidental hard delete is unrecoverable while a soft delete costs nothing
(rows are small, and even decades of data for 2 people stays tiny - see the
index note below). The same is_deleted/deleted_at pair is used identically on
Transaction, AssetSnapshot, NotebookItem, NotebookAttachment, StockCashFlow,
StockTrade, StockHolding, and StockDividend.

Indexing for multi-year data (no table partitioning - see note): a composite
index on (user_id, date) supports the common "this person, this date range"
report query; the existing single-column index on `date` still covers the
combined (both people) view. Table PARTITIONING (e.g. by year) was considered
but is deliberately NOT used: at 2 users x maybe a few thousand rows/year, the
entire history after 30+ years is still only in the tens of thousands of rows
- far below where Postgres needs partitioning to stay fast, and partitioning
would add real operational complexity (partition maintenance, constraint
exclusion, migration risk) for a personal app - premature optimization per
the style guide ("Không tối ưu sớm những chức năng chưa cần thiết").
"""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TransactionType


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The calendar date of the transaction (no time-of-day needed). All monthly
    # and yearly statistics are grouped by this field.
    date: Mapped[date_type] = mapped_column(
        Date, nullable=False, index=True,
        comment="Ngày phát sinh giao dịch. Tháng/năm cho báo cáo được tính "
                "từ cột này, KHÔNG có bảng riêng theo tháng.",
    )

    # income or expense. Stored as text ("income"/"expense") in the database.
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False,
        comment="income = thu (tăng quỹ), expense = chi (giảm quỹ), "
                "transfer = chuyển nội bộ chồng->vợ (KHÔNG đổi tổng quỹ, chỉ "
                "dịch chuyển giữa 2 người trong báo cáo riêng).",
    )

    # Amount of money. Numeric(18, 0) stores whole VND with no rounding errors
    # (never use float for money). 18 digits is far more than enough.
    amount: Mapped[float] = mapped_column(Numeric(18, 0), nullable=False)

    # Free-text description, e.g. "di cho", "dien thang 6". Same idea as the
    # NOI DUNG column in the old spreadsheet.
    content: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional note (the old GHI CHU column, minus the H/D marker which now
    # lives in user_id instead).
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Which category this belongs to (nullable so a quick entry can skip it).
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )

    # Which of the two users entered this row. Replaces the old H/D marker.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    # Audit trail (not shown in the UI - only for inspecting the DB directly):
    # when the row was last changed and by which logged-in user.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Xóa mềm: True = người dùng đã xóa từ UI. Hàng vẫn còn trong "
                "DB, chỉ bị ẩn khỏi mọi danh sách và tổng hợp.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Python-side links for convenient access (transaction.user, .category).
    # foreign_keys is required because the table now has two FKs to users
    # (user_id = owner, updated_by = audit); the relationship uses user_id.
    user: Mapped["User"] = relationship(
        back_populates="transactions", foreign_keys=[user_id]
    )
    category: Mapped["Category | None"] = relationship()
