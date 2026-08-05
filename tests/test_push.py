"""Tests for Web Push subscriptions and the daily reminder job.

VAPID keys are empty in the test environment (never set via env var before
app.main is imported by conftest), so most tests exercise the
subscribe/unsubscribe/cron-secret plumbing with is_configured() == False;
send_daily_reminders() then correctly no-ops on the actual sending. The one
test that needs a real send path (test_run_daily_sends_and_prunes_expired)
mutates the cached Settings object's attributes directly and mocks
pywebpush.webpush - the same pattern works because get_settings() is
lru_cached, so every module holds the exact same Settings instance.
"""

from datetime import date, timedelta
from unittest.mock import patch

from app.api.routes import push as push_routes
from app.schemas.notebook_item import NotebookItemRead, UpcomingReminder
from app.services import push_service


def _reminder(item_type: str, title: str, days_until: int) -> UpcomingReminder:
    item = NotebookItemRead(id=1, type=item_type, title=title)
    return UpcomingReminder(item=item, occurs_on=date.today(), days_until=days_until)


def test_notification_phrasing_is_contextual_per_event_type():
    # Sinh nhật hôm nay: giọng vui mừng, có icon 🎂, nhắc "sinh nhật".
    title, body = push_service._format_notification([_reminder("birthday", "Bố", 0)])
    assert title == "🎂 Bố"
    assert "sinh nhật" in body.lower()

    # Ngày giỗ: trang trọng, không lẫn với sinh nhật.
    title, body = push_service._format_notification([_reminder("anniversary", "Ông nội", 1)])
    assert title == "🕯️ Ông nội"
    assert "giỗ" in body.lower()

    # Nhắc việc: icon 📝, câu văn thực tế ("hạn"/"hoàn thành").
    title, body = push_service._format_notification([_reminder("task", "Nộp báo cáo", 2)])
    assert title == "📝 Nộp báo cáo"
    assert "còn 2 ngày" in body.lower()


def test_notification_title_prioritizes_birthday_when_mixed():
    reminders = [
        _reminder("task", "Đóng tiền điện", 1),
        _reminder("birthday", "Mẹ", 2),
    ]
    title, body = push_service._format_notification(reminders)
    assert title == "🎂 Vài điều đặc biệt sắp tới"
    assert "Mẹ" in body and "Đóng tiền điện" in body


def _make_endpoint_payload(endpoint="https://push.example.com/ep1"):
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": "fake-p256dh", "auth": "fake-auth"},
        "user_agent": "pytest-agent",
    }


def test_vapid_public_key_endpoint(client):
    r = client.get("/push/vapid-public-key")
    assert r.status_code == 200
    assert "public_key" in r.json()


def test_subscribe_then_unsubscribe(client):
    r = client.post("/push/subscribe", json=_make_endpoint_payload())
    assert r.status_code == 201

    # Re-subscribing the same endpoint updates in place, not duplicates.
    r2 = client.post("/push/subscribe", json=_make_endpoint_payload())
    assert r2.status_code == 201

    r3 = client.request(
        "DELETE", "/push/subscribe",
        json={"endpoint": "https://push.example.com/ep1"},
    )
    assert r3.status_code == 200
    assert r3.json()["ok"] is True


def test_run_daily_requires_cron_secret(client):
    push_routes.settings.notify_cron_secret = "test-secret"
    try:
        r = client.post("/push/run-daily")
        assert r.status_code == 401

        r2 = client.post("/push/run-daily", headers={"X-Cron-Secret": "wrong"})
        assert r2.status_code == 401

        r3 = client.post("/push/run-daily", headers={"X-Cron-Secret": "test-secret"})
        assert r3.status_code == 200
    finally:
        push_routes.settings.notify_cron_secret = ""


def test_run_daily_counts_reminders_within_window(client):
    push_routes.settings.notify_cron_secret = "test-secret"
    try:
        due = (date.today() + timedelta(days=2)).isoformat()
        client.post("/notebook-items", json={
            "type": "task", "title": "Đóng học phí", "date2": due,
        })
        # Outside the 3-day window - must NOT be counted.
        far = (date.today() + timedelta(days=10)).isoformat()
        client.post("/notebook-items", json={
            "type": "task", "title": "Việc xa", "date2": far,
        })

        r = client.post("/push/run-daily", headers={"X-Cron-Secret": "test-secret"})
        assert r.status_code == 200
        body = r.json()
        assert body["reminders_found"] == 1
        # No VAPID keys configured in the test env -> no actual send attempted.
        assert body["notifications_sent"] == 0
    finally:
        push_routes.settings.notify_cron_secret = ""


def test_run_daily_sends_and_prunes_expired_subscription(client):
    client.post("/push/subscribe", json=_make_endpoint_payload("https://push.example.com/good"))
    client.post("/push/subscribe", json=_make_endpoint_payload("https://push.example.com/gone"))

    due = (date.today() + timedelta(days=1)).isoformat()
    client.post("/notebook-items", json={
        "type": "task", "title": "Nộp báo cáo", "date2": due,
    })

    push_routes.settings.notify_cron_secret = "test-secret"
    push_service.settings.vapid_public_key = "test-pub"
    push_service.settings.vapid_private_key = "test-priv"
    try:
        from pywebpush import WebPushException

        def fake_webpush(subscription_info, **kwargs):
            if subscription_info["endpoint"].endswith("/gone"):
                raise WebPushException("Gone", response=type("R", (), {"status_code": 410})())
            return None

        with patch("pywebpush.webpush", side_effect=fake_webpush):
            r = client.post("/push/run-daily", headers={"X-Cron-Secret": "test-secret"})

        assert r.status_code == 200
        body = r.json()
        assert body["reminders_found"] == 1
        assert body["notifications_sent"] == 1
        assert body["subscriptions_removed"] == 1

        # The pruned subscription should really be gone from the DB - a
        # second run only tries the surviving one, no repeat 410.
        with patch("pywebpush.webpush", side_effect=fake_webpush) as mocked:
            client.post("/push/run-daily", headers={"X-Cron-Secret": "test-secret"})
            assert mocked.call_count == 1
    finally:
        push_routes.settings.notify_cron_secret = ""
        push_service.settings.vapid_public_key = ""
        push_service.settings.vapid_private_key = ""
