"""Base helpers for deterministic mock marketplace collectors."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.collection import (
    CollectedListing,
    CollectionFailure,
    CollectionResult,
    CollectionStatus,
    CollectionTarget,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.intelligence.collection.ids import make_marketplace_result_id
from app.intelligence.collection.scenarios import (
    SCENARIO_DUPLICATE,
    SCENARIO_EMPTY,
    SCENARIO_MALFORMED,
    SCENARIO_PARTIAL_FAILURE,
    SCENARIO_SUCCESS,
    SCENARIO_TOTAL_FAILURE,
    SCENARIO_UNAVAILABLE,
    filter_by_query,
    resolve_scenario,
)


class BaseMockCollector(MarketplaceCollector):
    """Shared canned-data collector with scenario support (no HTTP)."""

    def __init__(
        self,
        *,
        marketplace_name: str,
        fixtures: Sequence[Mapping[str, Any]],
        normalize: Callable[[Mapping[str, Any]], MarketplaceListing],
        clock: Callable[[], datetime] | None = None,
        run_id_factory: Callable[[CollectionTarget, datetime], str] | None = None,
    ) -> None:
        self._marketplace_name = marketplace_name
        self._fixtures = list(fixtures)
        self._normalize = normalize
        self._clock = clock or (lambda: datetime.now(UTC))
        self._run_id_factory = run_id_factory

    @property
    def marketplace_name(self) -> str:
        return self._marketplace_name

    def health_check(self) -> bool:
        return True

    def collect(self, target: CollectionTarget) -> CollectionResult:
        started_at = self._clock()
        scenario = resolve_scenario(target.scenario, target.query)
        run_id = (
            self._run_id_factory(target, started_at)
            if self._run_id_factory is not None
            else make_marketplace_result_id(
                run_id=f"local|{target.query}|{started_at.isoformat()}",
                marketplace=self._marketplace_name,
            )
        )

        if scenario == SCENARIO_TOTAL_FAILURE:
            completed_at = self._clock()
            failure = CollectionFailure(
                marketplace=self._marketplace_name,
                code="total_failure",
                message=f"{self._marketplace_name} mock collector forced total failure",
                retryable=False,
            )
            return CollectionResult(
                run_id=run_id,
                marketplace=self._marketplace_name,
                query=target.query,
                target_id=target.target_id,
                started_at=started_at,
                completed_at=completed_at,
                listing_count=0,
                successful_listing_count=0,
                failed_listing_count=1,
                listings=(),
                errors=(failure,),
                status=CollectionStatus.FAILED,
            )

        matched = filter_by_query(self._fixtures, target.query)
        listings: list[CollectedListing] = []
        errors: list[CollectionFailure] = []
        warnings: list[str] = []

        if scenario == SCENARIO_EMPTY:
            matched = []

        if scenario == SCENARIO_UNAVAILABLE:
            matched = [raw for raw in matched if self._is_unavailable_raw(raw)] or matched[:1]
            if matched:
                # Force a synthetic unavailable listing when fixtures lack one.
                listing = self._normalize(matched[0])
                listing = MarketplaceListing(
                    marketplace=listing.marketplace,
                    product_id=listing.product_id,
                    title=listing.title,
                    price=listing.price,
                    currency=listing.currency,
                    seller=listing.seller,
                    rating=listing.rating,
                    url=listing.url,
                    availability=AvailabilityStatus.OUT_OF_STOCK,
                )
                listings.append(
                    CollectedListing(
                        listing=listing,
                        source_marketplace=self._marketplace_name,
                        collected_at=started_at,
                    )
                )
                warnings.append("Listing marked unavailable by mock scenario")
            completed_at = self._clock()
            return self._build_result(
                run_id=run_id,
                target=target,
                started_at=started_at,
                completed_at=completed_at,
                listings=listings,
                errors=errors,
                warnings=warnings,
            )

        if scenario == SCENARIO_MALFORMED:
            errors.append(
                CollectionFailure(
                    marketplace=self._marketplace_name,
                    code="malformed_listing",
                    message="Mock source listing missing required product identity fields",
                    retryable=False,
                    listing_id="malformed-1",
                )
            )
            # Also attempt to include any valid matches so partial outcomes are testable.
            for raw in matched[:1]:
                listing = self._normalize(raw)
                listings.append(
                    CollectedListing(
                        listing=listing,
                        source_marketplace=self._marketplace_name,
                        collected_at=started_at,
                    )
                )
            completed_at = self._clock()
            return self._build_result(
                run_id=run_id,
                target=target,
                started_at=started_at,
                completed_at=completed_at,
                listings=listings,
                errors=errors,
                warnings=["Malformed source listing rejected from storage path"],
            )

        if scenario == SCENARIO_PARTIAL_FAILURE:
            if matched:
                listing = self._normalize(matched[0])
                listings.append(
                    CollectedListing(
                        listing=listing,
                        source_marketplace=self._marketplace_name,
                        collected_at=started_at,
                    )
                )
            errors.append(
                CollectionFailure(
                    marketplace=self._marketplace_name,
                    code="temporary_unavailable",
                    message="Mock partial failure for secondary listing batch",
                    retryable=True,
                    listing_id="partial-batch",
                )
            )
            completed_at = self._clock()
            return self._build_result(
                run_id=run_id,
                target=target,
                started_at=started_at,
                completed_at=completed_at,
                listings=listings,
                errors=errors,
                warnings=["Partial marketplace failure isolated"],
            )

        if scenario == SCENARIO_DUPLICATE:
            if matched:
                listing = self._normalize(matched[0])
                first = CollectedListing(
                    listing=listing,
                    source_marketplace=self._marketplace_name,
                    collected_at=started_at,
                    is_duplicate=False,
                )
                second = CollectedListing(
                    listing=listing,
                    source_marketplace=self._marketplace_name,
                    collected_at=started_at,
                    is_duplicate=True,
                )
                listings.extend([first, second])
                warnings.append("Duplicate listing emitted by mock scenario")
            completed_at = self._clock()
            return self._build_result(
                run_id=run_id,
                target=target,
                started_at=started_at,
                completed_at=completed_at,
                listings=listings,
                errors=errors,
                warnings=warnings,
            )

        # Default / success
        _ = scenario == SCENARIO_SUCCESS
        for raw in matched:
            listing = self._normalize(raw)
            listings.append(
                CollectedListing(
                    listing=listing,
                    source_marketplace=self._marketplace_name,
                    collected_at=started_at,
                )
            )

        completed_at = self._clock()
        return self._build_result(
            run_id=run_id,
            target=target,
            started_at=started_at,
            completed_at=completed_at,
            listings=listings,
            errors=errors,
            warnings=warnings,
        )

    def _is_unavailable_raw(self, raw: Mapping[str, Any]) -> bool:
        stock = raw.get("stock")
        if stock is not None:
            try:
                return int(stock) <= 0
            except (TypeError, ValueError):
                return False
        availability = str(raw.get("availability", "")).lower()
        return "out" in availability

    def _build_result(
        self,
        *,
        run_id: str,
        target: CollectionTarget,
        started_at: datetime,
        completed_at: datetime,
        listings: list[CollectedListing],
        errors: list[CollectionFailure],
        warnings: list[str],
    ) -> CollectionResult:
        successful = len(listings)
        failed = len(errors)
        if failed and successful:
            status = CollectionStatus.PARTIALLY_COMPLETED
        elif failed and not successful:
            status = CollectionStatus.FAILED
        else:
            status = CollectionStatus.COMPLETED
        return CollectionResult(
            run_id=run_id,
            marketplace=self._marketplace_name,
            query=target.query,
            target_id=target.target_id,
            started_at=started_at,
            completed_at=completed_at,
            listing_count=successful + failed,
            successful_listing_count=successful,
            failed_listing_count=failed,
            listings=tuple(listings),
            errors=tuple(errors),
            status=status,
            warnings=tuple(warnings),
        )
