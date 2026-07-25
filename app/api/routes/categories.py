"""HTTP endpoints for categories.

Note there is no DELETE route on purpose - categories can never be deleted
(it would silently corrupt historical reports). Use PUT with
is_active=false to hide one instead.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import category_service as service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(include_inactive: bool = False, db: Session = Depends(get_db)):
    """Return categories (default suggestions plus any the user added).

    By default only active ones (what the entry-screen picker should show);
    pass include_inactive=true for the settings screen, which also needs to
    show - and let the user re-enable - hidden categories.
    """
    return service.list_categories(db, include_inactive=include_inactive)


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(
    payload: CategoryCreate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Add a user-defined category."""
    return service.create_category(db, payload, actor_id=current.id)


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Rename, re-icon, re-kind, or hide/show a category (never delete)."""
    row = service.update_category(db, category_id, payload, actor_id=current.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")
    return row
