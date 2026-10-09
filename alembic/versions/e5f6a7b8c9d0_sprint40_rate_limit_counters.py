"""create rate_limit_counters table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-09 03:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_counters",
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("identity_key", sa.String(length=128), nullable=False),
        sa.Column("window_started_ms", sa.BigInteger(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("expires_at_ms", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("scope", "identity_key", name="pk_rate_limit_counters"),
    )
    op.create_index(
        "ix_rate_limit_counters_expires_at_ms",
        "rate_limit_counters",
        ["expires_at_ms"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_counters_expires_at_ms", table_name="rate_limit_counters")
    op.drop_table("rate_limit_counters")
