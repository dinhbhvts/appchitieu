"""personal_info + task notebook types, attachments, dividends, soft-delete,
multi-year indexes

Revision ID: f3a1c9e7d8b2
Revises: e9bf8b627c97
Create Date: 2026-07-26 15:00:00.000000

Written defensively (existence checks before every add/create), same as
e9bf8b627c97 - see that migration's docstring for why. Two lessons carried
forward from debugging that migration on real production Postgres:

1. COMMENT ON COLUMN is DDL and Postgres rejects bind parameters ($1) inside
   DDL - comment text is escaped and inlined as a literal, never passed via
   .bindparams()/execute with params.
2. Table partitioning was considered for this migration (per a request to
   "review partition/index strategy for multi-year data") and deliberately
   NOT used - see the note in app/models/transaction.py. At 2 users' worth of
   data, even 30+ years of history stays in the tens of thousands of rows;
   partitioning would add real operational complexity for no measurable
   benefit at this scale. Composite indexes are added instead, matching the
   app's actual query patterns.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a1c9e7d8b2'
down_revision: str | None = 'e9bf8b627c97'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (key, name, icon) - must match the new entries in app/core/seed.py
# DEFAULT_NOTEBOOK_TYPES. Inserted only if that key doesn't already exist
# (existing installs already have the original 8 types from e9bf8b627c97).
_NEW_NOTEBOOK_TYPES = [
    ("personal_info", "Thông tin cá nhân", "🪪"),
    ("task", "Nhắc việc", "✅"),
]


def _existing_columns(conn, table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table_name)}


def _existing_indexes(conn, table_name: str) -> set[str]:
    return {i["name"] for i in sa.inspect(conn).get_indexes(table_name)}


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _comment_if_exists(conn, table: str, column: str, comment: str) -> None:
    """Set a column comment - Postgres only; silent no-op on SQLite (no
    COMMENT ON COLUMN there) or if the table/column isn't there yet.

    Inlined as an escaped literal, NOT a bind parameter - Postgres does not
    allow bind params ($1) inside DDL statements like COMMENT ON COLUMN.
    """
    if conn.dialect.name != "postgresql":
        return
    if not _has_table(conn, table) or column not in _existing_columns(conn, table):
        return
    escaped = comment.replace("'", "''")
    op.execute(f'COMMENT ON COLUMN "{table}"."{column}" IS \'{escaped}\'')


def _add_soft_delete_columns(conn, table: str) -> None:
    """Add is_deleted/deleted_at to `table` if not already present.

    Skips cleanly if the table itself doesn't exist yet on this database -
    some tables (e.g. stock_holdings, stock_month_summaries) predate this
    project's migration chain and only ever got created via
    Base.metadata.create_all on startup, never through Alembic (see the
    drift note in e9bf8b627c97). A brand-new database built purely from
    `alembic upgrade head` (no create_all) legitimately won't have them yet
    at this point - main.py's create_all will make them on first boot, same
    as it always has, and this migration doesn't need to be the one to do it.
    """
    if not _has_table(conn, table):
        return
    cols = _existing_columns(conn, table)
    with op.batch_alter_table(table) as batch_op:
        if "is_deleted" not in cols:
            batch_op.add_column(sa.Column(
                "is_deleted", sa.Boolean(), nullable=False,
                server_default=sa.false(),
            ))
        if "deleted_at" not in cols:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
    _comment_if_exists(
        conn, table, "is_deleted",
        "Xóa mềm: True = người dùng đã xóa từ UI. Hàng vẫn còn trong DB, chỉ "
        "bị ẩn khỏi mọi danh sách và tổng hợp.",
    )


def upgrade() -> None:
    conn = op.get_bind()

    # --- soft delete: transactions, asset_snapshots, notebook_items,
    # stock_cashflows, stock_trades, stock_holdings ---
    for table in (
        "transactions", "asset_snapshots", "notebook_items",
        "stock_cashflows", "stock_trades", "stock_holdings",
    ):
        _add_soft_delete_columns(conn, table)

    # --- notebook_items: personal_info fields ---
    ni_cols = _existing_columns(conn, "notebook_items")
    with op.batch_alter_table("notebook_items") as batch_op:
        if "full_name" not in ni_cols:
            batch_op.add_column(sa.Column("full_name", sa.String(length=150), nullable=True))
        if "id_number" not in ni_cols:
            batch_op.add_column(sa.Column("id_number", sa.String(length=50), nullable=True))
        if "id_issued_date" not in ni_cols:
            batch_op.add_column(sa.Column("id_issued_date", sa.Date(), nullable=True))
        if "id_issued_place" not in ni_cols:
            batch_op.add_column(sa.Column("id_issued_place", sa.String(length=150), nullable=True))
        if "birth_cert_no" not in ni_cols:
            batch_op.add_column(sa.Column("birth_cert_no", sa.String(length=50), nullable=True))
        if "health_insurance_no" not in ni_cols:
            batch_op.add_column(sa.Column("health_insurance_no", sa.String(length=50), nullable=True))
        if "hometown" not in ni_cols:
            batch_op.add_column(sa.Column("hometown", sa.String(length=150), nullable=True))

    # --- transactions: index on category_id (was an unindexed FK) + composite
    # (user_id, date) for "this person, this date range" report queries ---
    tx_idx = _existing_indexes(conn, "transactions")
    if "ix_transactions_category_id" not in tx_idx:
        op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    if "ix_transactions_user_date" not in tx_idx:
        op.create_index("ix_transactions_user_date", "transactions", ["user_id", "date"])

    # --- asset_snapshots: composite (year, month) - the real access pattern ---
    as_idx = _existing_indexes(conn, "asset_snapshots")
    if "ix_asset_snapshots_year_month" not in as_idx:
        op.create_index("ix_asset_snapshots_year_month", "asset_snapshots", ["year", "month"])

    # --- stock_trades: composite (symbol, date) - matches _positions()'s
    # group-by-symbol-then-walk-by-date access pattern ---
    st_idx = _existing_indexes(conn, "stock_trades")
    if "ix_stock_trades_symbol_date" not in st_idx:
        op.create_index("ix_stock_trades_symbol_date", "stock_trades", ["symbol", "date"])

    # --- stock_dividends: new table (Cổ tức) ---
    if not _has_table(conn, "stock_dividends"):
        op.create_table(
            "stock_dividends",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column(
                "amount", sa.Numeric(18, 0), nullable=False,
                comment="Tiền cổ tức thực nhận (đã trừ thuế nếu có) - VNĐ.",
            ),
            sa.Column("fee", sa.Numeric(18, 0), nullable=False, server_default="0"),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("note", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_stock_dividends_date", "stock_dividends", ["date"])
        op.create_index("ix_stock_dividends_symbol", "stock_dividends", ["symbol"])

    # --- notebook_attachments: new table (Hồ sơ đính kèm) ---
    if not _has_table(conn, "notebook_attachments"):
        op.create_table(
            "notebook_attachments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("notebook_item_id", sa.Integer(), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("mime_type", sa.String(length=100), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column(
                "drive_file_id", sa.String(length=120), nullable=False,
                comment="ID file trên Google Drive của chủ app - nội dung "
                        "file KHÔNG lưu trong database này, chỉ lưu tham chiếu.",
            ),
            sa.Column("drive_link", sa.String(length=500), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("uploaded_by", sa.Integer(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["notebook_item_id"], ["notebook_items.id"]),
            sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_notebook_attachments_notebook_item_id",
            "notebook_attachments", ["notebook_item_id"],
        )

    # --- seed the 2 new notebook types, only if missing (existing installs
    # already have the original 8 from e9bf8b627c97) ---
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

    # --- column comments (Postgres only, metadata-only) ---
    _comment_if_exists(conn, "notebook_items", "full_name",
        "Họ tên đầy đủ (khai sinh/CCCD) - khác với `title` (Tên thường gọi).")
    _comment_if_exists(conn, "notebook_items", "id_number", "Số CCCD.")
    _comment_if_exists(conn, "notebook_items", "id_issued_date", "Ngày cấp CCCD.")
    _comment_if_exists(conn, "notebook_items", "id_issued_place", "Nơi cấp CCCD.")
    _comment_if_exists(conn, "notebook_items", "birth_cert_no", "Số giấy khai sinh.")
    _comment_if_exists(conn, "notebook_items", "health_insurance_no", "Số thẻ BHYT.")
    _comment_if_exists(conn, "notebook_items", "hometown",
        "Quê quán - khác với `address` (dùng làm Địa chỉ thường trú ở type "
        "này).")


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "notebook_attachments"):
        op.drop_table("notebook_attachments")
    if _has_table(conn, "stock_dividends"):
        op.drop_table("stock_dividends")

    st_idx = _existing_indexes(conn, "stock_trades")
    if "ix_stock_trades_symbol_date" in st_idx:
        op.drop_index("ix_stock_trades_symbol_date", table_name="stock_trades")

    as_idx = _existing_indexes(conn, "asset_snapshots")
    if "ix_asset_snapshots_year_month" in as_idx:
        op.drop_index("ix_asset_snapshots_year_month", table_name="asset_snapshots")

    tx_idx = _existing_indexes(conn, "transactions")
    if "ix_transactions_user_date" in tx_idx:
        op.drop_index("ix_transactions_user_date", table_name="transactions")
    if "ix_transactions_category_id" in tx_idx:
        op.drop_index("ix_transactions_category_id", table_name="transactions")

    ni_cols = _existing_columns(conn, "notebook_items")
    with op.batch_alter_table("notebook_items") as batch_op:
        for col in (
            "hometown", "health_insurance_no", "birth_cert_no",
            "id_issued_place", "id_issued_date", "id_number", "full_name",
        ):
            if col in ni_cols:
                batch_op.drop_column(col)

    for table in (
        "stock_holdings", "stock_trades", "stock_cashflows",
        "notebook_items", "asset_snapshots", "transactions",
    ):
        if not _has_table(conn, table):
            continue
        cols = _existing_columns(conn, table)
        with op.batch_alter_table(table) as batch_op:
            if "deleted_at" in cols:
                batch_op.drop_column("deleted_at")
            if "is_deleted" in cols:
                batch_op.drop_column("is_deleted")

    # Deliberately NOT removing the personal_info/task notebook_types rows on
    # downgrade - if the user has already created real notebook items with
    # those types, deleting the type row would break the FK. Downgrading past
    # this migration while such data exists isn't supported; this mirrors how
    # e9bf8b627c97 handles its own seeded rows.
