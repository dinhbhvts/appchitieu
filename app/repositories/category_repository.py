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


def get_by_name(db: Session, name: str) -> Category | None:
    return db.scalar(select(Category).where(Category.name == name))


def list_all(db: Session) -> list[Category]:
    """Return categories in insertion order, but always with the catch-all
    "Khác" / "Thu khác" pushed to the end of the list."""
    # 1 for the catch-all names, 0 otherwise -> sorts them last; ties broken by id.
    is_other = case((Category.name.in_(["Khác", "Thu khác"]), 1), else_=0)
    stmt = select(Category).order_by(is_other, Category.id)
    return list(db.scalars(stmt).all())
