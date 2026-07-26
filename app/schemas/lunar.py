"""Pydantic schemas for the lunar (âm lịch) conversion utility."""

from datetime import date as date_type

from pydantic import BaseModel


class LunarDateRead(BaseModel):
    year: int
    month: int
    day: int
    is_leap: bool


class SolarDateRead(BaseModel):
    date: date_type


class LunarMonthDayRead(BaseModel):
    """One day of a solar month, paired with its lunar equivalent - powers
    the month-calendar view (dương/âm song song) in the Tổng quan lunar
    lookup tool."""

    date: date_type
    lunar_day: int
    lunar_month: int
    lunar_year: int
    is_leap: bool
