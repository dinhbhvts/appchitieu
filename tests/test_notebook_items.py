"""Tests for the family notebook ("Sổ tay") endpoints: CRUD + search."""


def test_create_and_list_address(client):
    r = client.post("/notebook-items", json={
        "type": "address", "title": "Bố", "relation": "Bố",
        "phone": "0981234567", "address": "Yên Lạc - Vĩnh Phúc",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "address"
    assert data["title"] == "Bố"

    rows = client.get("/notebook-items").json()
    assert any(x["title"] == "Bố" for x in rows)


def test_filter_by_type(client):
    client.post("/notebook-items", json={"type": "address", "title": "Mẹ"})
    client.post("/notebook-items", json={
        "type": "birthday", "title": "Con", "date1": "2020-05-12",
    })

    addresses = client.get("/notebook-items", params={"type": "address"}).json()
    assert all(x["type"] == "address" for x in addresses)
    assert any(x["title"] == "Mẹ" for x in addresses)

    birthdays = client.get("/notebook-items", params={"type": "birthday"}).json()
    assert all(x["type"] == "birthday" for x in birthdays)


def test_anniversary_with_lunar_flag(client):
    r = client.post("/notebook-items", json={
        "type": "anniversary", "title": "Ông nội", "relation": "Ông nội",
        "date1": "2020-08-18", "date1_is_lunar": True,
    })
    data = r.json()
    assert data["date1_is_lunar"] is True


def test_service_with_expiry_and_recurrence(client):
    r = client.post("/notebook-items", json={
        "type": "service", "title": "Internet VNPT",
        "date1": "2025-05-12", "date2": "2026-05-12",
        "recurrence_days": 365, "amount": 3200000,
        "note": "12+1 khuyen mai",
    })
    data = r.json()
    assert data["date2"] == "2026-05-12"
    assert data["recurrence_days"] == 365
    assert data["amount"] == 3200000


def test_search_is_approximate_and_case_insensitive(client):
    client.post("/notebook-items", json={
        "type": "maintenance", "title": "Thay lõi lọc nước", "date1": "2026-06-01",
    })
    client.post("/notebook-items", json={
        "type": "note", "title": "Mật khẩu Wifi", "note": "wifi nha 12345678",
    })

    r = client.get("/notebook-items", params={"q": "lọc"}).json()
    assert any("lọc" in x["title"] for x in r)

    # Case-insensitive, substring match on note too.
    r2 = client.get("/notebook-items", params={"q": "WIFI"}).json()
    assert any(x["title"] == "Mật khẩu Wifi" for x in r2)


def test_update_and_delete_item(client):
    created = client.post("/notebook-items", json={
        "type": "note", "title": "Kich thuoc rem cua",
    }).json()

    updated = client.put(f"/notebook-items/{created['id']}", json={
        "note": "2m x 1.5m",
    }).json()
    assert updated["note"] == "2m x 1.5m"

    r = client.delete(f"/notebook-items/{created['id']}")
    assert r.status_code == 200

    rows = client.get("/notebook-items").json()
    assert all(x["id"] != created["id"] for x in rows)


def test_update_missing_item_returns_404(client):
    r = client.put("/notebook-items/999999", json={"title": "x"})
    assert r.status_code == 404


def test_delete_missing_item_returns_404(client):
    r = client.delete("/notebook-items/999999")
    assert r.status_code == 404


def test_upcoming_includes_solar_birthday_within_window(client):
    import datetime
    today = datetime.date.today()
    soon = today + datetime.timedelta(days=10)
    client.post("/notebook-items", json={
        "type": "birthday", "title": "Sinh nhật con",
        # Store a date1 whose (month, day) match a day 10 days from now, so
        # the yearly recurrence lands inside the 30-day window regardless of
        # what year the test happens to run in.
        "date1": f"2000-{soon.month:02d}-{soon.day:02d}",
    })
    upcoming = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    assert any(u["item"]["title"] == "Sinh nhật con" for u in upcoming)
    match = next(u for u in upcoming if u["item"]["title"] == "Sinh nhật con")
    assert 0 <= match["days_until"] <= 30


def test_upcoming_excludes_items_outside_window(client):
    import datetime
    today = datetime.date.today()
    far = today + datetime.timedelta(days=200)
    client.post("/notebook-items", json={
        "type": "birthday", "title": "Sinh nhật xa",
        "date1": f"2000-{far.month:02d}-{far.day:02d}",
    })
    upcoming = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    assert all(u["item"]["title"] != "Sinh nhật xa" for u in upcoming)


def test_upcoming_includes_service_due_date(client):
    import datetime
    today = datetime.date.today()
    due = today + datetime.timedelta(days=5)
    client.post("/notebook-items", json={
        "type": "service", "title": "Internet VNPT",
        "date2": due.isoformat(),
    })
    upcoming = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    assert any(u["item"]["title"] == "Internet VNPT" and u["occurs_on"] == due.isoformat()
               for u in upcoming)


def test_upcoming_lunar_anniversary_converts_to_solar(client):
    # Just check it doesn't error and returns a solar date - the actual
    # lunar math is covered by test_lunar.py.
    client.post("/notebook-items", json={
        "type": "anniversary", "title": "Giỗ ông",
        "date1": "2000-01-01", "date1_is_lunar": True,
    })
    r = client.get("/notebook-items/upcoming", params={"days": 400})
    assert r.status_code == 200
    match = next(u for u in r.json() if u["item"]["title"] == "Giỗ ông")
    assert match["occurs_on"]
