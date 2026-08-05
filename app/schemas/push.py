"""Pydantic schemas for Web Push subscriptions (thông báo nhắc sự kiện)."""

from pydantic import BaseModel, ConfigDict


class PushSubscriptionKeys(BaseModel):
    """Matches the `keys` object inside the browser's
    `PushSubscription.toJSON()` output exactly - field names are fixed by
    the Web Push spec, not ours to rename."""

    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """Body the frontend sends after `pushManager.subscribe()` succeeds -
    same shape as `subscription.toJSON()`, plus an optional user_agent hint
    for the future "quản lý thiết bị" list."""

    endpoint: str
    keys: PushSubscriptionKeys
    user_agent: str | None = None


class PushUnsubscribe(BaseModel):
    endpoint: str


class PushSubscriptionRead(BaseModel):
    id: int
    endpoint: str
    user_agent: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VapidPublicKeyRead(BaseModel):
    """Public key the frontend passes to `pushManager.subscribe()` as
    `applicationServerKey`. Safe to expose - it's the PUBLIC half of the
    VAPID key pair (see app/core/config.py); the private half never leaves
    the server."""

    public_key: str


class RunDailyResult(BaseModel):
    """What POST /push/run-daily returns - shown in the GitHub Actions log
    so a failed/empty run is easy to notice without digging into Render's
    logs."""

    reminders_found: int
    notifications_sent: int
    subscriptions_removed: int
