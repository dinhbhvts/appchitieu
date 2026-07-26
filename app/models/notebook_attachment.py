"""NotebookAttachment model - "Hồ sơ đính kèm" (file attachments) on a
NotebookItem, e.g. scanned CCCD/giấy khai sinh/thẻ BHYT for type=personal_info
(though any notebook item can have attachments, not just that type).

The file CONTENT is never stored in this app's own database - it lives on the
app owner's Google Drive (see app/core/drive.py), and this row only keeps the
Drive file id/link plus display metadata. That keeps the Postgres database
small regardless of how many photos/PDFs get attached over the years, and
means the files remain fully accessible/manageable directly from Drive too.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotebookAttachment(Base):
    __tablename__ = "notebook_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    notebook_item_id: Mapped[int] = mapped_column(
        ForeignKey("notebook_items.id"), nullable=False, index=True,
    )

    # Display name shown in the app (the original uploaded filename).
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Google Drive file id (from the Drive API) - the actual file lives on
    # Drive, not in this database. drive_link is Drive's "view in browser"
    # URL, saved at upload time so the app never needs an extra Drive API
    # call just to display a link.
    drive_file_id: Mapped[str] = mapped_column(
        String(120), nullable=False,
        comment="ID file trên Google Drive của chủ app - nội dung file "
                "KHÔNG lưu trong database này, chỉ lưu tham chiếu.",
    )
    drive_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Soft delete: hides the attachment from the app but deliberately does
    # NOT delete the underlying Drive file (see app/core/drive.py - avoids a
    # UI bug ever permanently destroying a scanned document by mistake).
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Xóa mềm: ẩn khỏi danh sách trong app, nhưng KHÔNG xóa file "
                "thật trên Google Drive - file vẫn còn trên Drive nếu cần.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
