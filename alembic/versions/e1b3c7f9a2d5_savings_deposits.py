"""savings_deposits table (Gửi tiết kiệm)

Revision ID: e1b3c7f9a2d5
Revises: d7e4a1c9f6b3
Create Date: 2026-07-29 09:00:00.000000

New table for bank term deposits ("Gửi tiết kiệm"), entered by hand like
every other financial record in this app. Written defensively (existence
checks), same pattern as every migration since c013e455162f.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e1b3c7f9a2d5'
down_revision: str | None = 'd7e4a1c9f6b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "savings_deposits"):
        op.create_table(
            "savings_deposits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("content", sa.String(length=255), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("amount", sa.Numeric(18, 0), nullable=False),
            sa.Column("term_value", sa.Integer(), nullable=False),
            sa.Column(
                "term_unit",
                sa.Enum("day", "month", name="savingstermunit"),
                nullable=False, server_default="month",
            ),
            sa.Column("maturity_date", sa.Date(), nullable=False),
            sa.Column("interest_rate", sa.Numeric(6, 3), nullable=False),
            sa.Column(
                "expected_interest", sa.Numeric(18, 0), nullable=False,
                server_default="0",
            ),
            sa.Column("bank", sa.String(length=150), nullable=True),
            sa.Column(
                "status",
                sa.Enum("active", "settled", name="savingsstatus"),
                nullable=False, server_default="active",
            ),
            sa.Column("actual_interest", sa.Numeric(18, 0), nullable=True),
            sa.Column("settled_date", sa.Date(), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column(
                "updated_at", sa.DateTime(),
                server_default=sa.func.now(), onupdate=sa.func.now(),
            ),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column(
                "is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(),
            ),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_savings_deposits_start_date", "savings_deposits", ["start_date"],
        )
        op.create_index(
            "ix_savings_deposits_maturity_date", "savings_deposits", ["maturity_date"],
        )
        op.create_index(
            "ix_savings_deposits_user_id", "savings_deposits", ["user_id"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "savings_deposits"):
        op.drop_table("savings_deposits")
        if conn.dialect.name == "postgresql":
            op.execute("DROP TYPE IF EXISTS savingstermunit")
            op.execute("DROP TYPE IF EXISTS savingsstatus")
