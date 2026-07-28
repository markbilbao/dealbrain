"""create canonical product registry tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-28 10:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canonical_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_key", sa.String(length=512), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("family", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("storage", sa.String(length=64), nullable=True),
        sa.Column("color", sa.String(length=128), nullable=True),
        sa.Column("display_name", sa.String(length=512), nullable=False),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identity_key"),
    )
    op.create_index(
        op.f("ix_canonical_products_brand"),
        "canonical_products",
        ["brand"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canonical_products_family"),
        "canonical_products",
        ["family"],
        unique=False,
    )
    op.create_index(
        "ix_canonical_products_brand_family_model",
        "canonical_products",
        ["brand", "family", "model"],
        unique=False,
    )
    op.create_index(
        "ix_canonical_products_status",
        "canonical_products",
        ["status"],
        unique=False,
    )

    op.create_table(
        "canonical_product_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["canonical_products.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["canonical_products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "target_id",
            "relation_type",
            name="uq_canonical_product_relation_edge",
        ),
    )
    op.create_index(
        "ix_canonical_product_relations_source_type",
        "canonical_product_relations",
        ["source_id", "relation_type"],
        unique=False,
    )
    op.create_index(
        "ix_canonical_product_relations_target_type",
        "canonical_product_relations",
        ["target_id", "relation_type"],
        unique=False,
    )
    op.create_index(
        "ix_canonical_product_relations_type",
        "canonical_product_relations",
        ["relation_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_canonical_product_relations_type",
        table_name="canonical_product_relations",
    )
    op.drop_index(
        "ix_canonical_product_relations_target_type",
        table_name="canonical_product_relations",
    )
    op.drop_index(
        "ix_canonical_product_relations_source_type",
        table_name="canonical_product_relations",
    )
    op.drop_table("canonical_product_relations")

    op.drop_index("ix_canonical_products_status", table_name="canonical_products")
    op.drop_index(
        "ix_canonical_products_brand_family_model",
        table_name="canonical_products",
    )
    op.drop_index(op.f("ix_canonical_products_family"), table_name="canonical_products")
    op.drop_index(op.f("ix_canonical_products_brand"), table_name="canonical_products")
    op.drop_table("canonical_products")
