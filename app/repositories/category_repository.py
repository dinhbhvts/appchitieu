"""Data-access layer for categories."""

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models.category import Category


def create(db: Session, data: dict) -> Category:
    row = Category(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_by_name(db: Session, name: str) -> Category | None:
    return db.scalar(select(Category).where(Category.name == name))


def list_all(db: Session, include_inactive: bool = False) -> list[Category]:
    """Return categories in insertion order, but always with the catch-all
    "Khác" / "Thu khác" pushed to the end of the list.

    By default only active (is_active) categories are returned - that is what
    the entry-screen picker wants. Pass include_inactive=True for the
    settings screen, which needs to show hidden categories too so they can be
    turned back on.
    """
    # 1 for the catch-all names, 0 otherwise -> sorts them last; ties broken by id.
    is_other = case((Category.name.in_(["Khác", "Thu khác"]), 1), else_=0)
    stmt = select(Category)
    if not include_inactive:
        stmt = stmt.where(Category.is_active.is_(True))
    stmt = stmt.order_by(is_other, Category.id)
    return list(db.scalars(stmt).all())


def update(db: Session, row: Category, changes: dict) -> Category:
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
