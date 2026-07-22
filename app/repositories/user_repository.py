"""Data-access layer for users."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def create(db: Session, data: dict) -> User:
    row = User(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_all(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)).all())
