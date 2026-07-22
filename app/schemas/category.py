"""Pydantic schemas for Category."""

from pydantic import BaseModel, ConfigDict

from app.models.enums import CategoryKind


class CategoryBase(BaseModel):
    name: str
    kind: CategoryKind = CategoryKind.both


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: int
    is_default: bool

    model_config = ConfigDict(from_attributes=True)
