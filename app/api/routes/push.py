"""HTTP endpoints for Web Push notifications (thông báo nhắc sự kiện).

Split into two routers with different auth models:
  - `router` (subscribe/unsubscribe/vapid-public-key): normal login-required
    endpoints, included alongside every other protected router in main.py.
  - `cron_router` (run-daily): called by the daily GitHub Actions workflow,
    which has no user login - it authenticates with a shared secret header
    instead (see _require_cron_secret). Included WITHOUT the login
    dependency in main.py, on purpose.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.push import (
    PushSubscriptionCreate,
    PushUnsubscribe,
    RunDailyResult,
    VapidPublicKeyRead,
)
from app.services import push_service as service

settings = get_settings()

router = APIRouter(prefix="/push", tags=["push"])
cron_router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key", response_model=VapidPublicKeyRead)
def vapid_public_key():
    """Public key the frontend passes to pushManager.subscribe(). Returns an
    empty string if the server hasn't configured VAPID keys yet - the
    frontend shows "Chưa cấu hình thông báo" instead of crashing."""
    return VapidPublicKeyRead(public_key=service.get_vapid_public_key())


@router.post("/subscribe", status_code=201)
def subscribe(
    payload: PushSubscriptionCreate, db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Save (or refresh) this device's push subscription."""
    service.subscribe(db, payload, user_id=current.id)
    return {"ok": True}


@router.delete("/subscribe")
def unsubscribe(payload: PushUnsubscribe, db: Session = Depends(get_db)):
    """Remove a device's subscription (user tapped "Tắt thông báo", or the
    browser reports the subscription changed/expired)."""
    service.unsubscribe(db, payload.endpoint)
    return {"ok": True}


def _require_cron_secret(x_cron_secret: str | None = Header(default=None)) -> None:
    if not settings.notify_cron_secret or x_cron_secret != settings.notify_cron_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu hoặc sai X-Cron-Secret",
        )


@cron_router.post(
    "/run-daily", response_model=RunDailyResult,
    dependencies=[Depends(_require_cron_secret)],
)
def run_daily(db: Session = Depends(get_db)):
    """Send today's push notification for every upcoming event within
    `push_reminder_days` days - triggered once a day by an external
    scheduler (see .github/workflows/daily-reminders.yml), since Render's
    free tier has no cron of its own and sleeps this app when idle."""
    return service.send_daily_reminders(db)
