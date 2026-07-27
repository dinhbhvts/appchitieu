"""Google Drive integration for "Hồ sơ đính kèm" attachments (Sổ tay > Thông
tin cá nhân, and any other notebook item).

Design choice: OAuth2 as the app owner's OWN Google account (a stored,
long-lived refresh token) - NOT a service account. A service account was the
original design (see git history), but it turned out to be a dead end for
this app: Google service accounts have ZERO storage quota of their own, and
can only create files in a paid Google Workspace "Shared Drive" - never in a
regular personal "My Drive" folder, even one explicitly shared with the
service account as Editor. Every upload attempt against a normal Gmail
account's folder fails with `storageQuotaExceeded`. Since this app is built
for a personal (non-Workspace) Google account, OAuth as the real user is the
only option that actually works - the trade-off (a one-time interactive
login instead of a headless JSON key) is unavoidable, not a preference.

One-time setup (done by the app owner, not by this code) - see TRIEN_KHAI.md
mục 3C for the full walkthrough:
  1. Google Cloud Console -> new project -> enable "Google Drive API".
  2. Create an OAuth Client ID (type "Desktop app") -> download its JSON.
  3. Run `python backend/scripts/get_drive_refresh_token.py` ONCE on your own
     computer (not the server) - it opens a browser, you log into your own
     Google account and approve access, and it prints a refresh token.
  4. In your own Google Drive, create a folder (e.g. "VibeApp - Hồ sơ") and
     take its Folder ID from the URL - no sharing step needed, it's already
     your own folder.
  5. Set four env vars on the backend: GOOGLE_OAUTH_CLIENT_ID,
     GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN (from step 3),
     GOOGLE_DRIVE_FOLDER_ID (from step 4).

If these are not set, every function here raises DriveNotConfigured with a
Vietnamese message - nothing else in the app depends on this module.
"""

import io
import logging
import traceback
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger("vibeapp.drive")

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveNotConfigured(Exception):
    """Attachment upload/download attempted before Google Drive was set up."""


class DriveError(Exception):
    """Google rejected the request (revoked/expired refresh token, wrong
    folder id, quota, ...).

    Deliberately a distinct, caught exception - NOT left to propagate as a
    raw googleapiclient/google.auth exception. An uncaught exception here
    would 500 without CORS headers (see main.py's unhandled_exception_handler
    docstring), which the browser reports as an opaque "Failed to fetch"
    instead of a message the user (or we, debugging with them) can act on.
    """


def is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_oauth_refresh_token
        and settings.google_drive_folder_id
    )


def _credentials():
    """Build OAuth2 user credentials from the stored refresh token, and
    immediately exchange it for a fresh access token.

    Doing the refresh here (rather than letting googleapiclient refresh
    lazily on first use) means a revoked/expired refresh token surfaces as a
    clear DriveError right away instead of a confusing failure deeper inside
    the upload call.
    """
    settings = get_settings()
    missing = [
        name for name, val in (
            ("GOOGLE_OAUTH_CLIENT_ID", settings.google_oauth_client_id),
            ("GOOGLE_OAUTH_CLIENT_SECRET", settings.google_oauth_client_secret),
            ("GOOGLE_OAUTH_REFRESH_TOKEN", settings.google_oauth_refresh_token),
        ) if not val
    ]
    if missing:
        raise DriveNotConfigured(
            f"Chưa cấu hình Google Drive (thiếu {', '.join(missing)}) - "
            "xem hướng dẫn thiết lập trong TRIEN_KHAI.md mục 3C."
        )

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=None,
        refresh_token=settings.google_oauth_refresh_token,
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        token_uri=_TOKEN_URI,
        scopes=_SCOPES,
    )
    try:
        creds.refresh(Request())
    except Exception as e:
        logger.error("Lỗi làm mới access token Google Drive:\n%s", traceback.format_exc())
        raise DriveError(
            "Không làm mới được quyền truy cập Google Drive - refresh token có "
            "thể đã hết hạn hoặc bị thu hồi (thường do đổi mật khẩu Google, hoặc "
            "chưa dùng tới quá 6 tháng với app ở trạng thái Testing). Chạy lại "
            "backend/scripts/get_drive_refresh_token.py để lấy refresh token mới, "
            f"rồi cập nhật GOOGLE_OAUTH_REFRESH_TOKEN. Chi tiết: {_describe_exception(e)}"
        ) from e
    return creds


# Cached per-process - building the API client is not free. Credentials are
# rebuilt (and refreshed) on every call to _credentials(), so a revoked token
# is still caught promptly even though the client object itself is cached.
@lru_cache
def _service():
    from googleapiclient.discovery import build

    try:
        return build("drive", "v3", credentials=_credentials(), cache_discovery=False)
    except (DriveNotConfigured, DriveError):
        raise
    except Exception as e:
        logger.error("Lỗi khởi tạo Google Drive client:\n%s", traceback.format_exc())
        raise DriveError(
            f"Không kết nối được tới Google Drive: {_describe_exception(e)}"
        ) from e


