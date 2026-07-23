"""Authentication helpers: password hashing and login tokens (JWT).

Design choices for this small family app:
- Passwords are hashed with PBKDF2-HMAC-SHA256 from the Python standard
  library (no extra C dependency to compile - important given the deploy
  environment). Each password gets its own random salt.
- Login state is a signed JWT (JSON Web Token). The client sends it back in the
  "Authorization: Bearer <token>" header; the server verifies the signature.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

settings = get_settings()
_ALGORITHM = "HS256"
_PBKDF2_ROUNDS = 200_000

# Reads the "Authorization: Bearer ..." header. auto_error=False lets us return
# a clean 401 message instead of FastAPI's default.
_bearer = HTTPBearer(auto_error=False)


# --- Password hashing -----------------------------------------------------

def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash (base64) safe to store in the database."""
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS
    )
    return base64.b64encode(salt + derived).decode("ascii")


def verify_password(password: str, stored: str | None) -> bool:
    """Check a raw password against a stored hash. Constant-time comparison."""
    if not stored:
        return False
    raw = base64.b64decode(stored.encode("ascii"))
    salt, derived = raw[:16], raw[16:]
    test = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS
    )
    return hmac.compare_digest(derived, test)


# --- Login tokens (JWT) ---------------------------------------------------

def create_access_token(user_id: int) -> str:
    """Create a signed token that identifies the logged-in user."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.access_token_expire_days
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: return the logged-in user, or raise 401.

    Add this to a router (`dependencies=[Depends(get_current_user)]`) to require
    a valid login for every endpoint in it.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Chưa đăng nhập hoặc phiên đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[_ALGORITHM]
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
