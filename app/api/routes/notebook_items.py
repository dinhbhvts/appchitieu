"""HTTP endpoints for the family notebook (NotebookItem / "Sổ tay")."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Message
from app.schemas.notebook_item import (
    NotebookItemCreate,
    NotebookItemRead,
    NotebookItemUpdate,
    UpcomingReminder,
)
from app.services import notebook_item_service as service

router = APIRouter(prefix="/notebook-items", tags=["notebook-items"])


@router.get("", response_model=list[NotebookItemRead])
def list_items(
    type: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    """List notebook items, optionally filtered by type (a notebook_types
    key) and/or a free-text search (q matches title/relation/phone/address/
    system/username/info/tags/note, "contains", case-insensitive)."""
    return service.list_items(db, type=type, q=q)


@router.get("/upcoming", response_model=list[UpcomingReminder])
def upcoming(days: int = 30, db: Session = Depends(get_db)):
    """Notebook items due in the next `days` days - birthdays, ngày giỗ
    (converted from lunar automatically), and service/maintenance due dates.
    Used by the Dashboard's "sắp tới" list."""
    return service.get_upcoming(db, days=days)


@router.post("", response_model=NotebookItemRead, status_code=201)
def create_item(
    payload: NotebookItemCreate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    try:
        return service.create_item(db, payload, actor_id=current.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{item_id}", response_model=NotebookItemRead)
def update_item(
    item_id: int, payload: NotebookItemUpdate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    try:
        row = service.update_item(db, item_id, payload, actor_id=current.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục sổ tay")
    return row


@router.delete("/{item_id}", response_model=Message)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    if not service.delete_item(db, item_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy mục sổ tay")
    return Message(detail="Đã xóa mục sổ tay")