def upload_file(
    filename: str, mime_type: str, content: bytes, parent_folder_id: str | None = None,
) -> dict:
    """Upload one file into a Drive folder (in the app owner's own Google
    Drive - authenticated as that user, not a service account).

    `parent_folder_id` defaults to the shared GOOGLE_DRIVE_FOLDER_ID; pass a
    specific subfolder id (e.g. a personal_info row's own folder from
    create_folder()) to file it there instead - see
    notebook_attachment_service.upload_attachment.

    Returns Drive's file metadata: {"id", "name", "webViewLink"}.

    Raises DriveNotConfigured if the env vars aren't set, or DriveError for
    any failure talking to Google (expired/revoked token, wrong folder id,
    quota, network...) - never lets a raw googleapiclient/google.auth
    exception escape uncaught.
    """
    settings = get_settings()
    if not settings.google_drive_folder_id:
        raise DriveNotConfigured(
            "Chưa cấu hình Google Drive (thiếu GOOGLE_DRIVE_FOLDER_ID) - "
            "xem hướng dẫn thiết lập trong TRIEN_KHAI.md mục 3C."
        )
    folder_id = parent_folder_id or settings.google_drive_folder_id
    from googleapiclient.http import MediaIoBaseUpload

    # Credentials are re-fetched (and refreshed) directly here rather than
    # relying only on the cached _service() client, since an access token
    # obtained at process-start can expire (~1h) long before the process
    # restarts - _service()'s cache is for the API client object, not the
    # token; googleapiclient does auto-refresh internally too, but calling
    # _credentials() up front turns an expired/revoked token into a clear
    # DriveError immediately instead of a confusing mid-call failure.
    _credentials()
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
    metadata = {"name": filename, "parents": [folder_id]}
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
        # Most common real-world cause: GOOGLE_DRIVE_FOLDER_ID is wrong, or
        # points at a folder this Google account can't write to. Logged with
        # full traceback here (this except block converts to a caught
        # DriveError -> HTTPException in the route, which never goes through
        # main.py's unhandled-exception logger) so the real cause is visible
        # in server logs even when str(e) itself is unhelpful/empty.
        logger.error("Lỗi tải file lên Google Drive:\n%s", traceback.format_exc())
        raise DriveError(
            "Tải file lên Google Drive thất bại. Kiểm tra lại: (1) "
            f"GOOGLE_DRIVE_FOLDER_ID (đang dùng: {settings.google_drive_folder_id}) "
            "đúng với ID thư mục trong Drive của chính tài khoản đã đăng nhập lúc "
            "lấy refresh token (lấy ID từ URL thư mục, không phải cả đường link), "
            "(2) thư mục đó chưa bị xóa/di chuyển. "
            f"Chi tiết lỗi: {_describe_exception(e)}"
        ) from e


def create_folder(name: str, parent_folder_id: str | None = None) -> dict:
    """Create a subfolder inside a Drive folder (defaults to the shared
    GOOGLE_DRIVE_FOLDER_ID) - used to give each personal_info row ("Tên hồ
    sơ") its own folder for attachments.

    Returns Drive's folder metadata: {"id", "name"}. Raises the same
    DriveNotConfigured/DriveError as upload_file.
    """
    settings = get_settings()
    if not settings.google_drive_folder_id:
        raise DriveNotConfigured(
            "Chưa cấu hình Google Drive (thiếu GOOGLE_DRIVE_FOLDER_ID) - "
            "xem hướng dẫn thiết lập trong TRIEN_KHAI.md mục 3C."
        )
    folder_id = parent_folder_id or settings.google_drive_folder_id
    _credentials()
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [folder_id],
    }
    try:
        return _service().files().create(body=metadata, fields="id, name").execute()
    except (DriveNotConfigured, DriveError):
        raise
    except Exception as e:
        logger.error("Lỗi tạo thư mục Google Drive:\n%s", traceback.format_exc())
        raise DriveError(
            f"Tạo thư mục hồ sơ trên Google Drive thất bại. Chi tiết lỗi: {_describe_exception(e)}"
        ) from e


def rename_file(drive_file_id: str, new_name: str) -> dict:
    """Rename a file already on Drive (keeps the same content/id/link) - used
    when the user renames an attachment in the app, to keep the Drive file
    name in sync. Raises the same DriveNotConfigured/DriveError as upload_file."""
    _credentials()
    try:
        return (
            _service()
            .files()
            .update(fileId=drive_file_id, body={"name": new_name}, fields="id, name")
            .execute()
        )
    except (DriveNotConfigured, DriveError):
        raise
    except Exception as e:
        logger.error("Lỗi đổi tên file trên Google Drive:\n%s", traceback.format_exc())
        raise DriveError(
            f"Đổi tên file trên Google Drive thất bại. Chi tiết lỗi: {_describe_exception(e)}"
        ) from e


def _describe_exception(e: Exception) -> str:
    """Human-readable detail for an exception that may stringify to nothing
    useful on its own (notably googleapiclient.errors.HttpError, whose
    str() can come back blank depending on the response shape - the real
    info lives in e.resp.status / e.content, not in str(e))."""
    try:
        from googleapiclient.errors import HttpError

        if isinstance(e, HttpError):
            status = getattr(e.resp, "status", "?")
            reason = getattr(e.resp, "reason", "") or ""
            body = e.content
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="replace")
            body = (body or "").strip()
            return f"HTTP {status} {reason} - {body or '(không có nội dung phản hồi)'}"
    except ImportError:
        pass
    text = str(e).strip()
    return f"{e.__class__.__name__}: {text}" if text else (
        f"{e.__class__.__name__} (không có thông tin chi tiết - xem log server)"
    )


def delete_file(drive_file_id: str) -> None:
    """Permanently remove a file from Drive.

    Called by notebook_attachment_service.delete_attachment() alongside the
    normal soft-delete of the NotebookAttachment row - the user explicitly
    asked for "xóa file thì cũng tự động xóa file tương ứng trên drive", so
    unlike every other soft-deleted table in this app, deleting an attachment
    DOES remove the real file, not just hide the DB row.

    Best-effort: failures are swallowed. The DB row's is_deleted is always
    the source of truth for what the app shows, so if Drive is briefly
    unreachable the file just becomes an orphan on Drive (harmless, just
    takes a little space) rather than blocking the user's delete action.
    """
    try:
        _service().files().delete(fileId=drive_file_id).execute()
    except Exception:
        pass
