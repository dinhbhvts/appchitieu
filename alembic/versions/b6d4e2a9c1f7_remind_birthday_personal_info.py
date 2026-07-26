"""remind_birthday flag for personal_info notebook items

Revision ID: b6d4e2a9c1f7
Revises: f3a1c9e7d8b2
Create Date: 2026-07-28 10:00:00.000000

Adds NotebookItem.remind_birthday (default True) - lets the user untick the
"Nhắc sinh nhật" checkbox on a type=personal_info row so its Ngày sinh does
NOT also show up in the Dashboard's upcoming-reminders list, for people who
already keep a separate type=birthday row for the same person.

Written defensively (existence checks), same pattern as e9bf8b627c97 and
f3a1c9e7d8b2 - see those migrations' docstrings for why (notably: this repo's
database can have drift from Base.metadata.create_all() running before any
migration touches a given table, so every ADD COLUMN is guarded).
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b6d4e2a9c1f7'
down_revision: str | None = 'f3a1c9e7d8b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(conn, table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table_name)}


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "notebook_items"):
        return
    cols = _existing_columns(conn, "notebook_items")
    if "remind_birthday" in cols:
        return
    with op.batch_alter_table("notebook_items") as batch_op:
        batch_op.add_column(sa.Column(
            "remind_birthday", sa.Boolean(), nullable=False,
            server_default=sa.true(),
        ))
    if conn.dialect.name == "postgresql":
        comment = (
            "Chỉ áp dụng cho type=personal_info: True = Ngày sinh của mục "
            "này cũng hiện trong danh sách nhắc nhở ở Tổng quan, giống "
            "type=birthday. Mặc định True - bỏ tích nếu đã có bản ghi "
            "'Sinh nhật' riêng cho người này để tránh nhắc trùng."
        ).replace("'", "''")
        op.execute(
            f'COMMENT ON COLUMN "notebook_items"."remind_birthday" IS \'{comment}\''
        )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "notebook_items"):
        return
    cols = _existing_columns(conn, "notebook_items")
    if "remind_birthday" not in cols:
        return
    with op.batch_alter_table("notebook_items") as batch_op:
        batch_op.drop_column("remind_birthday")
