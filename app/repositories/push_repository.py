"""Data-access layer for push_subscriptions (thông báo nhắc sự kiện)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.push_subscription import PushSubscription


def get_by_endpoint(db: Session, endpoint: str) -> PushSubscription | None:
    return db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )


def upsert(db: Session, data: dict) -> PushSubscription:
    """Create the subscription, or update it in place if this endpoint
    (device/browser) already subscribed before - e.g. the key rotated, or
    the user logged in as the other person on the same phone."""
    row = get_by_endpoint(db, data["endpoint"])
    if row is None:
        row = PushSubscription(**data)
        db.add(row)
    else:
        for field, value in data.items():
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def list_all(db: Session) -> list[PushSubscription]:
    return list(db.scalars(select(PushSubscription)).all())


def delete_by_endpoint(db: Session, endpoint: str) -> bool:
    row = get_by_endpoint(db, endpoint)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def delete(db: Session, row: PushSubscription) -> None:
    db.delete(row)
    db.commit()
