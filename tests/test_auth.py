"""Tests for login and endpoint protection."""


def test_protected_requires_login():
    # A bare client with NO Authorization header must be rejected.
    import os, tempfile
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.get("/transactions")
        assert r.status_code == 401


def test_login_flow(client):
    # Set a password for "Chồng" via the security helper, then log in.
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    with SessionLocal() as db:
        u = db.query(User).filter(User.name == "Chồng").one()
        u.password_hash = hash_password("matkhau123")
        db.commit()

    # Wrong password -> 401.
    bad = client.post("/auth/login",
                      json={"username": "Chồng", "password": "sai"})
    assert bad.status_code == 401

    # Correct password -> token + user.
    ok = client.post("/auth/login",
                     json={"username": "Chồng", "password": "matkhau123"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["user"]["name"] == "Chồng"
    assert body["access_token"]
