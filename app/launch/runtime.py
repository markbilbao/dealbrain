"""Process uptime and startup markers for health probes."""

from __future__ import annotations

from datetime import UTC, datetime

_STARTED_AT: datetime | None = None


def mark_startup(*, when: datetime | None = None) -> datetime:
    """Record application startup time (idempotent for the first call)."""
    global _STARTED_AT
    if _STARTED_AT is None:
        _STARTED_AT = when or datetime.now(UTC)
    return _STARTED_AT


def get_startup_instant() -> datetime | None:
    return _STARTED_AT


def uptime_seconds(*, now: datetime | None = None) -> float:
    started = _STARTED_AT
    if started is None:
        return 0.0
    current = now or datetime.now(UTC)
    return max(0.0, (current - started).total_seconds())
