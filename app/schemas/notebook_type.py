"""Pydantic schemas for NotebookType (danh mục tiện ích / Sổ tay)."""

from pydantic import BaseModel, ConfigDict


class NotebookTypeCreate(BaseModel):
    """Add a custom type. `key` is NOT accepted from the client - the
    server derives a stable machine key from `name` automatically (the UI
    is Vietnamese-only per the style guide; users should never have to type
    an English identifier)."""

    name: str
    icon: str | None = None


class NotebookTypeUpdate(BaseModel):
    """Rename/re-icon/hide a type. Deleting is never allowed - hide it
    instead (is_active = False). `key` can never be changed (it is what
    existing notebook_items rows point at)."""

    name: str | None = None
    icon: str | None = None
    is_active: bool | None = None


class NotebookTypeRead(BaseModel):
    id: int
    key: str
    name: str
    icon: str | None = None
    is_default: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
