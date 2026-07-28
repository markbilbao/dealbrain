"""create price_snapshots table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-28 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_snapshots",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_product_id", sa.String(length=64), nullable=False),
        sa.Column("marketplace", sa.String(length=64), nullable=False),
        sa.Column("listing_id", sa.String(length=128), nullable=False),
        sa.Column("seller_name", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("item_price", sa.Float(), nullable=False),
        sa.Column("shipping_cost", sa.Float(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.Column("availability", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint(
            "canonical_product_id",
            "marketplace",
            "listing_id",
            "observed_at",
            name="uq_price_snapshot_observation",
        ),
    )
    op.create_index(
        "ix_price_snapshots_canonical_product_id",
        "price_snapshots",
        ["canonical_product_id"],
        unique=False,
    )
    op.create_index(
        "ix_price_snapshots_listing_id",
        "price_snapshots",
        ["listing_id"],
        unique=False,
    )
    op.create_index(
        "ix_price_snapshots_observed_at",
        "price_snapshots",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_price_snapshots_product_observed",
        "price_snapshots",
        ["canonical_product_id", "observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_price_snapshots_product_observed", table_name="price_snapshots")
    op.drop_index("ix_price_snapshots_observed_at", table_name="price_snapshots")
    op.drop_index("ix_price_snapshots_listing_id", table_name="price_snapshots")
    op.drop_index(
        "ix_price_snapshots_canonical_product_id",
        table_name="price_snapshots",
    )
    op.drop_table("price_snapshots")
