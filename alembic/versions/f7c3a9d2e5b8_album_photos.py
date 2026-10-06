"""album_photos table (khung ảnh kỹ thuật số ở Tổng quan)

Revision ID: f7c3a9d2e5b8
Revises: e6b2d8f4a1c9
Create Date: 2026-10-06 10:00:00.000000

Brand-new table, so on an existing database the app's startup create_all()
may already have created it before this migration runs - hence the
existence check (same defensive pattern as the earlier migrations).
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f7c3a9d2e5b8'
down_revision: str | None = 'e6b2d8f4a1c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    if sa.inspect(conn).has_table("album_photos"):
        return
    op.create_table(
        "album_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("caption", sa.String(length=200), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("image_data", sa.LargeBinary(), nullable=False,
                  comment="Ảnh JPEG đã thu nhỏ (cạnh dài tối đa ~1280px) để hiển thị "
                          "trên khung ảnh - không phải file gốc."),
        sa.Column("thumb_data", sa.LargeBinary(), nullable=False,
                  comment="Ảnh thu nhỏ (cạnh dài ~320px) cho lưới quản lý album."),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False,
                  comment="Dung lượng ảnh hiển thị (image_data) sau khi thu nhỏ, byte."),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(),
                  comment="Xóa mềm: True = người dùng đã xóa ảnh khỏi album từ UI. "
                          "Dữ liệu ảnh vẫn còn trong DB, chỉ không hiển thị nữa."),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    conn = op.get_bind()
    if sa.inspect(conn).has_table("album_photos"):
        op.drop_table("album_photos")
