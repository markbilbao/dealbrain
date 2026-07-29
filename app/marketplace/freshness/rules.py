"""Data freshness evaluation for marketplace observations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.marketplace_data import (
    DataFreshness,
    FreshnessStatus,
    SourceMode,
)


def evaluate_freshness(
    *,
    source_mode: SourceMode,
    observed_at: datetime | None,
    source_timestamp: datetime | None,
    ingested_at: datetime | None,
    now: datetime | None = None,
    connector_healthy: bool | None = None,
    thresholds: tuple[float, float, float] = (6.0, 24.0, 72.0),
    simulated: bool = False,
) -> DataFreshness:
    """Classify freshness. Fixture data is never presented as current live pricing."""
    clock = now or datetime.now(UTC)
    fresh_h, aging_h, stale_h = thresholds

    reference = observed_at or source_timestamp or ingested_at
    age_hours: float | None = None
    if reference is not None:
        ref = reference if reference.tzinfo else reference.replace(tzinfo=UTC)
        age_hours = max(0.0, (clock - ref).total_seconds() / 3600.0)

    warning: str | None = None
    is_current_live = False

    if source_mode == SourceMode.FIXTURE:
        status = FreshnessStatus.UNKNOWN
        warning = "Fixture/demo data — not current live marketplace pricing"
    elif source_mode == SourceMode.IMPORTED:
        if age_hours is None:
            status = FreshnessStatus.UNKNOWN
            warning = "Imported data with unknown observation time — not live"
        elif age_hours <= aging_h:
            status = FreshnessStatus.AGING
            warning = "Imported data — not live marketplace pricing"
        else:
            status = FreshnessStatus.STALE
            warning = "Imported data may be outdated — not live marketplace pricing"
    else:  # LIVE
        if simulated:
            warning = "SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION"
        if connector_healthy is False:
            status = (
                FreshnessStatus.STALE
                if age_hours and age_hours > fresh_h
                else FreshnessStatus.AGING
            )
            warning = (
                warning + "; " if warning else ""
            ) + "Connector unhealthy — treat prices cautiously"
        elif age_hours is None:
            status = FreshnessStatus.UNKNOWN
            warning = (warning + "; " if warning else "") + "Live observation timestamp missing"
        elif age_hours <= fresh_h:
            status = FreshnessStatus.FRESH
            is_current_live = not simulated and connector_healthy is not False
        elif age_hours <= aging_h:
            status = FreshnessStatus.AGING
            warning = (warning + "; " if warning else "") + "Price/inventory data is aging"
        elif age_hours <= stale_h:
            status = FreshnessStatus.STALE
            warning = (warning + "; " if warning else "") + "Price/inventory data is stale"
        else:
            status = FreshnessStatus.STALE
            warning = (warning + "; " if warning else "") + "Price/inventory data is stale"

    return DataFreshness(
        status=status,
        source_mode=source_mode,
        last_successful_observation=observed_at,
        source_timestamp=source_timestamp,
        ingestion_timestamp=ingested_at,
        age_hours=age_hours,
        connector_healthy=connector_healthy,
        warning=warning,
        is_current_live_price=is_current_live,
    )
