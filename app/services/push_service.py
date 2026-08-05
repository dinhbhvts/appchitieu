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

The notification text itself is picked CONTEXTUALLY, not a single generic
template - see the phrase pools below _format_notification(). A birthday
reads warm/celebratory, a ngày giỗ reads respectful, a task/due-date reads
practical-but-friendly, and the exact sentence varies by how many days are
left (hôm nay / ngày mai / N ngày nữa) with a few random variants each so it
doesn't read identically day after day. The intent is for this to feel like
a family member nudging you, not a system alert.
"""

import json
import logging
import random

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import push_repository as repo
from app.schemas.notebook_item import UpcomingReminder
from app.schemas.push import PushSubscriptionCreate, RunDailyResult
from app.services.notebook_item_service import get_upcoming

logger = logging.getLogger("vibeapp.push")
settings = get_settings()

# Câu chữ theo TỪNG NGỮ CẢNH: loại sự kiện (sinh nhật / ngày giỗ / nhắc việc
# / dịch vụ-bảo trì) x số ngày còn lại (hôm nay / ngày mai / 2-3 ngày nữa).
# Mục tiêu là để thông báo đọc như một người thân đang nhắc khéo, không phải
# một dòng log hệ thống - "Còn 2 ngày nữa" đọc giống nhau dù là sinh nhật hay
# hạn nộp báo cáo thì rất máy móc, còn giọng "chúc mừng"/"kịp chuẩn bị"/trang
# trọng cho ngày giỗ mới đúng CẢM XÚC của từng loại. Mỗi ô có vài biến thể,
# chọn ngẫu nhiên mỗi lần gửi để không lặp lại y hệt ngày này qua ngày khác.
_BIRTHDAY_PHRASES = {
    0: [
        "🎉 Hôm nay là sinh nhật {title}! Đừng quên gửi một lời chúc thật ấm áp.",
        "🎂 Chúc mừng sinh nhật {title} hôm nay - một ngày đáng để cả nhà quây quần.",
    ],
    1: [
        "🎂 Ngày mai là sinh nhật {title} rồi - đã nghĩ ra món quà nho nhỏ chưa?",
        "🎁 Còn 1 ngày nữa là đến sinh nhật {title}, kịp chuẩn bị một bất ngờ nhé.",
    ],
    "default": [
        "🎂 Còn {days} ngày nữa là đến sinh nhật {title}.",
        "🎂 Sinh nhật {title} đang đến gần - còn {days} ngày nữa thôi.",
    ],
}
_ANNIVERSARY_PHRASES = {
    0: [
        "🕯️ Hôm nay là ngày giỗ {title}. Cả nhà mình cùng tưởng nhớ nhé.",
    ],
    1: [
        "🕯️ Ngày mai là ngày giỗ {title} - kịp thu xếp thời gian chuẩn bị.",
    ],
    "default": [
        "🕯️ Còn {days} ngày nữa là đến ngày giỗ {title}.",
        "🕯️ Ngày giỗ {title} sắp tới, còn {days} ngày để chuẩn bị chu đáo.",
    ],
}
_TASK_PHRASES = {
    0: [
        "⏰ Hôm nay là hạn cho việc: {title} - cố lên nhé!",
        "⏰ Đến hạn hôm nay rồi: {title}.",
    ],
    1: [
        "📝 Ngày mai đến hạn: {title}. Còn kịp thu xếp đấy.",
        "📝 Còn 1 ngày để hoàn thành: {title}.",
    ],
    "default": [
        "📝 Còn {days} ngày nữa đến hạn: {title}.",
        "📝 {title} - còn {days} ngày nữa là tới hạn, đừng để dồn việc nhé.",
    ],
}
_DUE_PHRASES = {  # service / maintenance (dich vu, bao tri)
    0: [
        "🔧 Hôm nay đến hạn: {title}.",
    ],
    1: [
        "🔧 Ngày mai đến hạn: {title} - tranh thủ xử lý sớm nhé.",
    ],
    "default": [
        "🔧 Còn {days} ngày nữa đến hạn: {title}.",
    ],
}
_BIRTHDAY_TYPES = ("birthday", "personal_info")


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


def _icon_and_pool(item_type: str) -> tuple[str, dict]:
    if item_type in _BIRTHDAY_TYPES:
        return "🎂", _BIRTHDAY_PHRASES
    if item_type == "anniversary":
        return "🕯️", _ANNIVERSARY_PHRASES
    if item_type == "task":
        return "📝", _TASK_PHRASES
    return "🔧", _DUE_PHRASES  # service / maintenance


def _sentence_for(reminder: UpcomingReminder) -> tuple[str, str]:
    """(icon, câu văn) cho một sự kiện, chọn ngẫu nhiên trong nhóm phù hợp
    loại sự kiện + số ngày còn lại - xem bảng phrase ở đầu file."""
    icon, pool = _icon_and_pool(reminder.item.type)
    choices = pool.get(reminder.days_until, pool["default"])
    sentence = random.choice(choices).format(
        title=reminder.item.title, days=reminder.days_until,
    )
    return icon, sentence


def _short_days_phrase(days: int) -> str:
    if days == 0:
        return "hôm nay"
    if days == 1:
        return "ngày mai"
    return f"còn {days} ngày"


def _format_notification(reminders: list[UpcomingReminder]) -> tuple[str, str]:
    """Build (title, body) for one push notification out of today's list of
    upcoming reminders - one combined notification per day rather than one
    per event, so a busy 3-day window doesn't spam multiple pushes at once.

    Phrasing is picked per-event based on its TYPE and how many days are
    left (see the phrase pools above), so the notification reads like a
    family member gently nudging you - warm for a birthday, respectful for
    a ngày giỗ, practical-but-friendly for a task/due date - instead of one
    flat "Còn N ngày nữa" line regardless of what's actually coming up.
    """
    if len(reminders) == 1:
        r = reminders[0]
        icon, sentence = _sentence_for(r)
        title = f"{icon} {r.item.title}"
        return title, sentence

    has_birthday = any(r.item.type in _BIRTHDAY_TYPES for r in reminders)
    has_anniversary = any(r.item.type == "anniversary" for r in reminders)
    if has_birthday:
        title = "🎂 Vài điều đặc biệt sắp tới"
    elif has_anniversary:
        title = "🕯️ Vài điều cần nhớ sắp tới"
    else:
        title = f"📝 {len(reminders)} việc sắp tới trong nhà"

    lines = []
    for r in reminders[:6]:
        icon, _ = _sentence_for(r)
        lines.append(f"{icon} {r.item.title} - {_short_days_phrase(r.days_until)}")
    if len(reminders) > 6:
        lines.append(f"… và {len(reminders) - 6} việc khác")
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
