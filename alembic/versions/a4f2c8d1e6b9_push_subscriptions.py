"""push_subscriptions table (Web Push - thông báo nhắc sự kiện)

Revision ID: a4f2c8d1e6b9
Revises: e1b3c7f9a2d5
Create Date: 2026-08-05 09:00:00.000000

New table storing each browser/device's Web Push subscription (endpoint +
encryption keys) after the user taps "Bật thông báo" - see
app/models/push_subscription.py. Written defensively (existence checks),
same pattern as every migration since c013e455162f.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a4f2c8d1e6b9'
down_revision: str | None = 'e1b3c7f9a2d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "push_subscriptions"):
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("endpoint", sa.Text(), nullable=False),
            sa.Column("p256dh", sa.String(length=255), nullable=False),
            sa.Column("auth", sa.String(length=255), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column(
                "updated_at", sa.DateTime(),
                server_default=sa.func.now(), onupdate=sa.func.now(),
            ),
        )
        # SQLite can't add a UNIQUE constraint on a Text column via a plain
        # unique index in some builds, but push endpoints are always short
        # URLs in practice - a regular unique index works fine on both
        # SQLite and PostgreSQL.
        op.create_index(
            "uq_push_subscriptions_endpoint", "push_subscriptions",
            ["endpoint"], unique=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "push_subscriptions"):
        op.drop_table("push_subscriptions")
