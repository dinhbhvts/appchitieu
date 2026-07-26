"""Google Drive integration for "Hồ sơ đính kèm" attachments (Sổ tay > Thông
tin cá nhân, and any other notebook item).

Design choice: a SERVICE ACCOUNT, not interactive per-user OAuth. This is a
2-person personal app with a headless backend (no browser session to run an
OAuth consent flow in, and no desire to store/refresh per-user tokens or hit
Google's "unverified app" warning screen for an unpublished app). A service
account authenticates with a JSON key and no user interaction at all - the
trade-off is that the files live in a folder the service account has access
to, not directly "My Drive", which is why setup asks you to share one folder
with it (see TRIEN_KHAI.md for the exact steps).

One-time setup (done by the app owner, not by this code):
  1. Google Cloud Console -> new project -> enable "Google Drive API".
  2. Create a Service Account -> create a JSON key -> download it.
  3. In your own Google Drive, create a folder (e.g. "VibeApp - Ho so") and
     Share it with the service account's email (looks like
     xxx@xxx.iam.gserviceaccount.com) as Editor.
  4. Set two env vars on the backend:
       GOOGLE_SERVICE_ACCOUNT_JSON = the full JSON key content (one line)
       GOOGLE_DRIVE_FOLDER_ID      = that folder's id (from its URL)

If these are not set, every function here raises DriveNotConfigured with a
Vietnamese message - nothing else in the app depends on this module.
"""

import io
import json
from functools import lru_cache

from app.core.config import get_settings


class DriveNotConfigured(Exception):
    """Attachment upload/download attempted before Google Drive was set up."""


class DriveError(Exception):
    """Google rejected the request (bad credentials, folder not shared with
    the service account, quota exceeded, malformed JSON key, ...).

    Deliberately a distinct, caught exception - NOT left to propagate as a
    raw googleapiclient/google.auth exception. An uncaught exception here
    would 500 without CORS headers (see main.py's unhandled_exception_handler
    docstring), which the browser reports as an opaque "Failed to fetch"
    instead of a message the user (or we, debugging with them) can act on.
    """


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_service_account_json and settings.google_drive_folder_id)


def _credentials():
    settings = get_settings()
    if not settings.google_service_account_json:
        raise DriveNotConfigured(
            "Chưa cấu hình Google Drive (thiếu GOOGLE_SERVICE_ACCOUNT_JSON) - "
            "xem hướng dẫn thiết lập trong TRIEN_KHAI.md."
        )
    from google.oauth2 import service_account

    try:
        info = json.loads(settings.google_service_account_json)
    except json.JSONDecodeError as e:
        raise DriveError(
            "GOOGLE_SERVICE_ACCOUNT_JSON không phải JSON hợp lệ - kiểm tra "
            "lại đã dán ĐÚNG và ĐỦ nội dung file key (mục 3C, TRIEN_KHAI.md)."
        ) from e
    try:
        return service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive"]
        )
    except Exception as e:
        raise DriveError(
            f"Không tạo được thông tin xác thực Google Drive: {e}"
        ) from e


# Cached per-process - building the API client is not free, and the service
# account credentials do not change while the process is running.
@lru_cache
def _service():
    from googleapiclient.discovery import build

    try:
        return build("drive", "v3", credentials=_credentials(), cache_discovery=False)
    except (DriveNotConfigured, DriveError):
        raise
    except Exception as e:
        raise DriveError(f"Không kết nối được tới Google Drive: {e}") from e


def upload_file(filename: str, mime_type: str, content: bytes) -> dict:
    """Upload one file into the configured shared folder.

    Returns Drive's file metadata: {"id", "name", "webViewLink"}.

    Raises DriveNotConfigured if the env vars aren't set, or DriveError for
    any failure talking to Google (bad credentials, folder not shared with
    the service account, quota, network...) - never lets a raw
    googleapiclient/google.auth exception escape uncaught.
    """
    settings = get_settings()
    if not settings.google_drive_folder_id:
        raise DriveNotConfigured(
            "Chưa cấu hình Google Drive (thiếu GOOGLE_DRIVE_FOLDER_ID) - "
            "xem hướng dẫn thiết lập trong TRIEN_KHAI.md."
        )
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
    metadata = {"name": filename, "parents": [settings.google_drive_folder_id]}
    try:
        return (
            _service()
            .files()
            .create(body=metadata, media_body=media, fields="id, name, webViewLink")
            .execute()
        )
    except (DriveNotConfigured, DriveError):
        raise
    except Exception as e:
        # Most common real-world cause: the shared folder ID is wrong, or the
        # folder was never actually shared with the service account's email
        # (mục 3C bước 4, TRIEN_KHAI.md) - Google then rejects the upload
        # with a permission/not-found error.
        raise DriveError(
            "Tải file lên Google Drive thất bại. Kiểm tra lại: (1) đã share "
            "thư mục Drive với đúng email service account (dạng "
            "...@...iam.gserviceaccount.com) quyền Editor, (2) "
            "GOOGLE_DRIVE_FOLDER_ID đúng với thư mục đó. "
            f"Chi tiết lỗi: {e}"
        ) from e


def delete_file(drive_file_id: str) -> None:
    """Permanently remove a file from Drive.

    NOT called by the normal "xóa" flow in the app (that only soft-deletes
    the NotebookAttachment row, per the app-wide soft-delete rule - the file
    stays safely on Drive). This exists for a future hard-purge/admin tool,
    and is best-effort: failures are swallowed since the DB row is always the
    source of truth for what the app shows, and a stray Drive file is
    harmless (just takes a little space in the shared folder).
    """
    try:
        _service().files().delete(fileId=drive_file_id).execute()
    except Exception:
        pass
