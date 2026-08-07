"""Tests for the open (no-login) health-check endpoint.

/health is a plain alias of "/" - added so external wake-up pings (e.g. a
cron-job.org job hit before /push/run-daily to wake a sleeping Render
free-tier instance) have a conventional path to call, distinct from the
cron-secret protected /push/run-daily endpoint.
"""


def test_health_root_and_alias_both_ok(client):
    for path in ("/", "/health"):
        r = client.get(path)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "app" in body


def test_health_does_not_require_login():
    # Bare client, no Authorization header - must still succeed (unlike
    # protected routes, see test_auth.test_protected_requires_login).
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200
