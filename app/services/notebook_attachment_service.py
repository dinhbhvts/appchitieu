"""Business logic for "Hồ sơ đính kèm" (file attachments) on a notebook item.

Files are uploaded to the app owner's Google Drive (app/core/drive.py) - only
a reference (drive_file_id/drive_link) plus display metadata is kept here.
"""

from sqlalchemy.orm import Session

from app.core import drive
from app.repositories import notebook_attachment_repository as repo
from app.repositories import notebook_item_repository as item_repo

# Kept intentionally small ("các định dạng cơ bản" - basic formats only, per
# the feature request): common image formats, PDF, and Word documents.
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

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

    Raises ValueError (-> HTTP 400) for a bad request, LookupError (-> 404)
    if the notebook item does not exist, and lets drive.DriveNotConfigured
    propagate (the route maps it to a clear error) if Drive isn't set up.
    """
    if item_repo.get(db, notebook_item_id) is None:
        raise LookupError("Không tìm thấy mục sổ tay")
    if not content:
        raise ValueError("File rỗng")
    if len(content) > MAX_SIZE_BYTES:
        raise ValueError("File quá lớn (tối đa 15MB)")
    mime = mime_type or "application/octet-stream"
    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(
            "Định dạng file không được hỗ trợ - chỉ nhận ảnh (jpg/png/webp/"
            "heic), PDF, hoặc Word (doc/docx)."
        )

    drive_file = drive.upload_file(filename, mime, content)

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


def delete_attachment(db: Session, attachment_id: int) -> bool:
    row = repo.get(db, attachment_id)
    if row is None:
        return False
    repo.delete(db, row)
    return True
