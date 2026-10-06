"""AlbumPhoto model - photos for the "khung ảnh kỹ thuật số" (digital photo
frame) at the bottom of the Tổng quan screen.

Unlike notebook attachments (which live on Google Drive), album photos are
stored DIRECTLY in this database, already downscaled by the server
(app/services/album_service.py): one display-size JPEG (longest side
~1280px, ~150-300 KB) plus a small thumbnail for the management grid. Reasons:
  - the frame shows a new photo every few seconds - serving it straight from
    our own DB is fast and has no extra dependency (no Render -> Drive hop,
    which already proved flaky for uploads);
  - photos are automatically included in the nightly pg_dump backup;
  - at ~250 KB per photo the free Neon tier (0.5 GB) still fits roughly a
    thousand photos, far more than a family photo frame needs.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.core.database import Base


class AlbumPhoto(Base):
    __tablename__ = "album_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Optional short caption shown on the frame, e.g. "Bông - Đà Lạt 2026".
    caption: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Original file name as uploaded (display/reference only).
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Display-size image (always JPEG after server-side processing). Loaded
    # lazily (deferred) so listing photos never pulls the binary data.
    image_data: Mapped[bytes] = deferred(mapped_column(
        LargeBinary, nullable=False,
        comment="Ảnh JPEG đã thu nhỏ (cạnh dài tối đa ~1280px) để hiển thị "
                "trên khung ảnh - không phải file gốc.",
    ))
    thumb_data: Mapped[bytes] = deferred(mapped_column(
        LargeBinary, nullable=False,
        comment="Ảnh thu nhỏ (cạnh dài ~320px) cho lưới quản lý album.",
    ))
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Dung lượng ảnh hiển thị (image_data) sau khi thu nhỏ, byte.",
    )

    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Soft delete, same app-wide convention as every other table.
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Xóa mềm: True = người dùng đã xóa ảnh khỏi album từ UI. "
                "Dữ liệu ảnh vẫn còn trong DB, chỉ không hiển thị nữa.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
