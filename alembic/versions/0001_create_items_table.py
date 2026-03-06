"""create items table

Revision ID: 0001_create_items_table
Revises:
Create Date: 2026-03-06 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_items_table"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_items_tenant_id", "items", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_items_tenant_id", table_name="items")
    op.drop_table("items")
