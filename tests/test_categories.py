"""Tests for the category config endpoints (create, edit, hide - never delete)."""


def test_create_category_with_icon(client):
    r = client.post("/categories", json={
        "name": "Xăng xe", "kind": "expense", "icon": "⛽",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Xăng xe"
    assert data["icon"] == "⛽"
    assert data["is_default"] is False
    assert data["is_active"] is True


def test_update_category_rename_and_icon(client):
    created = client.post("/categories", json={
        "name": "Tam", "kind": "expense",
    }).json()

    r = client.put(f"/categories/{created['id']}", json={
        "name": "Sua chua", "icon": "🔧",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Sua chua"
    assert data["icon"] == "🔧"


def test_hide_category_removes_it_from_default_list_but_keeps_it_with_include_inactive(client):
    created = client.post("/categories", json={
        "name": "Se an", "kind": "expense",
    }).json()

    hidden = client.put(f"/categories/{created['id']}", json={"is_active": False}).json()
    assert hidden["is_active"] is False

    active_only = client.get("/categories").json()
    assert all(c["id"] != created["id"] for c in active_only)

    with_inactive = client.get("/categories", params={"include_inactive": True}).json()
    assert any(c["id"] == created["id"] for c in with_inactive)


def test_no_delete_route_exists(client):
    created = client.post("/categories", json={
        "name": "Khong the xoa", "kind": "expense",
    }).json()

    r = client.delete(f"/categories/{created['id']}")
    # There is no DELETE route for categories on purpose - it must not exist
    # (405 Method Not Allowed), and the row must still be readable afterwards.
    assert r.status_code == 405

    still_there = client.get("/categories", params={"include_inactive": True}).json()
    assert any(c["id"] == created["id"] for c in still_there)


def test_update_missing_category_returns_404(client):
    r = client.put("/categories/999999", json={"name": "x"})
    assert r.status_code == 404
