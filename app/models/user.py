"""User model.

In this first version there are exactly two fixed users (e.g. Chong / Vo).
Each transaction and stock record points back to the user who entered it, which
is how we produce per-person reports as well as combined totals.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key: a unique auto-incrementing integer for every user.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Display name shown in the app UI (e.g. "Chong", "Vo").
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # When the row was created; the database fills this in automatically.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Convenience back-references so we can do user.transactions in Python.
    # These do NOT create extra columns; they are virtual links.
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user"
    )
