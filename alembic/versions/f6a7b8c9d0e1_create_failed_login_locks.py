"""create failed_login_locks table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-13 08:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "failed_login_locks",
        sa.Column("identity_key", sa.String(length=128), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("locked_until_ms", sa.BigInteger(), nullable=True),
        sa.Column("first_failure_ms", sa.BigInteger(), nullable=False),
        sa.Column("last_failure_ms", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("identity_key", name="pk_failed_login_locks"),
    )
    op.create_index(
        "ix_failed_login_locks_locked_until_ms",
        "failed_login_locks",
        ["locked_until_ms"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_failed_login_locks_locked_until_ms", table_name="failed_login_locks")
    op.drop_table("failed_login_locks")
