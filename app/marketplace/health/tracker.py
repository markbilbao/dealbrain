"""Connector health tracking helpers."""

from __future__ import annotations

from datetime import datetime

from app.domain.entities.marketplace_data import (
    ConnectorError,
    ConnectorHealth,
    ConnectorHealthStatus,
    ConnectorRateLimit,
)


def derive_health_status(
    *,
    enabled: bool,
    configured: bool,
    consecutive_failures: int,
    rate_limited: bool,
    last_successful_sync: datetime | None,
) -> ConnectorHealthStatus:
    if not enabled:
        return ConnectorHealthStatus.DISABLED
    if not configured:
        return ConnectorHealthStatus.UNCONFIGURED
    if consecutive_failures >= 3:
        return ConnectorHealthStatus.UNAVAILABLE
    if rate_limited or consecutive_failures > 0:
        return ConnectorHealthStatus.DEGRADED
    if last_successful_sync is None:
        return ConnectorHealthStatus.UNCONFIGURED
    return ConnectorHealthStatus.HEALTHY


def build_health(
    *,
    connector_id: str,
    enabled: bool,
    configured: bool,
    consecutive_failures: int = 0,
    rate_limit: ConnectorRateLimit | None = None,
    last_attempted_sync: datetime | None = None,
    last_successful_sync: datetime | None = None,
    records_processed: int = 0,
    records_failed: int = 0,
    latency_ms: float | None = None,
    recent_errors: tuple[ConnectorError, ...] = (),
    checkpoint: str | None = None,
    message: str = "",
) -> ConnectorHealth:
    status = derive_health_status(
        enabled=enabled,
        configured=configured,
        consecutive_failures=consecutive_failures,
        rate_limited=bool(rate_limit and rate_limit.limited),
        last_successful_sync=last_successful_sync,
    )
    return ConnectorHealth(
        connector_id=connector_id,
        status=status,
        last_attempted_sync=last_attempted_sync,
        last_successful_sync=last_successful_sync,
        records_processed=records_processed,
        records_failed=records_failed,
        latency_ms=latency_ms,
        rate_limit=rate_limit,
        recent_errors=recent_errors,
        checkpoint=checkpoint,
        consecutive_failures=consecutive_failures,
        message=message,
    )
