"""HTTP endpoints for users."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, hash_password, verify_password
from app.models.user import User
from app.repositories import user_repository as repo
from app.schemas.user import UserCreate, UserRead, ChangePasswordRequest

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


@router.put("/me/password", response_model=UserRead)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the logged-in user's password.

    Requires:
    - old_password: the current password (must match)
    - new_password: the new password (must not be empty, must != old)
    - confirm_password: must match new_password
    """
    # Verify old password.
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không chính xác",
        )

    # Validate new password.
    if not payload.new_password or len(payload.new_password.strip()) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới không được để trống",
        )

    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xác nhận mật khẩu không trùng khớp",
        )

    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới không được trùng với mật khẩu hiện tại",
        )

    # Hash and save the new password.
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(current_user)
    return current_user
