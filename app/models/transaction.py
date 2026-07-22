"""Transaction model - the heart of the whole application.

Design decision (from the style guide): we do NOT create one table per month.
Every income/expense row lives in this single table. Month and year are derived
from the "date" column at query time. This removes the manual "create a new
sheet each month and carry the balance over" work the Excel workflow required -
the running balance is computed automatically instead.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TransactionType


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The calendar date of the transaction (no time-of-day needed). All monthly
    # and yearly statistics are grouped by this field.
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    # income or expense. Stored as text ("income"/"expense") in the database.
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
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
        ForeignKey("categories.id"), nullable=True
    )

    # Which of the two users entered this row. Replaces the old H/D marker.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Python-side links for convenient access (transaction.user, .category).
    user: Mapped["User"] = relationship(back_populates="transactions")
    category: Mapped["Category | None"] = relationship()
