"""PushSubscription model - one row per browser/device that turned on "Bật
thông báo" (Web Push, RFC 8030), for the daily upcoming-event reminder.

Each row is exactly what the browser's `PushManager.subscribe()` call
returns (endpoint + keys.p256dh + keys.auth) - the three values a server
needs to encrypt and send a push message via VAPID (see
app/services/push_service.py). `user_id` just records who was logged in when
the device subscribed, for the settings screen ("thiết bị này đã bật cho
Chồng/Vợ") - notifications themselves are NOT filtered by user, because the
family notebook (Sổ tay) is shared: both partners should see every upcoming
birthday/ngày giỗ/task, not just their own.

A subscription is per-BROWSER-INSTALL, not per-login-session: the same phone
keeps the same `endpoint` across logins/logouts (it's issued by the OS push
service - FCM for Chrome/Android, APNs for Safari/iOS - not by this app), so
`endpoint` is unique and re-subscribing just updates the row instead of
creating a duplicate.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The push service URL the browser gave us (unique per browser+device
    # install) - this is what we POST the encrypted message to.
    endpoint: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="URL dịch vụ push của trình duyệt (FCM/APNs...), duy nhất "
                "cho mỗi thiết bị/trình duyệt đã Bật thông báo.",
    )
    # Public key + auth secret from the subscription's `keys` object, used to
    # encrypt the push payload (aes128gcm, RFC 8291) - see push_service.py.
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)

    # Who was logged in when this device subscribed (informational only -
    # see module docstring for why sending is NOT filtered by this).
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Free-text browser/OS hint (navigator.userAgent), shown in a future
    # "quản lý thiết bị đã bật thông báo" list so the user can tell devices
    # apart (e.g. "Chrome trên Android" vs "Safari trên iPhone").
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
