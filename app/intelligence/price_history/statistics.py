"""Deterministic price statistics and trend classification.

Formulas (documented for Sprint 7 Price History Foundation)
===========================================================

All calculations use **only stored** :class:`PriceSnapshot` observations.
Currencies are never converted. Mixed currencies raise
:class:`PriceHistoryValidationError`.

Statistics (single currency)
----------------------------
Observations are sorted by ``(observed_at ASC, marketplace, listing_id, snapshot_id)``.

- ``current_total_cost`` = ``total_cost`` of the last observation
- ``lowest_recorded_total_cost`` = min ``total_cost``
- ``highest_recorded_total_cost`` = max ``total_cost``
- ``average_total_cost`` = arithmetic mean of ``total_cost`` (rounded to 2 dp)
- ``median_total_cost`` = median of ``total_cost`` (rounded to 2 dp)
- ``observation_count`` = number of snapshots
- ``first_observed`` / ``last_observed`` = earliest / latest ``observed_at``
- ``absolute_change`` = ``current_total_cost - first_total_cost`` (first by time)
- ``percentage_change`` = ``(absolute_change / first_total_cost) * 100``
  rounded to 2 dp (0.0 when first total cost is 0)

Trend classification
--------------------
Default threshold: ``DEFAULT_TREND_THRESHOLD_PERCENT = 2.0``
(configurable via ``trend_threshold_percent``).

1. If ``observation_count < 3`` → ``insufficient_data``
2. Split chronologically into earlier and recent halves:
   - ``mid = observation_count // 2``
   - earlier = first ``mid`` observations
   - recent = remaining observations
3. ``earlier_avg`` = mean total cost of earlier half
4. ``recent_avg`` = mean total cost of recent half
5. ``delta_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100``
   (0.0 when ``earlier_avg`` is 0)
6. ``rising`` if ``delta_pct > threshold``
7. ``falling`` if ``delta_pct < -threshold``
8. otherwise ``stable``

Wording: prefer “Lowest recorded price in the available DealBrain history.”
Never claim “lowest ever” or future price movement.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import (
    MarketplacePriceSummary,
    PriceSnapshot,
    PriceStatistics,
    PriceTrend,
)
from app.domain.exceptions import PriceHistoryValidationError

DEFAULT_TREND_THRESHOLD_PERCENT = 2.0
MIN_OBSERVATIONS_FOR_TREND = 3


def sort_snapshots(snapshots: Sequence[PriceSnapshot]) -> list[PriceSnapshot]:
    """Deterministic ordering for statistics and API responses."""
    return sorted(
        snapshots,
        key=lambda s: (
            s.observed_at,
            s.marketplace,
            s.listing_id,
            str(s.snapshot_id),
        ),
    )


def ensure_single_currency(snapshots: Sequence[PriceSnapshot]) -> str:
    """Return the sole currency or raise when currencies differ / are empty."""
    if not snapshots:
        raise PriceHistoryValidationError(
            "Cannot compute price statistics: no observations available."
        )
    currencies = {snapshot.currency.upper() for snapshot in snapshots}
    if len(currencies) > 1:
        joined = ", ".join(sorted(currencies))
        raise PriceHistoryValidationError(
            f"Cannot combine price snapshots with different currencies: {joined}. "
            "Currency conversion is not supported."
        )
    return next(iter(currencies))


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    mid = count // 2
    if count % 2 == 1:
        return round(ordered[mid], 2)
    return round((ordered[mid - 1] + ordered[mid]) / 2.0, 2)


def _mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 2)


def classify_trend(
    snapshots: Sequence[PriceSnapshot],
    *,
    threshold_percent: float = DEFAULT_TREND_THRESHOLD_PERCENT,
) -> PriceTrend:
    """Classify trend using only stored observations and the documented formula."""
    ordered = sort_snapshots(snapshots)
    if len(ordered) < MIN_OBSERVATIONS_FOR_TREND:
        return PriceTrend.INSUFFICIENT_DATA

    mid = len(ordered) // 2
    earlier = ordered[:mid]
    recent = ordered[mid:]
    earlier_avg = sum(s.total_cost for s in earlier) / len(earlier)
    recent_avg = sum(s.total_cost for s in recent) / len(recent)

    delta_pct = (
        0.0 if earlier_avg == 0 else ((recent_avg - earlier_avg) / earlier_avg) * 100.0
    )

    if delta_pct > threshold_percent:
        return PriceTrend.RISING
    if delta_pct < -threshold_percent:
        return PriceTrend.FALLING
    return PriceTrend.STABLE


def calculate_statistics(
    snapshots: Sequence[PriceSnapshot],
    *,
    threshold_percent: float = DEFAULT_TREND_THRESHOLD_PERCENT,
) -> PriceStatistics:
    """Compute price statistics from stored snapshots of a single currency."""
    currency = ensure_single_currency(snapshots)
    ordered = sort_snapshots(snapshots)
    totals = [snapshot.total_cost for snapshot in ordered]
    first = ordered[0]
    last = ordered[-1]
    absolute_change = round(last.total_cost - first.total_cost, 2)
    if first.total_cost == 0:
        percentage_change = 0.0
    else:
        percentage_change = round((absolute_change / first.total_cost) * 100.0, 2)

    return PriceStatistics(
        currency=currency,
        current_total_cost=round(last.total_cost, 2),
        lowest_recorded_total_cost=round(min(totals), 2),
        highest_recorded_total_cost=round(max(totals), 2),
        average_total_cost=_mean(totals),
        median_total_cost=_median(totals),
        observation_count=len(ordered),
        first_observed=first.observed_at,
        last_observed=last.observed_at,
        absolute_change=absolute_change,
        percentage_change=percentage_change,
        trend=classify_trend(ordered, threshold_percent=threshold_percent),
    )


def build_marketplace_summaries(
    snapshots: Sequence[PriceSnapshot],
) -> tuple[MarketplacePriceSummary, ...]:
    """Roll up per-marketplace stats from stored observations (single currency)."""
    ensure_single_currency(snapshots)
    ordered = sort_snapshots(snapshots)
    by_marketplace: dict[str, list[PriceSnapshot]] = {}
    for snapshot in ordered:
        by_marketplace.setdefault(snapshot.marketplace, []).append(snapshot)

    summaries: list[MarketplacePriceSummary] = []
    for marketplace in sorted(by_marketplace):
        group = by_marketplace[marketplace]
        totals = [s.total_cost for s in group]
        latest = group[-1]
        summaries.append(
            MarketplacePriceSummary(
                marketplace=marketplace,
                latest_total_cost=round(latest.total_cost, 2),
                lowest_recorded_total_cost=round(min(totals), 2),
                average_total_cost=_mean(totals),
                observation_count=len(group),
                latest_availability=latest.availability,
                last_observed=latest.observed_at,
            )
        )
    return tuple(summaries)


def filter_available(snapshots: Sequence[PriceSnapshot]) -> list[PriceSnapshot]:
    """Exclude out-of-stock observations when callers request available-only views."""
    return [
        snapshot
        for snapshot in snapshots
        if snapshot.availability != AvailabilityStatus.OUT_OF_STOCK
    ]
