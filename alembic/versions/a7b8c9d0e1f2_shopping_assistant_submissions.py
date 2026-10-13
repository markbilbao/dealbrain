"""create shopping_assistant_submissions table

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-13 11:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shopping_assistant_submissions",
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("updated_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("expires_at_ms", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint(
            "scope",
            "key_hash",
            name="pk_shopping_assistant_submissions",
        ),
    )
    op.create_index(
        "ix_shopping_assistant_submissions_state_expires",
        "shopping_assistant_submissions",
        ["state", "expires_at_ms"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shopping_assistant_submissions_state_expires",
        table_name="shopping_assistant_submissions",
    )
    op.drop_table("shopping_assistant_submissions")
