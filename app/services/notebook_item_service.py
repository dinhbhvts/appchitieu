"""Business logic for the family notebook (NotebookItem)."""

from datetime import date as date_type
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.core.lunar import next_solar_occurrence
from app.repositories import notebook_item_repository as repo
from app.repositories import notebook_type_repository as type_repo
from app.schemas.notebook_item import (
    NotebookItemCreate,
    NotebookItemUpdate,
    UpcomingReminder,
)

# Built-in type keys that recur every year on a fixed (month, day) - birthday
# for the living, anniversary for the deceased (ngày giỗ).
_YEARLY_RECURRING_TYPES = ("birthday", "anniversary")
# Built-in type keys whose date2 ("ngày hết hạn / đến hạn kế tiếp") is a
# one-off upcoming due date, not a yearly recurrence. "task" reuses date2 as
# "Ngày cần hoàn thành" (Tạo nhắc việc) - same one-off due-date semantics.
_DUE_DATE_TYPES = ("service", "maintenance", "task")


def _prepare_data(db: Session, data: dict) -> dict:
    """Validate `type` against notebook_types, and swap the plain `password`
    field for its encrypted form before it ever reaches the database."""
    if "type" in data and data["type"] is not None:
        if type_repo.get_by_key(db, data["type"]) is None:
            raise ValueError(f"Loại tiện ích '{data['type']}' không tồn tại")

    if "password" in data:
        plain = data.pop("password")
        data["password_encrypted"] = encrypt_text(plain)

    return data


def list_items(db: Session, type: str | None = None, q: str | None = None):
    return repo.list_all(db, type=type, q=q)


def create_item(db: Session, payload: NotebookItemCreate, actor_id=None):
    data = _prepare_data(db, payload.model_dump())
    data["updated_by"] = actor_id
    return repo.create(db, data)


def update_item(db: Session, item_id: int, payload: NotebookItemUpdate, actor_id=None):
    row = repo.get(db, item_id)
    if row is None:
        return None
    changes = _prepare_data(db, payload.model_dump(exclude_unset=True))
    changes["updated_by"] = actor_id
    return repo.update(db, row, changes)


def delete_item(db: Session, item_id: int) -> bool:
    row = repo.get(db, item_id)
    if row is None:
        return False
    repo.delete(db, row)
    return True


def _next_solar_yearly(month: int, day: int, after: date_type) -> date_type:
    """Next solar date on/after `after` with this (month, day), for a
    plain (non-lunar) yearly recurrence like a birthday. Falls back to
    Feb 28 if the date is Feb 29 and the candidate year isn't a leap year."""
    for year in (after.year, after.year + 1):
        d = day
        while d >= 1:
            try:
                candidate = date_type(year, month, d)
                break
            except ValueError:
                d -= 1  # e.g. Feb 29 on a non-leap year -> fall back to Feb 28
        else:
            continue
        if candidate >= after:
            return candidate
    # Unreachable in practice.
    return after + timedelta(days=365)


def get_upcoming(db: Session, days: int = 30, today: date_type | None = None) -> list[UpcomingReminder]:
    """Notebook items whose next occurrence falls within the next `days`
    days - for the Dashboard's "sắp tới" (upcoming) list.

    Covers:
      - birthday / anniversary: yearly recurrence via date1 (converted from
        lunar to solar first if date1_is_lunar).
      - service / maintenance: date2 ("ngày hết hạn / đến hạn kế tiếp") if
        it falls in the window - this is a stored one-off due date, not
        auto-recomputed from recurrence_days (keeps the logic simple; the
        user updates date2 by hand after renewing, same as before).
      - task ("Tạo nhắc việc"): date2 ("Ngày cần hoàn thành") if it falls in
        the window - same one-off due-date handling as service/maintenance.

    Other types (address, account, personal_info, note, child_milestone,
    custom types) have no natural "upcoming" concept and are not included.
    """
    today = today or date_type.today()
    end = today + timedelta(days=days)
    reminders: list[UpcomingReminder] = []

    for item in repo.list_all(db):
        if item.type in _YEARLY_RECURRING_TYPES and item.date1:
            if item.date1_is_lunar:
                occurs_on = next_solar_occurrence(
                    item.date1.month, item.date1.day, False, today
                )
            else:
                occurs_on = _next_solar_yearly(item.date1.month, item.date1.day, today)
        elif item.type in _DUE_DATE_TYPES and item.date2:
            occurs_on = item.date2
        else:
            continue

        if today <= occurs_on <= end:
            reminders.append(UpcomingReminder(
                item=item, occurs_on=occurs_on, days_until=(occurs_on - today).days,
            ))

    reminders.sort(key=lambda r: r.occurs_on)
    return reminders
