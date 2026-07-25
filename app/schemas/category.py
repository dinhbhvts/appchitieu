"""Pydantic schemas for Category."""

from pydantic import BaseModel, ConfigDict

from app.models.enums import CategoryKind


class CategoryBase(BaseModel):
    name: str
    kind: CategoryKind = CategoryKind.both
    icon: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    """Edit a category. Deleting is never allowed - hide it instead
    (is_active = False)."""

    name: str | None = None
    kind: CategoryKind | None = None
    icon: str | None = None
    is_active: bool | None = None


class CategoryRead(CategoryBase):
    id: int
    is_default: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
