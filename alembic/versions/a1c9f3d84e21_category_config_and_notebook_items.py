"""category config (icon, is_active, audit) + notebook_items table

Revision ID: a1c9f3d84e21
Revises: 0c2552388afd
Create Date: 2026-07-25 09:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c9f3d84e21'
down_revision: str | None = '0c2552388afd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- categories: let the user manage them (rename/hide, never delete) ---
    op.add_column('categories', sa.Column('icon', sa.String(length=8), nullable=True))
    op.add_column(
        'categories',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'categories',
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.add_column(
        'categories',
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.add_column('categories', sa.Column('updated_by', sa.Integer(), nullable=True))
    # batch mode: SQLite (used in dev) cannot ALTER in a constraint directly -
    # it needs the copy-and-move strategy batch mode provides. On Postgres
    # (production) this still emits a normal ALTER TABLE ADD CONSTRAINT.
    with op.batch_alter_table('categories') as batch_op:
        batch_op.create_foreign_key(
            'fk_categories_updated_by_users', 'users', ['updated_by'], ['id']
        )

    # --- notebook_items: the "Sổ tay gia đình" (family notebook) ---
    op.create_table(
        'notebook_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('relation', sa.String(length=80), nullable=True),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('date1', sa.Date(), nullable=True),
        sa.Column('date1_is_lunar', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('date2', sa.Date(), nullable=True),
        sa.Column('recurrence_days', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=18, scale=0), nullable=True),
        sa.Column('tags', sa.String(length=255), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notebook_items_type'), 'notebook_items', ['type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notebook_items_type'), table_name='notebook_items')
    op.drop_table('notebook_items')

    with op.batch_alter_table('categories') as batch_op:
        batch_op.drop_constraint('fk_categories_updated_by_users', type_='foreignkey')
    op.drop_column('categories', 'updated_by')
    op.drop_column('categories', 'updated_at')
    op.drop_column('categories', 'created_at')
    op.drop_column('categories', 'is_active')
    op.drop_column('categories', 'icon')
