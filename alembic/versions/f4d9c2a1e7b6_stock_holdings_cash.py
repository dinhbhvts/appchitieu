"""stock_holdings.is_cash + cash_base_value (dòng Tiền mặt tự động)

Revision ID: f4d9c2a1e7b6
Revises: b7c3e9f1a5d2
Create Date: 2026-08-08 10:00:00.000000

Adds stock_holdings.is_cash and stock_holdings.cash_base_value: the app now
auto-maintains one "Tiền mặt" holding row per person, whose value is computed
from cash_base_value (user-entered seed) plus every deposit/withdraw/buy/
sell/dividend recorded for that person (see stock_service._cash_delta /
_ensure_cash_holding). Written defensively (existence checks), same pattern
as every migration since c013e455162f.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f4d9c2a1e7b6'
down_revision: str | None = 'b7c3e9f1a5d2'
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

    if _has_table(conn, "stock_holdings"):
        cols = _existing_columns(conn, "stock_holdings")
        if "is_cash" not in cols:
            with op.batch_alter_table("stock_holdings") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "is_cash", sa.Boolean(), nullable=False,
                        server_default=sa.false(),
                    )
                )
            _comment_if_exists(
                conn, "stock_holdings", "is_cash",
                "True = dòng 'Tiền mặt' tự động do hệ thống tạo và tự tính "
                "giá trị, không phải khoản CK nhập tay bình thường.",
            )
        if "cash_base_value" not in cols:
            with op.batch_alter_table("stock_holdings") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "cash_base_value", sa.Numeric(18, 0), nullable=False,
                        server_default="0",
                    )
                )
            _comment_if_exists(
                conn, "stock_holdings", "cash_base_value",
                "Chỉ có ý nghĩa khi is_cash=True: giá trị khởi tạo người "
                "dùng tự nhập, value tự cộng thêm phát sinh từ nạp/rút/"
                "mua/bán/cổ tức.",
            )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, "stock_holdings"):
        cols = _existing_columns(conn, "stock_holdings")
        if "cash_base_value" in cols:
            with op.batch_alter_table("stock_holdings") as batch_op:
                batch_op.drop_column("cash_base_value")
        if "is_cash" in cols:
            with op.batch_alter_table("stock_holdings") as batch_op:
                batch_op.drop_column("is_cash")
