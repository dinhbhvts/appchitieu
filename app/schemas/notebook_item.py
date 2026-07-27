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
    # type=personal_info fields (Thông tin cá nhân).
    full_name: str | None = None
    id_number: str | None = None
    id_issued_date: date_type | None = None
    id_issued_place: str | None = None
    birth_cert_no: str | None = None
    health_insurance_no: str | None = None
    hometown: str | None = None
    # Only meaningful for type=personal_info - see the column's comment in
    # app/models/notebook_item.py. Defaults to True (checked in the UI).
    remind_birthday: bool = True
    # custom-type field ("Thông tin"); also used as "Công việc" for type=task.
    info: str | None = None
    tags: str | None = None
    note: str | None = None


class NotebookItemCreate(NotebookItemBase):
    # "Tên hồ sơ" - only meaningful for type=personal_info. Set once here at
    # creation to auto-create a matching Drive subfolder (see
    # notebook_item_service.create_item) - deliberately absent from
    # NotebookItemUpdate below so it can never be changed afterwards.
    profile_name: str | None = None


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
    full_name: str | None = None
    id_number: str | None = None
    id_issued_date: date_type | None = None
    id_issued_place: str | None = None
    birth_cert_no: str | None = None
    health_insurance_no: str | None = None
    hometown: str | None = None
    remind_birthday: bool | None = None
    info: str | None = None
    tags: str | None = None
    note: str | None = None


class NotebookItemRead(NotebookItemBase):
    id: int
    # None once the row's Drive subfolder failed/wasn't created (e.g. Drive
    # wasn't configured yet) - attachments still work, just land in the
    # shared root folder instead of this person's own subfolder.
    profile_name: str | None = None

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


class CalendarEvent(BaseModel):
    """One notebook-based event landing on a specific day of a solar month -
    powers the highlight dots on the Tổng quan month-calendar view.

    category: "birthday" (sinh nhật, includes personal_info with
    remind_birthday=True) | "anniversary" (ngày giỗ) | "task" (nhắc việc).
    date is always a concrete SOLAR date, same lunar-conversion guarantee as
    UpcomingReminder.occurs_on.
    """

    date: date_type
    category: str
    title: str
