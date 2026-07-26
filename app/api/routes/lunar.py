"""HTTP endpoints for the solar<->lunar (âm lịch) conversion utility."""

import calendar
from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Query

from app.core.lunar import lunar_to_solar, solar_to_lunar
from app.schemas.lunar import LunarDateRead, LunarMonthDayRead, SolarDateRead

router = APIRouter(prefix="/lunar", tags=["lunar"])


@router.get("/to-lunar", response_model=LunarDateRead)
def to_lunar(date: date_type = Query(..., description="Ngày dương lịch (YYYY-MM-DD)")):
    """Convert a solar date to its lunar (âm lịch) equivalent."""
    l = solar_to_lunar(date)
    return LunarDateRead(year=l.year, month=l.month, day=l.day, is_leap=l.is_leap)


@router.get("/to-solar", response_model=SolarDateRead)
def to_solar(
    year: int = Query(..., description="Năm âm lịch"),
    month: int = Query(..., ge=1, le=12, description="Tháng âm lịch"),
    day: int = Query(..., ge=1, le=30, description="Ngày âm lịch"),
    is_leap: bool = Query(False, description="Có phải tháng nhuận không"),
):
    """Convert a lunar date to its solar (dương lịch) equivalent.

    Falls back to the last valid day of that lunar month if the exact day
    doesn't exist that year (e.g. ngày 30 tháng thiếu -> lấy ngày 29).
    """
    try:
        d = lunar_to_solar(year, month, day, is_leap)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SolarDateRead(date=d)


@router.get("/month", response_model=list[LunarMonthDayRead])
def lunar_month(
    year: int = Query(..., description="Năm dương lịch"),
    month: int = Query(..., ge=1, le=12, description="Tháng dương lịch"),
):
    """Every day of one solar month, each paired with its lunar equivalent.

    Powers the month-calendar view of the "Tra cứu lịch âm" tool (Tổng
    quan): one call gets the whole month instead of the frontend calling
    /lunar/to-lunar once per day.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    result = []
    for day in range(1, days_in_month + 1):
        d = date_type(year, month, day)
        l = solar_to_lunar(d)
        result.append(LunarMonthDayRead(
            date=d, lunar_day=l.day, lunar_month=l.month,
            lunar_year=l.year, is_leap=l.is_leap,
        ))
    return result
