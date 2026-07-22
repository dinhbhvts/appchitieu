"""Seed the database with the two fixed users and the suggested categories.

This runs automatically on startup (only when those tables are still empty), so
a brand-new install is immediately usable. Editing these lists changes what a
fresh database starts with.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import CategoryKind
from app.models.user import User

# The two people who use the app. Names are display strings (shown in the UI),
# so they use proper Vietnamese with diacritics.
DEFAULT_USERS = ["Chồng", "Vợ"]

# Suggested categories shown in the quick-entry screen. (name, kind)
# Order matters: they are seeded (and displayed) in this order. "Khác" and
# "Thu khác" are always pushed to the end of their group by the query.
DEFAULT_CATEGORIES = [
    # Income categories
    ("Lương chồng", CategoryKind.income),
    ("Lương vợ", CategoryKind.income),
    ("Thưởng", CategoryKind.income),
    ("Thu khác", CategoryKind.income),
    # Expense categories
    ("Ăn uống", CategoryKind.expense),
    ("Đi lại", CategoryKind.expense),
    ("Mua sắm", CategoryKind.expense),
    ("Sức khỏe", CategoryKind.expense),
    ("Gia đình", CategoryKind.expense),
    ("Học phí", CategoryKind.expense),
    ("Giải trí", CategoryKind.expense),
    ("Tài chính", CategoryKind.expense),
    ("Quà tặng", CategoryKind.expense),
    ("Khác", CategoryKind.expense),
]


def seed(db: Session) -> None:
    """Insert default rows only if the relevant table is currently empty."""
    if db.scalar(select(User)) is None:
        for name in DEFAULT_USERS:
            db.add(User(name=name))

    if db.scalar(select(Category)) is None:
        for name, kind in DEFAULT_CATEGORIES:
            db.add(Category(name=name, kind=kind, is_default=True))

    db.commit()
