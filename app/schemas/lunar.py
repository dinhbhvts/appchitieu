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
