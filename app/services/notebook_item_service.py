"""Business logic for the family notebook (NotebookItem)."""

import calendar as _calendar
import logging
from datetime import date as date_type
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core import drive
from app.core.crypto import encrypt_text
from app.core.lunar import next_solar_occurrence, solar_to_lunar
from app.repositories import notebook_item_repository as repo
from app.repositories import notebook_type_repository as type_repo
from app.schemas.notebook_item import (
    CalendarEvent,
    NotebookItemCreate,
    NotebookItemUpdate,
    UpcomingReminder,
)

logger = logging.getLogger("vibeapp.notebook_item")

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
    row = repo.create(db, data)

    # type=personal_info with a "Tên hồ sơ": auto-create its own Drive
    # subfolder so this person's attachments land there instead of the
    # shared root folder - see notebook_attachment_service.upload_attachment.
    # Best-effort: if Drive isn't configured (or the call otherwise fails),
    # the item is still saved fine - it just falls back to the shared root
    # folder for attachments, same as before this feature existed.
    if row.type == "personal_info" and row.profile_name:
        try:
            folder = drive.create_folder(row.profile_name)
            repo.update(db, row, {"drive_folder_id": folder["id"]})
        except Exception:
            logger.warning(
                "Không tạo được thư mục Drive cho hồ sơ '%s' (item id=%s) - "
                "file đính kèm sẽ dùng thư mục chung.",
                row.profile_name, row.id, exc_info=True,
            )
    return row


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
      - personal_info: yearly recurrence via date1 (Ngày sinh), same as
        type=birthday, but only when remind_birthday is True (default) -
        the user unticks it in the UI if that person's birthday is already
        tracked as a separate type=birthday row, to avoid a duplicate.
      - service / maintenance: date2 ("ngày hết hạn / đến hạn kế tiếp") if
        it falls in the window - this is a stored one-off due date, not
        auto-recomputed from recurrence_days (keeps the logic simple; the
        user updates date2 by hand after renewing, same as before).
      - task ("Tạo nhắc việc"): date2 ("Ngày cần hoàn thành") if it falls in
        the window - same one-off due-date handling as service/maintenance,
        EXCEPT a task with is_completed=True is skipped entirely regardless
        of its due date (đã xong thì thôi không còn "sắp tới" nữa).

    Other types (address, account, note, child_milestone, custom types) have
    no natural "upcoming" concept and are not included.
    """
    today = today or date_type.today()
    end = today + timedelta(days=days)
    reminders: list[UpcomingReminder] = []

    for item in repo.list_all(db):
        # Viec (task) da danh dau hoan thanh: bo qua han - khong con la
        # "sap toi" nua. Ap dung o day (nguon chung cho ca Dashboard va
        # push_service.send_daily_reminders) nen chi can sua 1 cho la ca
        # hai tu dong ngung nhac.
        if item.type == "task" and item.is_completed:
            continue
        is_birthday_reminder = (
            item.type in _YEARLY_RECURRING_TYPES
            or (item.type == "personal_info" and item.remind_birthday)
        )
        if is_birthday_reminder and item.date1:
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


def _yearly_occurrence_in_month(
    date1: date_type, is_lunar: bool, year: int, month: int,
    lunar_lookup: dict[tuple[int, int], date_type],
) -> date_type | None:
    """Where a yearly-recurring date1 (birthday/anniversary) lands within
    solar (year, month), or None if it doesn't land in this month at all.

    Lunar dates are resolved via `lunar_lookup` (built once per request from
    every day of the month - see get_calendar_events) rather than by
    guessing a lunar year, since a solar month can span two different lunar
    months/years (e.g. Tết) and this way it always agrees exactly with what
    /lunar/month shows for the same days.
    """
    if is_lunar:
        return lunar_lookup.get((date1.month, date1.day))
    if date1.month != month:
        return None
    d = date1.day
    while d >= 1:
        try:
            return date_type(year, month, d)
        except ValueError:
            d -= 1  # e.g. Feb 29 on a non-leap year -> fall back to Feb 28
    return None


def get_calendar_events(db: Session, year: int, month: int) -> list[CalendarEvent]:
    """Every notebook-based event landing on a day of solar (year, month) -
    birthday/personal_info/anniversary (yearly recurring, lunar-aware) and
    task due dates (one-off, date2). Powers the event-highlight dots on the
    Tổng quan month-calendar view (see /lunar/month for the day grid itself).
    """
    days_in_month = _calendar.monthrange(year, month)[1]
    lunar_lookup: dict[tuple[int, int], date_type] = {}
    for day in range(1, days_in_month + 1):
        d = date_type(year, month, day)
        l = solar_to_lunar(d)
        lunar_lookup[(l.month, l.day)] = d

    month_start = date_type(year, month, 1)
    month_end = date_type(year, month, days_in_month)

    events: list[CalendarEvent] = []
    for item in repo.list_all(db):
        is_birthday_reminder = (
            item.type == "birthday"
            or (item.type == "personal_info" and item.remind_birthday)
        )
        if is_birthday_reminder and item.date1:
            occurs_on = _yearly_occurrence_in_month(
                item.date1, item.date1_is_lunar, year, month, lunar_lookup,
            )
            if occurs_on:
                events.append(CalendarEvent(date=occurs_on, category="birthday", title=item.title))
        elif item.type == "anniversary" and item.date1:
            occurs_on = _yearly_occurrence_in_month(
                item.date1, item.date1_is_lunar, year, month, lunar_lookup,
            )
            if occurs_on:
                events.append(CalendarEvent(date=occurs_on, category="anniversary", title=item.title))
        elif item.type == "task" and item.date2 and not item.is_completed:
            if month_start <= item.date2 <= month_end:
                events.append(CalendarEvent(date=item.date2, category="task", title=item.title))

    events.sort(key=lambda e: e.date)
    return events
