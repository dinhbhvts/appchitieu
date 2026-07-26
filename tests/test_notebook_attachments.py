"""Tests for "Hồ sơ đính kèm" (file attachments) on a notebook item.

Real Google Drive calls are never made in tests - app.core.drive.upload_file
is monkeypatched to return fake Drive metadata, so these tests check the
app's own logic (validation, DB bookkeeping, soft delete) without needing
real credentials or network access.
"""

from app.core import drive
from app.core.database import SessionLocal
from app.models.notebook_attachment import NotebookAttachment


def _fake_upload(filename, mime_type, content):
    return {"id": "fake-drive-id-123", "name": filename, "webViewLink": "https://drive.google.com/file/d/fake-drive-id-123/view"}


def test_upload_list_and_soft_delete_attachment(client, monkeypatch):
    monkeypatch.setattr(drive, "upload_file", _fake_upload)

    item = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông",
    }).json()

    r = client.post(
        f"/notebook-items/{item['id']}/attachments",
        files={"file": ("cccd.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert r.status_code == 201
    att = r.json()
    assert att["file_name"] == "cccd.jpg"
    assert att["mime_type"] == "image/jpeg"
    assert att["size_bytes"] == len(b"fake-image-bytes")
    assert att["drive_link"] == "https://drive.google.com/file/d/fake-drive-id-123/view"

    rows = client.get(f"/notebook-items/{item['id']}/attachments").json()
    assert any(x["id"] == att["id"] for x in rows)

    assert client.delete(f"/notebook-attachments/{att['id']}").status_code == 200
    rows_after = client.get(f"/notebook-items/{item['id']}/attachments").json()
    assert all(x["id"] != att["id"] for x in rows_after)

    # Soft delete: still in the DB, and the Drive file id is untouched (the
    # app never deletes the actual Drive file from this flow).
    with SessionLocal() as db:
        row = db.get(NotebookAttachment, att["id"])
        assert row is not None
        assert row.is_deleted is True
        assert row.drive_file_id == "fake-drive-id-123"


def test_upload_rejects_unsupported_file_type(client, monkeypatch):
    monkeypatch.setattr(drive, "upload_file", _fake_upload)
    item = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông",
    }).json()

    r = client.post(
        f"/notebook-items/{item['id']}/attachments",
        files={"file": ("virus.exe", b"MZ...", "application/x-msdownload")},
    )
    assert r.status_code == 400


def test_upload_to_missing_item_returns_404(client, monkeypatch):
    monkeypatch.setattr(drive, "upload_file", _fake_upload)
    r = client.post(
        "/notebook-items/999999/attachments",
        files={"file": ("cccd.jpg", b"bytes", "image/jpeg")},
    )
    assert r.status_code == 404


def test_upload_without_drive_configured_returns_clear_error(client):
    # No monkeypatch here - GOOGLE_SERVICE_ACCOUNT_JSON is empty by default
    # in tests, so this should fail with a clear 400, not a crash.
    item = client.post("/notebook-items", json={
        "type": "personal_info", "title": "Bông",
    }).json()
    r = client.post(
        f"/notebook-items/{item['id']}/attachments",
        files={"file": ("cccd.jpg", b"bytes", "image/jpeg")},
    )
    assert r.status_code == 400
    assert "Google Drive" in r.json()["detail"]
