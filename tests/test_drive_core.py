"""Tests for the Google Drive OAuth config-checking logic in app.core.drive.

Only local logic (env-var presence checks, error messages) is tested here -
no real network calls to Google are made. The actual upload against a real
Drive account is exercised by using the app for real (see TRIEN_KHAI.md mục
3C), not by an automated test.
"""

from types import SimpleNamespace

import pytest

from app.core import drive


def _fake_settings(**overrides):
    base = dict(
        google_oauth_client_id="",
        google_oauth_client_secret="",
        google_oauth_refresh_token="",
        google_drive_folder_id="",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_is_configured_false_when_any_var_missing(monkeypatch):
    monkeypatch.setattr(drive, "get_settings", lambda: _fake_settings())
    assert drive.is_configured() is False

    # 3/4 vars set - vẫn coi là chưa cấu hình đủ (thiếu folder id).
    monkeypatch.setattr(drive, "get_settings", lambda: _fake_settings(
        google_oauth_client_id="x",
        google_oauth_client_secret="y",
        google_oauth_refresh_token="z",
    ))
    assert drive.is_configured() is False


def test_is_configured_true_when_all_vars_present(monkeypatch):
    monkeypatch.setattr(drive, "get_settings", lambda: _fake_settings(
        google_oauth_client_id="x",
        google_oauth_client_secret="y",
        google_oauth_refresh_token="z",
        google_drive_folder_id="folder123",
    ))
    assert drive.is_configured() is True


def test_credentials_raises_drive_not_configured_when_missing(monkeypatch):
    monkeypatch.setattr(drive, "get_settings", lambda: _fake_settings())
    with pytest.raises(drive.DriveNotConfigured) as exc_info:
        drive._credentials()
    msg = str(exc_info.value)
    assert "GOOGLE_OAUTH_CLIENT_ID" in msg
    assert "GOOGLE_OAUTH_CLIENT_SECRET" in msg
    assert "GOOGLE_OAUTH_REFRESH_TOKEN" in msg


def test_upload_file_raises_drive_not_configured_without_folder_id(monkeypatch):
    monkeypatch.setattr(drive, "get_settings", lambda: _fake_settings(
        google_oauth_client_id="x",
        google_oauth_client_secret="y",
        google_oauth_refresh_token="z",
        # google_drive_folder_id van rong
    ))
    with pytest.raises(drive.DriveNotConfigured) as exc_info:
        drive.upload_file("a.jpg", "image/jpeg", b"bytes")
    assert "GOOGLE_DRIVE_FOLDER_ID" in str(exc_info.value)
