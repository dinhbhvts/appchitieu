"""Category model.

Categories (an uong, di lai, hoa don, ...) let us group transactions so the
report screen can answer "how much did we spend on food this month?". The Excel
file did not have this; it is a deliberate improvement.

Categories can never be deleted (deleting one would orphan every past
transaction that used it, silently corrupting old reports). A category the
user no longer wants can be renamed or hidden (is_active = False) instead -
hidden categories disappear from the entry-screen picker but still show up
correctly on historical transactions/reports.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import CategoryKind


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Name shown to the user, must be unique so we do not get duplicates.
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)

    # Whether this category is for income, expense, or usable for both.
    kind: Mapped[CategoryKind] = mapped_column(
        Enum(CategoryKind), default=CategoryKind.both, nullable=False
    )

    # True for the built-in suggested categories we seed on first run.
    # The user can still add their own (is_default = False).
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Suggested emoji shown next to the name in pickers (e.g. "🍜"). Optional -
    # the UI falls back to a generic icon when this is blank.
    icon: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # False = hidden from the entry-screen picker (the user's way of
    # "removing" a category without deleting it and breaking old reports).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
