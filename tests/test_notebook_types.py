"""Tests for notebook types (danh mục tiện ích) + the account password
encryption round-trip, since both changed together."""


def test_default_types_are_seeded(client):
    types = client.get("/notebook-types").json()
    keys = {t["key"] for t in types}
    assert {"address", "birthday", "anniversary", "service", "maintenance",
            "account", "note", "child_milestone"} <= keys
    assert all(t["is_default"] for t in types)


def test_create_custom_type_derives_key_from_name(client):
    r = client.post("/notebook-types", json={"name": "Ghi số điện nước", "icon": "💧"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Ghi số điện nước"
    assert data["is_default"] is False
    assert data["key"]  # auto-derived, non-empty
    assert data["key"] != "Ghi số điện nước"  # ASCII slug, not the raw name


def test_duplicate_name_gets_unique_key(client):
    a = client.post("/notebook-types", json={"name": "Xe cộ"}).json()
    b = client.post("/notebook-types", json={"name": "Xe cộ"}).json()
    assert a["key"] != b["key"]


def test_hide_type_removes_from_default_list_but_keeps_with_include_inactive(client):
    created = client.post("/notebook-types", json={"name": "Thử nghiệm"}).json()
    hidden = client.put(f"/notebook-types/{created['id']}", json={"is_active": False}).json()
    assert hidden["is_active"] is False

    active_only = client.get("/notebook-types").json()
    assert all(t["id"] != created["id"] for t in active_only)

    with_inactive = client.get("/notebook-types", params={"include_inactive": True}).json()
    assert any(t["id"] == created["id"] for t in with_inactive)


def test_no_delete_route_for_notebook_types(client):
    created = client.post("/notebook-types", json={"name": "Không xóa được"}).json()
    r = client.delete(f"/notebook-types/{created['id']}")
    assert r.status_code == 405


def test_creating_item_with_unknown_type_is_rejected(client):
    r = client.post("/notebook-items", json={"type": "khong_ton_tai", "title": "x"})
    assert r.status_code == 400


def test_account_password_is_encrypted_at_rest_and_decrypted_on_read(client):
    r = client.post("/notebook-items", json={
        "type": "account", "title": "Netflix nhà", "system": "Netflix",
        "relation": "Chồng", "username": "chong@example.com",
        "password": "matkhau_bi_mat_123",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["password"] == "matkhau_bi_mat_123"  # decrypted back correctly
    assert data["username"] == "chong@example.com"
    assert data["system"] == "Netflix"

    # The row in the DB must NOT contain the plaintext password anywhere.
    from app.core.database import SessionLocal
    from app.models.notebook_item import NotebookItem
    with SessionLocal() as db:
        row = db.get(NotebookItem, data["id"])
        assert row.password_encrypted is not None
        assert "matkhau_bi_mat_123" not in row.password_encrypted

    # Reading it back through the list endpoint also decrypts correctly.
    listed = client.get("/notebook-items", params={"type": "account"}).json()
    assert any(x["password"] == "matkhau_bi_mat_123" for x in listed)


def test_update_account_password(client):
    created = client.post("/notebook-items", json={
        "type": "account", "title": "Wifi nhà", "password": "mk_cu",
    }).json()
    updated = client.put(f"/notebook-items/{created['id']}", json={"password": "mk_moi"}).json()
    assert updated["password"] == "mk_moi"


def test_custom_type_item_uses_info_field(client):
    ttype = client.post("/notebook-types", json={"name": "Số đo quần áo"}).json()
    r = client.post("/notebook-items", json={
        "type": ttype["key"], "title": "Áo sơ mi chồng",
        "info": "Cổ 40, tay dài", "tags": "#quanao", "note": "Mua ở Owen",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["info"] == "Cổ 40, tay dài"
