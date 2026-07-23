"""Schemas for the login endpoints."""

from pydantic import BaseModel

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""

    username: str   # the display name, e.g. "Chồng" or "Vợ"
    password: str


class TokenResponse(BaseModel):
    """Returned on a successful login: the token plus who logged in."""

    access_token: str
    token_type: str = "bearer"
    user: UserRead
