"""Durable failed-login lock rows.

One row per opaque login identity. The identity is an HMAC, not an email,
password, bearer token, session token, or owner cookie. ``locked_until_ms``
is the end of a lock that starts when the failure count reaches the
threshold. It is not the end of a window that started on the first failure.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class FailedLoginLockModel(Base):
    """Failure count and optional lock deadline for one opaque login identity."""

    __tablename__ = "failed_login_locks"
    __table_args__ = (
        Index("ix_failed_login_locks_locked_until_ms", "locked_until_ms"),
        Index("ix_failed_login_locks_last_failure_ms", "last_failure_ms"),
    )

    identity_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False)
    locked_until_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    first_failure_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_failure_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
