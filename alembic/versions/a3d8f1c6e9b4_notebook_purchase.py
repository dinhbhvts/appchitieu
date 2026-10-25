"""notebook_types: seed Mua hàng (purchase)

Revision ID: a3d8f1c6e9b4
Revises: f7c3a9d2e5b8
Create Date: 2026-10-25 10:00:00.000000

- Seeds the new built-in type ("purchase", "Mua hàng", "🛒"). No new
  columns: its fields reuse existing notebook_items columns -
    title (Tiêu đề), document_type (Loại hàng hóa), info (Thông tin hàng
    hóa), date1 (Ngày mua hàng), address (Nơi mua hàng), tags, note,
    profile_name (Hóa đơn mua hàng) + drive_folder_id + notebook_attachments
    (Drive subfolder, handled exactly like type=document).
- Refreshes the PostgreSQL column comments of document_type / address /
  profile_name to mention the new meaning.

Written defensively (existence checks), same pattern as e6b2d8f4a1c9.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a3d8f1c6e9b4'
down_revision: str | None = 'f7c3a9d2e5b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_NOTEBOOK_TYPES = [
    ("purchase", "Mua hàng", "🛒"),
]

_COMMENTS = {
    "document_type":
        "type=document: 'Loại hồ sơ' (vd Sổ đỏ, Hợp đồng, Bằng cấp, Giấy tờ "
        "xe); type=purchase: 'Loại hàng hóa' (vd Điện tử, Gia dụng, Nội "
        "thất) - nhập tự do.",
    "address":
        "Địa chỉ (address/personal_info); type=purchase: 'Nơi mua hàng'.",
    "profile_name":
        "Chỉ áp dụng cho type=personal_info, document, purchase: 'Tên hồ sơ' "
        "(purchase: 'Hóa đơn mua hàng') - đặt 1 lần lúc tạo, dùng làm tên "
        "thư mục con trên Google Drive để chứa file đính kèm của mục này. "
        "Không cho đổi sau khi tạo (tránh lệch tên thư mục đã tạo trên Drive).",
}


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _existing_columns(conn, table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table_name)}


def upgrade() -> None:
    conn = op.get_bind()

    if conn.dialect.name == "postgresql" and _has_table(conn, "notebook_items"):
        existing = _existing_columns(conn, "notebook_items")
        for column, comment in _COMMENTS.items():
            if column in existing:
                escaped = comment.replace("'", "''")
                op.execute(f'COMMENT ON COLUMN "notebook_items"."{column}" IS \'{escaped}\'')

    if _has_table(conn, "notebook_types"):
        existing_keys = {
            row[0] for row in
            conn.execute(sa.text("SELECT key FROM notebook_types")).fetchall()
        }
        notebook_types_tbl = sa.table(
            "notebook_types",
            sa.column("key", sa.String),
            sa.column("name", sa.String),
            sa.column("icon", sa.String),
            sa.column("is_default", sa.Boolean),
            sa.column("is_active", sa.Boolean),
        )
        to_insert = [
            {"key": k, "name": n, "icon": i, "is_default": True, "is_active": True}
            for k, n, i in _NEW_NOTEBOOK_TYPES
            if k not in existing_keys
        ]
        if to_insert:
            op.bulk_insert(notebook_types_tbl, to_insert)


def downgrade() -> None:
    # Deliberately NOT removing the seeded type row - existing items may
    # reference it (FK). Same rationale as c8f1d5a3b7e2.
    pass
