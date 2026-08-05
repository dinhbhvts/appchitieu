"""notebook_items.is_completed (Nhắc việc - đánh dấu đã xong)

Revision ID: b7c3e9f1a5d2
Revises: a4f2c8d1e6b9
Create Date: 2026-08-06 09:00:00.000000

Adds notebook_items.is_completed: only meaningful for type=task - once True,
the item is skipped by get_upcoming()/get_calendar_events() (so it stops
showing on the Dashboard and stops generating push reminders), while staying
visible in the "Tiện ích" list as a history of finished tasks. Written
defensively (existence checks), same pattern as every migration since
c013e455162f.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c3e9f1a5d2'
down_revision: str | None = 'a4f2c8d1e6b9'
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
        if "is_completed" not in cols:
            with op.batch_alter_table("notebook_items") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "is_completed", sa.Boolean(), nullable=False,
                        server_default=sa.false(),
                    )
                )
            _comment_if_exists(
                conn, "notebook_items", "is_completed",
                "Chỉ áp dụng cho type=task: True = việc đã xong, ẩn khỏi "
                "Dashboard/lịch/thông báo nhắc.",
            )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "notebook_items"):
        cols = _existing_columns(conn, "notebook_items")
        if "is_completed" in cols:
            with op.batch_alter_table("notebook_items") as batch_op:
                batch_op.drop_column("is_completed")
