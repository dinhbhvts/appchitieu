"""Pydantic schemas for User.

Schemas describe the JSON shape the API accepts and returns. Keeping them
separate from the ORM models means we can change the database without breaking
the public API contract, and vice versa.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    name: str


class UserCreate(UserBase):
    """Fields required to create a user (client -> server)."""


class UserRead(UserBase):
    """Fields returned to the client (server -> client)."""

    id: int
    created_at: datetime

    # from_attributes lets Pydantic build this straight from an ORM object.
    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    """Request to change a user's password."""

    old_password: str
    new_password: str
    confirm_password: str
