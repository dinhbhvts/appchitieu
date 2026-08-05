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


def test_personal_info_fields_roundtrip(client):
    r = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông",
        "full_name": "Nguyễn Thị Bông", "date1": "2018-03-10",
        "phone": "0987654321", "id_number": "001234567890",
        "id_issued_date": "2024-01-15", "id_issued_place": "Cục CS QLHC về TTXH",
        "date2": "2034-01-15", "birth_cert_no": "12/2018/KS",
        "health_insurance_no": "HS4123456789012",
        "address": "Yên Lạc - Vĩnh Phúc", "hometown": "Vĩnh Phúc",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["full_name"] == "Nguyễn Thị Bông"
    assert data["id_number"] == "001234567890"
    assert data["id_issued_place"] == "Cục CS QLHC về TTXH"
    assert data["birth_cert_no"] == "12/2018/KS"
    assert data["health_insurance_no"] == "HS4123456789012"
    assert data["hometown"] == "Vĩnh Phúc"

    # Searchable by the new fields too.
    found = client.get("/notebook-items", params={"q": "001234567890"}).json()
    assert any(x["id"] == data["id"] for x in found)


def test_profile_name_creates_drive_folder_and_uploads_land_there(client, monkeypatch):
    """Saving a personal_info row with a "Tên hồ sơ" auto-creates a Drive
    subfolder, and later attachment uploads for that row go into it."""
    from app.core import drive

    created_folders = []

    def fake_create_folder(name, parent_folder_id=None):
        created_folders.append(name)
        return {"id": "folder-abc", "name": name}

    upload_calls = []

    def fake_upload(filename, mime_type, content, parent_folder_id=None):
        upload_calls.append(parent_folder_id)
        return {"id": "file-xyz", "name": filename, "webViewLink": "https://drive/x"}

    monkeypatch.setattr(drive, "create_folder", fake_create_folder)
    monkeypatch.setattr(drive, "upload_file", fake_upload)

    r = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông", "profile_name": "Hồ sơ Bông",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["profile_name"] == "Hồ sơ Bông"
    assert created_folders == ["Hồ sơ Bông"]

    client.post(
        f"/notebook-items/{data['id']}/attachments",
        files={"file": ("cccd.jpg", b"bytes", "image/jpeg")},
    )
    assert upload_calls == ["folder-abc"]


def test_profile_name_cannot_be_changed_after_creation(client, monkeypatch):
    from app.core import drive
    monkeypatch.setattr(
        drive, "create_folder",
        lambda name, parent_folder_id=None: {"id": "folder-abc", "name": name},
    )

    created = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông", "profile_name": "Hồ sơ Bông",
    }).json()

    # NotebookItemUpdate has no profile_name field at all - sending one is
    # silently ignored, never changes the stored value.
    r = client.put(f"/notebook-items/{created['id']}", json={
        "title": "Bông (đã sửa)", "profile_name": "Tên khác",
    })
    assert r.status_code == 200
    assert r.json()["profile_name"] == "Hồ sơ Bông"


def test_profile_name_missing_drive_config_does_not_block_save(client):
    """No monkeypatch - Drive isn't configured in tests, so folder creation
    fails, but saving the personal_info row must still succeed (attachments
    just fall back to the shared root folder)."""
    r = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông", "profile_name": "Hồ sơ Bông",
    })
    assert r.status_code == 201
    assert r.json()["profile_name"] == "Hồ sơ Bông"


def test_task_type_and_upcoming_due_date(client):
    import datetime
    today = datetime.date.today()
    due = today + datetime.timedelta(days=3)

    r = client.post("/notebook-items", json={
        "type": "task", "title": "Đóng học phí",
        "info": "Nộp học phí kỳ 2 cho con",
        "date2": due.isoformat(), "tags": "#hoc_phi",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["info"] == "Nộp học phí kỳ 2 cho con"

    upcoming = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    match = next((u for u in upcoming if u["item"]["title"] == "Đóng học phí"), None)
    assert match is not None
    assert match["occurs_on"] == due.isoformat()


def test_task_defaults_to_not_completed(client):
    r = client.post("/notebook-items", json={"type": "task", "title": "Việc mới"})
    assert r.json()["is_completed"] is False


def test_completed_task_hidden_from_upcoming_and_calendar(client):
    """Tich 'Da hoan thanh' -> bien mat khoi Dashboard (upcoming) VA khoi
    dau cham su kien tren lich thang, du han van con trong 3 ngay toi -
    day cung la nguon du lieu push_service dung de gui thong bao, nen viec
    da xong tu dong ngung duoc nhac."""
    import datetime
    today = datetime.date.today()
    due = today + datetime.timedelta(days=2)

    r = client.post("/notebook-items", json={
        "type": "task", "title": "Nộp báo cáo", "date2": due.isoformat(),
    })
    item_id = r.json()["id"]

    upcoming = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    assert any(u["item"]["title"] == "Nộp báo cáo" for u in upcoming)
    events = client.get("/notebook-items/calendar-events",
                         params={"year": due.year, "month": due.month}).json()
    assert any(e["title"] == "Nộp báo cáo" for e in events)

    r2 = client.put(f"/notebook-items/{item_id}", json={"is_completed": True})
    assert r2.status_code == 200
    assert r2.json()["is_completed"] is True

    upcoming2 = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    assert all(u["item"]["title"] != "Nộp báo cáo" for u in upcoming2)
    events2 = client.get("/notebook-items/calendar-events",
                          params={"year": due.year, "month": due.month}).json()
    assert all(e["title"] != "Nộp báo cáo" for e in events2)

    # Van con trong danh sach chung (Tien ich) de xem lai lich su - chi an
    # khoi cac cho "sap toi", khong bi xoa.
    still_listed = client.get("/notebook-items", params={"type": "task"}).json()
    assert any(x["title"] == "Nộp báo cáo" and x["is_completed"] for x in still_listed)


def test_personal_info_birthday_reminder_default_on(client):
    """remind_birthday defaults to True - Ngày sinh của Thông tin cá nhân tự
    động lên danh sách nhắc nhở, giống type=birthday."""
    import datetime
    today = datetime.date.today()
    soon = today + datetime.timedelta(days=7)
    r = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông",
        "date1": f"2018-{soon.month:02d}-{soon.day:02d}",
    })
    assert r.json()["remind_birthday"] is True

    upcoming = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    assert any(u["item"]["title"] == "Bông" for u in upcoming)


