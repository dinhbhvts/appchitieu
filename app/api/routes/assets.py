"""HTTP endpoints for asset snapshots (monthly net worth)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.asset import (
    AssetHistoryItem,
    AssetItemCreate,
    AssetItemRead,
    AssetItemUpdate,
    AssetMonth,
    AssetYearlyItem,
)
from app.schemas.common import Message
from app.services import asset_service as service

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/month", response_model=AssetMonth)
def get_month(year: int, month: int, db: Session = Depends(get_db)):
    """All asset lines for a month plus the total net worth."""
    return service.get_month(db, year, month)


@router.get("/history", response_model=list[AssetHistoryItem])
def history(db: Session = Depends(get_db)):
    """Total net worth per month (for the trend chart)."""
    return service.history(db)


@router.get("/yearly-history", response_model=list[AssetYearlyItem])
def yearly_history(db: Session = Depends(get_db)):
    """Net worth "chốt năm" per year plus year-over-year change.

    Always covers the full history, regardless of any date filter elsewhere
    in the app - meant for the long-term yearly trend chart in Báo cáo.
    """
    return service.yearly_history(db)


@router.post("", response_model=AssetItemRead, status_code=201)
def add_item(
    payload: AssetItemCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Add one asset line to a month."""
    return service.add_item(db, payload, actor_id=current.id)


@router.put("/{item_id}", response_model=AssetItemRead)
def update_item(
    item_id: int,
    payload: AssetItemUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Edit an asset line."""
    row = service.update_item(db, item_id, payload, actor_id=current.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài sản")
    return row


@router.delete("/{item_id}", response_model=Message)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an asset line."""
    if not service.delete_item(db, item_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy tài sản")
    return Message(detail="Đã xóa tài sản")


@router.post("/copy-previous", response_model=AssetMonth)
def copy_previous(year: int, month: int, db: Session = Depends(get_db)):
    """Fill a month from the most recent earlier month's list (editable)."""
    return service.copy_from_previous(db, year, month)
