"""Business logic for "Hồ sơ đính kèm" (file attachments) on a notebook item.

Files are uploaded to the app owner's Google Drive (app/core/drive.py) - only
a reference (drive_file_id/drive_link) plus display metadata is kept here.
"""

from sqlalchemy.orm import Session

from app.core import drive
from app.repositories import notebook_attachment_repository as repo
from app.repositories import notebook_item_repository as item_repo

# Kept intentionally small ("các định dạng cơ bản" - basic formats only, per
# the feature request): common image formats, PDF, Word/Excel documents, and
# rar/zip archives (added later, per a follow-up request to also allow
# spreadsheets and compressed archives).
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/zip",
    "application/x-zip-compressed",  # .zip, as reported by some browsers/OS
    "application/vnd.rar",
    "application/x-rar-compressed",  # .rar, both known Content-Type variants
}

# Browsers/OS are inconsistent about the Content-Type they report for these
# less-common formats (some send "application/octet-stream" for .xlsx/.rar/
# .zip instead of the specific type above) - so uploads are also allowed
# through by file extension as a fallback when the MIME type didn't match.
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".zip", ".rar"}

# 15 MB - generous for a scanned ID photo or a multi-page PDF, small enough
# to upload comfortably from a phone connection and stay well under typical
# request-body limits on free hosting tiers.
MAX_SIZE_BYTES = 15 * 1024 * 1024


def upload_attachment(
    db: Session,
    notebook_item_id: int,
    filename: str,
    mime_type: str | None,
    content: bytes,
    actor_id: int | None = None,
) -> "NotebookAttachment":  # noqa: F821 - forward ref for the docstring reader
    """Validate, upload to Drive, and record one attachment.

    Uploaded into the notebook item's own Drive subfolder
    (item.drive_folder_id) when it has one - i.e. a personal_info row with a
    "Tên hồ sơ" - otherwise into the shared root folder, same as before that
    feature existed.

    Raises ValueError (-> HTTP 400) for a bad request, LookupError (-> 404)
    if the notebook item does not exist, and lets drive.DriveNotConfigured
    propagate (the route maps it to a clear error) if Drive isn't set up.
    """
    item = item_repo.get(db, notebook_item_id)
    if item is None:
        raise LookupError("Không tìm thấy mục sổ tay")
    if not content:
        raise ValueError("File rỗng")
    if len(content) > MAX_SIZE_BYTES:
        raise ValueError("File quá lớn (tối đa 15MB)")
    mime = mime_type or "application/octet-stream"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if mime not in ALLOWED_MIME_TYPES and ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Định dạng file không được hỗ trợ - chỉ nhận ảnh (jpg/png/webp/"
            "heic), PDF, Word (doc/docx), Excel (xls/xlsx), hoặc file nén "
            "(zip/rar)."
        )

    drive_file = drive.upload_file(
        filename, mime, content, parent_folder_id=item.drive_folder_id,
    )

    return repo.create(db, {
        "notebook_item_id": notebook_item_id,
        "file_name": filename,
        "mime_type": mime,
        "size_bytes": len(content),
        "drive_file_id": drive_file["id"],
        "drive_link": drive_file.get("webViewLink"),
        "uploaded_by": actor_id,
    })


def list_attachments(db: Session, notebook_item_id: int):
    return repo.list_for_item(db, notebook_item_id)


def rename_attachment(db: Session, attachment_id: int, new_name: str):
    """Rename an attachment - updates both the DB row's display name AND the
    real file name on Drive, so the two never drift apart.

    Raises ValueError (-> HTTP 400) for a blank name; returns None (-> 404 in
    the route) if the attachment does not exist.
    """
    row = repo.get(db, attachment_id)
    if row is None:
        return None
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Tên file không được để trống")
    drive.rename_file(row.drive_file_id, new_name)
    return repo.update(db, row, {"file_name": new_name})


def delete_attachment(db: Session, attachment_id: int) -> bool:
    """Soft-delete the DB row AND delete the real file on Drive (per explicit
    user request - unlike every other soft-deleted table in this app, this
    one also removes the underlying file, not just the reference)."""
    row = repo.get(db, attachment_id)
    if row is None:
        return False
    drive.delete_file(row.drive_file_id)  # best-effort, see drive.py docstring
    repo.delete(db, row)
    return True
