"""Solar <-> lunar (âm lịch) calendar conversion.

Built on the open-source `lunarcalendar` package (astronomical calculation,
same lunisolar rules Vietnam's calendar follows - occasionally off by a day
in rare years versus the official Vietnamese almanac, since that package is
calibrated to China's UTC+8 rather than Vietnam's UTC+7, but close enough for
a family reminder tool per the style guide's "không tối ưu sớm" principle).

Used for:
  - The /lunar utility (manual solar<->lunar lookup).
  - Converting a lunar anniversary (NotebookItem.date1 when date1_is_lunar)
    into this/next year's actual solar date, for the upcoming-reminders list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta

from lunarcalendar import Converter, Lunar, Solar
from lunarcalendar.converter import DateNotExist


@dataclass
class LunarDate:
    year: int
    month: int
    day: int
    is_leap: bool


def solar_to_lunar(d: date_type) -> LunarDate:
    """Convert a solar (dương lịch) date to its lunar (âm lịch) equivalent."""
    l = Converter.Solar2Lunar(Solar(d.year, d.month, d.day))
    return LunarDate(year=l.year, month=l.month, day=l.day, is_leap=l.isleap)


def lunar_to_solar(year: int, month: int, day: int, is_leap: bool = False) -> date_type:
    """Convert a lunar date to its solar equivalent.

    If that exact (month, day) doesn't exist in this particular lunar year
    (e.g. day 30 in a month that only has 29 days that year), falls back to
    the last valid day of that lunar month - the common convention for
    recurring lunar dates (giỗ ngày 30 -> tổ chức ngày 29 năm thiếu).
    """
    d = day
    while d >= 1:
        try:
            return Converter.Lunar2Solar(Lunar(year, month, d, isleap=is_leap)).to_date()
        except DateNotExist:
            d -= 1
    raise ValueError(f"Không tìm được ngày âm lịch hợp lệ: {year}/{month}/{day}")


def next_solar_occurrence(
    month: int, day: int, is_leap: bool, after: date_type,
) -> date_type:
    """Find the next solar date on/after `after` whose lunar (month, day)
    matches - used to turn a recurring lunar anniversary/birthday into a
    concrete upcoming solar date for the reminders list.

    Tries the current lunar year first; if that occurrence already passed
    (or landed before `after`), tries the next lunar year.
    """
    current_lunar_year = solar_to_lunar(after).year
    for year_offset in range(0, 3):  # a couple of years of headroom is plenty
        candidate = lunar_to_solar(current_lunar_year + year_offset, month, day, is_leap)
        if candidate >= after:
            return candidate
    # Should never happen in practice, but keep a safe fallback.
    return after + timedelta(days=365)
