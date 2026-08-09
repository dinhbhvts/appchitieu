"""stock_holdings.cash_sync_*_id (mốc đối chiếu Tiền mặt tay)

Revision ID: a2e7c4f9b3d6
Revises: f4d9c2a1e7b6
Create Date: 2026-08-09 09:00:00.000000

Adds stock_holdings.cash_sync_cashflow_id / cash_sync_trade_id /
cash_sync_dividend_id: watermark ids marking the last time the user manually
reconciled cash_base_value on the auto "Tiền mặt" row. Without this, editing
cash_base_value to match a real observed balance got the ENTIRE history of
deposit/withdraw/buy/sell/dividend activity added back on top again (double
counting everything already reflected in the number the user just typed in)
- see stock_service._cash_delta / _ensure_cash_holding.

Uses auto-increment ids rather than a timestamp on purpose: SQLite's
CURRENT_TIMESTAMP (used for created_at on these tables) only has
SECOND precision, so two requests landing in the same second (e.g. editing
cash_base_value then immediately recording a new transaction) could compare
out of order with a timestamp-based watermark. ids are strictly monotonic
with no such ambiguity. Written defensively (existence checks), same
pattern as every migration since c013e455162f.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a2e7c4f9b3d6'
down_revision: str | None = 'f4d9c2a1e7b6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "cash_sync_cashflow_id",
    "cash_sync_trade_id",
    "cash_sync_dividend_id",
)


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

    if _has_table(conn, "stock_holdings"):
        cols = _existing_columns(conn, "stock_holdings")
        for col in _COLUMNS:
            if col not in cols:
                with op.batch_alter_table("stock_holdings") as batch_op:
                    batch_op.add_column(
                        sa.Column(col, sa.Integer(), nullable=False,
                                  server_default="0")
                    )
                _comment_if_exists(
                    conn, "stock_holdings", col,
                    "Mốc đối chiếu tay 'Tiền mặt' - chỉ cộng dồn các dòng có "
                    "id lớn hơn giá trị này (0 = tính từ đầu).",
                )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "stock_holdings"):
        cols = _existing_columns(conn, "stock_holdings")
        for col in _COLUMNS:
            if col in cols:
                with op.batch_alter_table("stock_holdings") as batch_op:
                    batch_op.drop_column(col)
