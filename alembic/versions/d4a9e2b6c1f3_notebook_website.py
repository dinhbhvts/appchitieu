"""notebook_items.website + notebook_types: seed Trang web

Revision ID: d4a9e2b6c1f3
Revises: c8f1d5a3b7e2
Create Date: 2026-09-27 10:00:00.000000

- New nullable column notebook_items.website ("Trang web" URL), used by the
  new "website" (Trang web) type as its main field and by the existing
  "account" (Tài khoản) type for the login page of the system.
- Seeds the new built-in type ("website", "Trang web", "🔗"): title,
  website, info (Mô tả), tags, note.

Written defensively (existence checks), same pattern as c8f1d5a3b7e2.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd4a9e2b6c1f3'
down_revision: str | None = 'c8f1d5a3b7e2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_NOTEBOOK_TYPES = [
    ("website", "Trang web", "🔗"),
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

    if _has_table(conn, "notebook_items") and \
            "website" not in _existing_columns(conn, "notebook_items"):
        with op.batch_alter_table("notebook_items") as batch_op:
            batch_op.add_column(sa.Column("website", sa.String(length=500), nullable=True))
    _comment_if_exists(
        conn, "notebook_items", "website",
        "Trang web (URL) - dùng cho type=website và type=account. Frontend "
        "cho bấm mở link hoặc copy.",
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
    if _has_table(conn, "notebook_items") and \
            "website" in _existing_columns(conn, "notebook_items"):
        with op.batch_alter_table("notebook_items") as batch_op:
            batch_op.drop_column("website")
    # Deliberately NOT removing the seeded "website" type row - existing
    # items may reference it (FK). Same rationale as c8f1d5a3b7e2.
