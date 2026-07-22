"""HTTP endpoints for users."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import user_repository as repo
from app.schemas.user import UserCreate, UserRead

# All routes in this file share the /users prefix and the "users" doc tag.
router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    """Return the (two) users."""
    return repo.list_all(db)


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a user (used once during setup)."""
    return repo.create(db, payload.model_dump())
