"""asset_snapshots.system_key + notebook_items.profile_name

Revision ID: c2a5f8e3b1d4
Revises: b6d4e2a9c1f7
Create Date: 2026-07-29 09:00:00.000000

Two independent, additive column adds landing together:

  - asset_snapshots.system_key: identifies the 4 pinned, auto-computed rows
    (Tài khoản/Chứng khoán vợ/chồng) on the Tài sản screen - see
    app/services/asset_service.py SYSTEM_ITEMS.
  - notebook_items.profile_name: "Tên hồ sơ" for type=personal_info, used to
    name/find that person's own subfolder in Google Drive for attachments.

Written defensively (existence checks), same pattern as e9bf8b627c97,
f3a1c9e7d8b2, b6d4e2a9c1f7 - see those migrations' docstrings for why
(notably: this repo's database can have drift from Base.metadata.create_all()
running before any migration touches a given table, so every ADD COLUMN is
guarded).
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c2a5f8e3b1d4'
down_revision: str | None = 'b6d4e2a9c1f7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(conn, table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table_name)}


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _comment_if_exists(conn, table: str, column: str, comment: str) -> None:
    if conn.dialect.name != "postgresql":
        return
    if not _has_table(conn, table) or column not in _existing_columns(conn, table):
        return
    escaped = comment.replace("'", "''")
    op.execute(f'COMMENT ON COLUMN "{table}"."{column}" IS \'{escaped}\'')


def upgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "asset_snapshots"):
        cols = _existing_columns(conn, "asset_snapshots")
        if "system_key" not in cols:
            with op.batch_alter_table("asset_snapshots") as batch_op:
                batch_op.add_column(sa.Column("system_key", sa.String(length=30), nullable=True))
            op.create_index(
                "ix_asset_snapshots_system_key", "asset_snapshots", ["system_key"],
            )
            _comment_if_exists(
                conn, "asset_snapshots", "system_key",
                "NULL = mục thường, người dùng tự nhập/sửa/xóa. Khác NULL = "
                "mục hệ thống (Tài khoản/Chứng khoán chồng/vợ), tự động tính "
                "toán mỗi lần xem, không cho sửa/xóa thủ công.",
            )

    if _has_table(conn, "notebook_items"):
        cols = _existing_columns(conn, "notebook_items")
        if "profile_name" not in cols:
            with op.batch_alter_table("notebook_items") as batch_op:
                batch_op.add_column(sa.Column("profile_name", sa.String(length=150), nullable=True))
            _comment_if_exists(
                conn, "notebook_items", "profile_name",
                "Chỉ áp dụng cho type=personal_info: 'Tên hồ sơ' - đặt 1 lần "
                "lúc tạo, dùng làm tên thư mục con trên Google Drive để chứa "
                "file đính kèm của người này. Không cho đổi sau khi tạo "
                "(tránh lệch tên thư mục đã tạo trên Drive).",
            )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "notebook_items"):
        cols = _existing_columns(conn, "notebook_items")
        if "profile_name" in cols:
            with op.batch_alter_table("notebook_items") as batch_op:
                batch_op.drop_column("profile_name")

    if _has_table(conn, "asset_snapshots"):
        idx = {i["name"] for i in sa.inspect(conn).get_indexes("asset_snapshots")}
        if "ix_asset_snapshots_system_key" in idx:
            op.drop_index("ix_asset_snapshots_system_key", table_name="asset_snapshots")
        cols = _existing_columns(conn, "asset_snapshots")
        if "system_key" in cols:
            with op.batch_alter_table("asset_snapshots") as batch_op:
                batch_op.drop_column("system_key")
