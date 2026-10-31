"""Cấu hình > Người dùng: màu đại diện + avatar."""

import io

from PIL import Image


def _png(w=400, h=300, color=(200, 80, 120)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def test_defaults_are_null(client):
    me = client.get("/auth/me").json()
    assert me["color"] is None
    assert me["avatar_preset"] is None
    assert me["avatar_version"] == 0


def test_set_color_and_reset(client):
    r = client.patch("/users/me/profile", json={"color": "#d1f2e0"})
    assert r.status_code == 200
    assert r.json()["color"] == "#D1F2E0"
    # Danh sách users (dùng tô màu ở mọi màn) cũng trả màu mới.
    users = client.get("/users").json()
    assert any(u["color"] == "#D1F2E0" for u in users)
    # Chỉ đổi avatar thì màu giữ nguyên.
    r = client.patch("/users/me/profile", json={"avatar_preset": "chibi:3"})
    assert r.json()["color"] == "#D1F2E0"
    assert r.json()["avatar_preset"] == "chibi:3"
    assert r.json()["avatar_version"] > 0
    r = client.patch("/users/me/profile", json={"color": None})
    assert r.json()["color"] is None


def test_invalid_values_rejected(client):
    assert client.patch("/users/me/profile", json={"color": "red"}).status_code == 400
    assert client.patch("/users/me/profile", json={"avatar_preset": "chibi:99"}).status_code == 400
    assert client.patch("/users/me/profile", json={"avatar_preset": "../x"}).status_code == 400


def test_upload_avatar_square_and_served(client):
    r = client.put("/users/me/avatar", files={"file": ("a.png", _png(), "image/png")})
    assert r.status_code == 200
    me = r.json()
    assert me["avatar_preset"] == "upload"
    img = client.get(f"/users/{me['id']}/avatar")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/jpeg"
    assert Image.open(io.BytesIO(img.content)).size == (256, 256)
    # Chọn lại chibi -> ảnh tải lên bị bỏ.
    client.patch("/users/me/profile", json={"avatar_preset": "chibi:0"})
    assert client.get(f"/users/{me['id']}/avatar").status_code == 404


def test_upload_non_image_and_auth(client):
    r = client.put("/users/me/avatar", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 400
    me = client.get("/auth/me").json()
    del client.headers["Authorization"]
    assert client.get(f"/users/{me['id']}/avatar").status_code == 401
    assert client.patch("/users/me/profile", json={"color": "#FFFFFF"}).status_code == 401