def test_personal_info_birthday_reminder_can_be_turned_off(client):
    """Untick remind_birthday (vd: đã có bản ghi type=birthday riêng cho
    người này) -> KHÔNG xuất hiện trong danh sách nhắc nhở."""
    import datetime
    today = datetime.date.today()
    soon = today + datetime.timedelta(days=7)
    r = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông 2",
        "date1": f"2018-{soon.month:02d}-{soon.day:02d}",
        "remind_birthday": False,
    })
    assert r.json()["remind_birthday"] is False

    upcoming = client.get("/notebook-items/upcoming", params={"days": 30}).json()
    assert all(u["item"]["title"] != "Bông 2" for u in upcoming)


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


# ---- /notebook-items/calendar-events (highlight dots on the month calendar) ----

def test_calendar_events_includes_solar_birthday_in_month(client):
    client.post("/notebook-items", json={
        "type": "birthday", "title": "Sinh nhật con", "date1": "2000-05-12",
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2027, "month": 5}).json()
    match = next(e for e in events if e["title"] == "Sinh nhật con")
    assert match["date"] == "2027-05-12"
    assert match["category"] == "birthday"


def test_calendar_events_excludes_birthday_outside_month(client):
    client.post("/notebook-items", json={
        "type": "birthday", "title": "Sinh nhật tháng khác", "date1": "2000-05-12",
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2027, "month": 6}).json()
    assert all(e["title"] != "Sinh nhật tháng khác" for e in events)


def test_calendar_events_includes_personal_info_birthday_when_remind_on(client):
    client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông", "date1": "2018-09-03",
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2027, "month": 9}).json()
    match = next(e for e in events if e["title"] == "Bông")
    assert match["date"] == "2027-09-03"
    assert match["category"] == "birthday"


def test_calendar_events_excludes_personal_info_when_remind_off(client):
    client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông 2", "date1": "2018-09-03",
        "remind_birthday": False,
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2027, "month": 9}).json()
    assert all(e["title"] != "Bông 2" for e in events)


def test_calendar_events_includes_solar_anniversary(client):
    client.post("/notebook-items", json={
        "type": "anniversary", "title": "Giỗ bà", "date1": "2020-03-15",
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2030, "month": 3}).json()
    match = next(e for e in events if e["title"] == "Giỗ bà")
    assert match["date"] == "2030-03-15"
    assert match["category"] == "anniversary"


def test_calendar_events_lunar_anniversary_matches_known_conversion(client):
    # Same known fact as test_lunar.py::test_solar_to_lunar_and_back -
    # Feb 10, 2024 is mùng 1 Tết (lunar 1/1).
    client.post("/notebook-items", json={
        "type": "anniversary", "title": "Giỗ ông", "date1": "2000-01-01",
        "date1_is_lunar": True,
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2024, "month": 2}).json()
    match = next(e for e in events if e["title"] == "Giỗ ông")
    assert match["date"] == "2024-02-10"
    assert match["category"] == "anniversary"


def test_calendar_events_includes_task_due_date_in_month(client):
    client.post("/notebook-items", json={
        "type": "task", "title": "Đóng học phí", "date2": "2026-08-20",
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2026, "month": 8}).json()
    match = next(e for e in events if e["title"] == "Đóng học phí")
    assert match["date"] == "2026-08-20"
    assert match["category"] == "task"


def test_calendar_events_excludes_task_outside_month(client):
    client.post("/notebook-items", json={
        "type": "task", "title": "Việc tháng sau", "date2": "2026-09-01",
    })
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 2026, "month": 8}).json()
    assert all(e["title"] != "Việc tháng sau" for e in events)


def test_calendar_events_empty_month_returns_empty_list(client):
    events = client.get("/notebook-items/calendar-events",
                         params={"year": 1999, "month": 1}).json()
    assert events == []
