"""notebook_items.drive_folder_id

Revision ID: d7e4a1c9f6b3
Revises: c2a5f8e3b1d4
Create Date: 2026-07-27 10:00:00.000000

Adds notebook_items.drive_folder_id: the Google Drive folder id of a
personal_info row's own attachment subfolder (named after profile_name,
added in c2a5f8e3b1d4), created automatically the first time that row is
saved - see app/services/notebook_item_service.py.

Written defensively (existence checks), same pattern as every migration
since c013e455162f - see those migrations' docstrings for why.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd7e4a1c9f6b3'
down_revision: str | None = 'c2a5f8e3b1d4'
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

    if _has_table(conn, "notebook_items"):
        cols = _existing_columns(conn, "notebook_items")
        if "drive_folder_id" not in cols:
            with op.batch_alter_table("notebook_items") as batch_op:
                batch_op.add_column(sa.Column("drive_folder_id", sa.String(length=120), nullable=True))
            _comment_if_exists(
                conn, "notebook_items", "drive_folder_id",
                "ID thư mục con trên Google Drive của mục personal_info này "
                "(đặt tên theo profile_name), tự tạo khi lưu lần đầu.",
            )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "notebook_items"):
        cols = _existing_columns(conn, "notebook_items")
        if "drive_folder_id" in cols:
            with op.batch_alter_table("notebook_items") as batch_op:
                batch_op.drop_column("drive_folder_id")
