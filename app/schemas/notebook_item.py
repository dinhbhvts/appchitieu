"""Pydantic schemas for NotebookItem ("Sổ tay gia đình")."""

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotebookItemType


class NotebookItemBase(BaseModel):
    type: NotebookItemType
    title: str
    relation: str | None = None
    phone: str | None = None
    address: str | None = None
    date1: date_type | None = None
    date1_is_lunar: bool = False
    date2: date_type | None = None
    recurrence_days: int | None = None
    amount: float | None = None
    tags: str | None = None
    note: str | None = None


class NotebookItemCreate(NotebookItemBase):
    pass


class NotebookItemUpdate(BaseModel):
    """Edit an item. All fields optional (partial update)."""

    type: NotebookItemType | None = None
    title: str | None = None
    relation: str | None = None
    phone: str | None = None
    address: str | None = None
    date1: date_type | None = None
    date1_is_lunar: bool | None = None
    date2: date_type | None = None
    recurrence_days: int | None = None
    amount: float | None = None
    tags: str | None = None
    note: str | None = None


class NotebookItemRead(NotebookItemBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
