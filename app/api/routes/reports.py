"""HTTP endpoints for reports."""

from datetime import date as date_type

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.report import CategoryBreakdownItem, PeriodSummary
from app.services import report_service as service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=PeriodSummary)
def summary(
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Income / expense / balance totals for a period (all or one user)."""
    return service.period_summary(db, start=start, end=end, user_id=user_id)


@router.get("/by-category", response_model=list[CategoryBreakdownItem])
def by_category(
    start: date_type | None = None,
    end: date_type | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Expense totals grouped by category, biggest first."""
    return service.expense_by_category(db, start=start, end=end, user_id=user_id)
