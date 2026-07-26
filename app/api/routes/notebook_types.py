"""HTTP endpoints for notebook types (danh mục tiện ích / Sổ tay).

No DELETE route on purpose - see notebook_type_service.py. Use PUT with
is_active=false to hide one instead.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.notebook_type import (
    NotebookTypeCreate,
    NotebookTypeRead,
    NotebookTypeUpdate,
)
from app.services import notebook_type_service as service

router = APIRouter(prefix="/notebook-types", tags=["notebook-types"])


@router.get("", response_model=list[NotebookTypeRead])
def list_types(include_inactive: bool = False, db: Session = Depends(get_db)):
    """Return notebook types (built-in ones plus any the user added).

    By default only active ones (what the "thêm mục sổ tay" picker should
    show); pass include_inactive=true for the settings screen.
    """
    return service.list_types(db, include_inactive=include_inactive)


@router.post("", response_model=NotebookTypeRead, status_code=201)
def create_type(
    payload: NotebookTypeCreate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Add a custom notebook type."""
    return service.create_type(db, payload, actor_id=current.id)


@router.put("/{type_id}", response_model=NotebookTypeRead)
def update_type(
    type_id: int, payload: NotebookTypeUpdate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Rename, re-icon, or hide/show a notebook type (never delete)."""
    row = service.update_type(db, type_id, payload, actor_id=current.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy loại tiện ích")
    return row
