"""Category model.

Categories (an uong, di lai, hoa don, ...) let us group transactions so the
report screen can answer "how much did we spend on food this month?". The Excel
file did not have this; it is a deliberate improvement.
"""

from sqlalchemy import Boolean, Enum, Integer, String
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
