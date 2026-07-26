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


def test_change_password(client):
    """Test changing password via PUT /users/me/password."""
    from app.core.database import SessionLocal
    from app.core.security import hash_password, verify_password
    from app.models.user import User

    # Set initial password for "Vợ".
    with SessionLocal() as db:
        u = db.query(User).filter(User.name == "Vợ").one()
        u.password_hash = hash_password("old_password")
        db.commit()

    # Login to get token.
    login_r = client.post("/auth/login",
                          json={"username": "Vợ", "password": "old_password"})
    assert login_r.status_code == 200
    token = login_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong old password -> 400.
    r = client.put("/users/me/password",
                   json={"old_password": "wrong", "new_password": "new_pwd", "confirm_password": "new_pwd"},
                   headers=headers)
    assert r.status_code == 400
    assert "hiện tại không chính xác" in r.json()["detail"]

    # Mismatch new + confirm -> 400.
    r = client.put("/users/me/password",
                   json={"old_password": "old_password", "new_password": "new1", "confirm_password": "new2"},
                   headers=headers)
    assert r.status_code == 400
    assert "không trùng khớp" in r.json()["detail"]

    # New password = old password -> 400.
    r = client.put("/users/me/password",
                   json={"old_password": "old_password", "new_password": "old_password", "confirm_password": "old_password"},
                   headers=headers)
    assert r.status_code == 400
    assert "không được trùng" in r.json()["detail"]

    # Correct change -> 200, password updated.
    r = client.put("/users/me/password",
                   json={"old_password": "old_password", "new_password": "new_password", "confirm_password": "new_password"},
                   headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Vợ"

    # Old password no longer works.
    login_r2 = client.post("/auth/login",
                           json={"username": "Vợ", "password": "old_password"})
    assert login_r2.status_code == 401

    # New password works.
    login_r3 = client.post("/auth/login",
                           json={"username": "Vợ", "password": "new_password"})
    assert login_r3.status_code == 200
