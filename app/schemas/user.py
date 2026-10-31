"""Pydantic schemas for User.

Schemas describe the JSON shape the API accepts and returns. Keeping them
separate from the ORM models means we can change the database without breaking
the public API contract, and vice versa.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class UserBase(BaseModel):
    name: str


class UserCreate(UserBase):
    """Fields required to create a user (client -> server)."""


class UserRead(UserBase):
    """Fields returned to the client (server -> client)."""

    id: int
    created_at: datetime
    # Cấu hình > Người dùng. color null = màu mặc định (frontend tự áp).
    color: str | None = None
    avatar_preset: str | None = None
    avatar_updated_at: datetime | None = None

    @computed_field
    @property
    def avatar_version(self) -> int:
        """Đổi mỗi khi đổi avatar - frontend gắn vào URL/cache ảnh."""
        return int(self.avatar_updated_at.timestamp()) if self.avatar_updated_at else 0

    # from_attributes lets Pydantic build this straight from an ORM object.
    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """PATCH /users/me/profile - chỉ những trường gửi lên mới đổi; gửi null
    để về mặc định (màu mặc định / avatar chữ cái)."""

    color: str | None = None
    avatar_preset: str | None = None


class ChangePasswordRequest(BaseModel):
    """Request to change a user's password."""

    old_password: str
    new_password: str
    confirm_password: str
