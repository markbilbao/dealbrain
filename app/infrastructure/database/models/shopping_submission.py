"""Durable shopping-assistant submission ledger.

One row per opaque authority scope and SHA-256 idempotency key. The raw key,
owner cookie, bearer token, email, password, and client IP are not columns.
``response_body`` is the public JSON needed to replay a completed POST. It is
retained only until ``expires_at_ms``.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ShoppingAssistantSubmissionModel(Base):
    """Atomic claim row for one scoped shopping-assistant submission."""

    __tablename__ = "shopping_assistant_submissions"
    __table_args__ = (
        Index(
            "ix_shopping_assistant_submissions_state_expires",
            "state",
            "expires_at_ms",
        ),
    )

    scope: Mapped[str] = mapped_column(String(128), primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
