"""Business logic for Web Push notifications (thông báo nhắc sự kiện sắp tới).

Two jobs:
  1. subscribe()/unsubscribe() - called from the browser right after the
     user taps "Bật thông báo" / "Tắt thông báo" (see app/api/routes/push.py).
  2. send_daily_reminders() - called once a day by an external trigger (a
     scheduled GitHub Actions workflow - see .github/workflows/) via
     POST /push/run-daily, because Render's free tier sleeps the app when
     idle and has no built-in cron of its own. Reuses
     notebook_item_service.get_upcoming() (the exact same "sắp tới" list the
     Dashboard shows) so the two never drift apart, then pushes ONE
     notification per subscribed device summarizing everything due within
     `settings.push_reminder_days` (default 3) days - sent every day the
     window still contains that event, which is the "nhắc hàng ngày trong
     vòng 3 ngày" behavior the user asked for (not a one-time ping).
"""

import json
import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import push_repository as repo
from app.schemas.notebook_item import UpcomingReminder
from app.schemas.push import PushSubscriptionCreate, RunDailyResult
from app.services.notebook_item_service import get_upcoming

logger = logging.getLogger("vibeapp.push")
settings = get_settings()


def is_configured() -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key)


def get_vapid_public_key() -> str:
    return settings.vapid_public_key


def subscribe(db: Session, payload: PushSubscriptionCreate, user_id: int | None):
    data = {
        "endpoint": payload.endpoint,
        "p256dh": payload.keys.p256dh,
        "auth": payload.keys.auth,
        "user_id": user_id,
        "user_agent": payload.user_agent,
    }
    return repo.upsert(db, data)


def unsubscribe(db: Session, endpoint: str) -> bool:
    return repo.delete_by_endpoint(db, endpoint)


def _format_notification(reminders: list[UpcomingReminder]) -> tuple[str, str]:
    """Build (title, body) for one push notification out of today's list of
    upcoming reminders - one combined notification per day rather than one
    per event, so a busy 3-day window doesn't spam multiple pushes at once."""
    if len(reminders) == 1:
        r = reminders[0]
        title = f"🔔 {r.item.title}"
        body = "Hôm nay!" if r.days_until == 0 else f"Còn {r.days_until} ngày nữa"
        return title, body

    title = f"🔔 {len(reminders)} sự kiện sắp tới"
    lines = []
    for r in reminders[:6]:
        when = "hôm nay" if r.days_until == 0 else f"{r.days_until} ngày nữa"
        lines.append(f"• {r.item.title} ({when})")
    if len(reminders) > 6:
        lines.append(f"… và {len(reminders) - 6} mục khác")
    return title, "\n".join(lines)


def send_daily_reminders(db: Session) -> RunDailyResult:
    reminders = get_upcoming(db, days=settings.push_reminder_days)
    subscriptions = repo.list_all(db)

    if not reminders or not subscriptions or not is_configured():
        return RunDailyResult(
            reminders_found=len(reminders), notifications_sent=0,
            subscriptions_removed=0,
        )

    from pywebpush import WebPushException, webpush

    title, body = _format_notification(reminders)
    payload = json.dumps({"title": title, "body": body})
    vapid_claims = {"sub": f"mailto:{settings.vapid_claim_email}"}

    sent = 0
    removed = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims=dict(vapid_claims),
            )
            sent += 1
        except WebPushException as e:
            status_code = getattr(e.response, "status_code", None)
            if status_code in (404, 410):
                # The browser/OS says this subscription no longer exists
                # (uninstalled, notifications revoked, endpoint rotated) -
                # clean it up so future runs don't keep retrying it.
                repo.delete(db, sub)
                removed += 1
            else:
                logger.warning(
                    "Gửi thông báo thất bại cho subscription id=%s: %s",
                    sub.id, e, exc_info=True,
                )

    return RunDailyResult(
        reminders_found=len(reminders), notifications_sent=sent,
        subscriptions_removed=removed,
    )
