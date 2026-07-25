"""NotebookItem model - the "Sổ tay gia đình" (family notebook).

One flexible table backs every lookup-info screen (addresses, birthdays,
death anniversaries, long-running services, maintenance schedules, free
notes, a child's milestones...) instead of a separate table per kind. Each
row is tagged with `type` and only fills in the columns that make sense for
that type; the rest stay null. This keeps the architecture simple and lets a
brand-new kind be added later with a one-line enum change instead of a new
table + migration + API + screen (see NotebookItemType's docstring).
"""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import NotebookItemType


class NotebookItem(Base):
    __tablename__ = "notebook_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    type: Mapped[NotebookItemType] = mapped_column(
        Enum(NotebookItemType), nullable=False, index=True
    )

    # Main label shown in the list, e.g. "Bố", "Internet VNPT", "Xe Vision".
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # "Quan hệ" - relationship to the family (Bố, Mẹ, Ông nội...), used by
    # address/birthday/anniversary.
    relation: Mapped[str | None] = mapped_column(String(80), nullable=True)

    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Primary date: birth date, death date, service start date, last
    # maintenance date, milestone date - meaning depends on `type`.
    date1: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    # True when date1 is a LUNAR calendar date (âm lịch) - death anniversaries
    # in Vietnam are tracked by the lunar calendar. A future "lịch âm" utility
    # will use this flag to convert it to the correct solar date each year.
    date1_is_lunar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Secondary date: expiry date / next-due date (service, maintenance).
    date2: Mapped[date_type | None] = mapped_column(Date, nullable=True)

    # How often this repeats, in days (e.g. 180 for "6 tháng"), for a future
    # reminder engine. Null = one-off / no fixed cycle.
    recurrence_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Optional money amount (service price, loan amount...).
    amount: Mapped[float | None] = mapped_column(Numeric(18, 0), nullable=True)

    # Simple free-text tags, space or comma separated (e.g. "#xe #gia_dinh").
    # Deliberately not a separate tags table - a personal notebook for two
    # people does not need that much structure.
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Free-text content: general notes, or extra detail for any type.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
