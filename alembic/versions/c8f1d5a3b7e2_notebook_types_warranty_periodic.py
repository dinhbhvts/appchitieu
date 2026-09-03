"""notebook_types: seed Bảo hành + Định kỳ

Revision ID: c8f1d5a3b7e2
Revises: a2e7c4f9b3d6
Create Date: 2026-09-04 10:00:00.000000

Pure data migration - NO new columns/tables. Both new "loại tiện ích" reuse
existing NotebookItem columns entirely:
  - warranty (Bảo hành):  title, date1 (Ngày mua), date2 (Hạn bảo hành),
                          amount (Số tiền), tags, note. Not a due-date
                          reminder type (see notebook_item_service.
                          _DUE_DATE_TYPES) - the "còn hạn/hết hạn" distinction
                          is shown as a color on the list (frontend-only,
                          computed from date2 vs today), not a Dashboard
                          reminder.
  - periodic (Định kỳ):   title, date1 (Ngày thực hiện), date2 (Ngày đến hạn
                          kế tiếp), tags, note - PLUS is_completed (tickbox
                          "đã thực hiện"). Included in _DUE_DATE_TYPES so it
                          shows up in the Dashboard's "sắp tới" reminders,
                          same one-off due-date handling as service/
                          maintenance/task.
Same migration also makes the EXISTING "maintenance" (Bảo trì) type
recognise is_completed the same way "task" always has (frontend field-map
change only - the column already exists since b7c3e9f1a5d2, this migration
doesn't touch it).

Written defensively (existence checks), same pattern as f3a1c9e7d8b2.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c8f1d5a3b7e2'
down_revision: str | None = 'a2e7c4f9b3d6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (key, name, icon) - must match the new entries in app/core/seed.py
# DEFAULT_NOTEBOOK_TYPES. Inserted only if that key doesn't already exist
# (existing installs already have the original 10 types from earlier
# migrations).
_NEW_NOTEBOOK_TYPES = [
    ("warranty", "Bảo hành", "🛡️"),
    ("periodic", "Định kỳ", "🔁"),
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

    # is_completed now also covers maintenance/periodic, not just task -
    # refresh the Postgres column comment set by b7c3e9f1a5d2 to match
    # (metadata-only, no-op on SQLite - see _comment_if_exists).
    _comment_if_exists(
        conn, "notebook_items", "is_completed",
        "Áp dụng cho type=task/maintenance/periodic: True = đã xong/đã "
        "thực hiện, ẩn khỏi Dashboard/thông báo nhắc.",
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Deliberately NOT removing the seeded rows on downgrade - if the user
    # already created real notebook items with these types, deleting the
    # type row would break the FK. Same rationale as f3a1c9e7d8b2.
    _ = conn
