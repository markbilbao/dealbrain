"""Shared rate-limit counter rows (Sprint 40.3).

One row per scope and opaque identity. Staging and production share this table
across application workers through the existing PostgreSQL database.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class RateLimitCounterModel(Base):
    """Fixed-window counter. Expired rows are deleted, not archived."""

    __tablename__ = "rate_limit_counters"
    __table_args__ = (Index("ix_rate_limit_counters_expires_at_ms", "expires_at_ms"),)

    scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    identity_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    window_started_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
