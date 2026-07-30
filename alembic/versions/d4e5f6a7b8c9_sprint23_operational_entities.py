"""create operational_entities table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-30 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_entities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("secondary_key", sa.String(length=512), nullable=True),
        sa.Column("owner_id", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False, server_default="0"),
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
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store", "entity_id", name="uq_operational_store_entity"),
        sa.UniqueConstraint("store", "secondary_key", name="uq_operational_store_secondary"),
    )
    op.create_index(
        "ix_operational_store_owner",
        "operational_entities",
        ["store", "owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_operational_store_seq",
        "operational_entities",
        ["store", "seq"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operational_store_seq", table_name="operational_entities")
    op.drop_index("ix_operational_store_owner", table_name="operational_entities")
    op.drop_table("operational_entities")
