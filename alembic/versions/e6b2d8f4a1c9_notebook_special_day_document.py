"""notebook_items.document_type/document_no + seed Ngày kỉ niệm, Hồ sơ

Revision ID: e6b2d8f4a1c9
Revises: d4a9e2b6c1f3
Create Date: 2026-10-03 10:00:00.000000

- New nullable columns notebook_items.document_type ("Loại hồ sơ") and
  notebook_items.document_no ("Số giấy tờ"), used by the new "document"
  (Hồ sơ) type. Its other fields reuse existing columns: info (Nội dung),
  date1 (Ngày), profile_name + drive_folder_id (Drive subfolder, same as
  personal_info) and notebook_attachments.
- Seeds 2 new built-in types:
    ("special_day", "Ngày kỉ niệm", "💝") - title, date1, tags, note;
      yearly recurring reminder like birthday.
    ("document", "Hồ sơ", "📂").

Written defensively (existence checks), same pattern as d4a9e2b6c1f3.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e6b2d8f4a1c9'
down_revision: str | None = 'd4a9e2b6c1f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_NOTEBOOK_TYPES = [
    ("special_day", "Ngày kỉ niệm", "💝"),
    ("document", "Hồ sơ", "📂"),
]

_NEW_COLUMNS = [
    ("document_type", 100,
     "Chỉ áp dụng cho type=document: 'Loại hồ sơ' (vd Sổ đỏ, Hợp đồng, "
     "Bằng cấp, Giấy tờ xe) - nhập tự do."),
    ("document_no", 100,
     "Chỉ áp dụng cho type=document: 'Số giấy tờ' (số sổ, số hợp đồng, "
     "số văn bằng...)."),
]


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _existing_columns(conn, table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table_name)}


def _comment_if_exists(conn, table: str, column: str, comment: str) -> None:
    if conn.dialect.name != "postgresql":
        return
    if not _has_table(conn, table) or column not in _existing_columns(conn, table):
        return
    escaped = comment.replace("'", "''")
    op.execute(f'COMMENT ON COLUMN "{table}"."{column}" IS \'{escaped}\'')


def upgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "notebook_items"):
        existing = _existing_columns(conn, "notebook_items")
        missing = [(n, l) for n, l, _ in _NEW_COLUMNS if n not in existing]
        if missing:
            with op.batch_alter_table("notebook_items") as batch_op:
                for name, length in missing:
                    batch_op.add_column(sa.Column(name, sa.String(length=length), nullable=True))
        for name, _, comment in _NEW_COLUMNS:
            _comment_if_exists(conn, "notebook_items", name, comment)
        _comment_if_exists(
            conn, "notebook_items", "profile_name",
            "Chỉ áp dụng cho type=personal_info và type=document: 'Tên hồ sơ' "
            "- đặt 1 lần lúc tạo, dùng làm tên thư mục con trên Google Drive "
            "để chứa file đính kèm của mục này. Không cho đổi sau khi tạo "
            "(tránh lệch tên thư mục đã tạo trên Drive).",
        )

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
    conn = op.get_bind()
    if _has_table(conn, "notebook_items"):
        existing = _existing_columns(conn, "notebook_items")
        drop = [n for n, _, _ in _NEW_COLUMNS if n in existing]
        if drop:
            with op.batch_alter_table("notebook_items") as batch_op:
                for name in drop:
                    batch_op.drop_column(name)
    # Deliberately NOT removing the seeded type rows - existing items may
    # reference them (FK). Same rationale as c8f1d5a3b7e2.
