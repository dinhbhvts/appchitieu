"""Pydantic schemas for NotebookItem ("Sổ tay gia đình")."""

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict


class NotebookItemBase(BaseModel):
    # A key from notebook_types (e.g. "address", "account", or a custom
    # type) - validated against that table in the service layer, not here.
    type: str
    title: str
    relation: str | None = None
    phone: str | None = None
    address: str | None = None
    date1: date_type | None = None
    date1_is_lunar: bool = False
    date2: date_type | None = None
    recurrence_days: int | None = None
    amount: float | None = None
    # type=account fields.
    system: str | None = None
    username: str | None = None
    password: str | None = None  # plain in transit; encrypted at rest
    # custom-type field ("Thông tin").
    info: str | None = None
    tags: str | None = None
    note: str | None = None


class NotebookItemCreate(NotebookItemBase):
    pass


class NotebookItemUpdate(BaseModel):
    """Edit an item. All fields optional (partial update)."""

    type: str | None = None
    title: str | None = None
    relation: str | None = None
    phone: str | None = None
    address: str | None = None
    date1: date_type | None = None
    date1_is_lunar: bool | None = None
    date2: date_type | None = None
    recurrence_days: int | None = None
    amount: float | None = None
    system: str | None = None
    username: str | None = None
    password: str | None = None
    info: str | None = None
    tags: str | None = None
    note: str | None = None


class NotebookItemRead(NotebookItemBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UpcomingReminder(BaseModel):
    """One notebook item whose next occurrence falls within the requested
    window - for the Dashboard's "sắp tới" list.

    occurs_on is always a concrete SOLAR date, even for lunar anniversaries
    (already converted via app.core.lunar so the frontend never needs to
    know about lunar math).
    """

    item: NotebookItemRead
    occurs_on: date_type
    days_until: int
