"""Deterministic weighted DealScore engine.

Evaluates normalized marketplace listings using fixed component weights.
No LLMs and no live marketplace API calls.
"""

from __future__ import annotations

from collections.abc import Sequence
from statistics import fmean

from app.domain.entities.deal_score import (
    DealListingAttributes,
    DealScore,
    DealScoreComponents,
    ListingEvaluation,
    RankingResult,
    ScoreableListing,
    rating_for_score,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.exceptions import DealScoreValidationError
from app.domain.interfaces.deal_score_engine import DealScoreEngine

# Weights must total 100% (1.0).
DEFAULT_WEIGHTS: dict[str, float] = {
    "price": 0.35,
    "seller": 0.20,
    "shipping": 0.10,
    "availability": 0.10,
    "official_store": 0.10,
    "warranty": 0.10,
    "return_policy": 0.05,
}

_SELLER_RATING_MIN = 0.0
_SELLER_RATING_MAX = 5.0
_MISSING_COMPONENT_SCORE = 40.0


def _round_score(value: float) -> float:
    return round(value, 1)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


class WeightedDealScoreEngine(DealScoreEngine):
    """Explainable DealScore implementation using fixed component weights."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        resolved = dict(weights or DEFAULT_WEIGHTS)
        total = sum(resolved.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"DealScore weights must total 1.0; got {total}")
        self._weights = resolved

    @property
    def engine_name(self) -> str:
        return "weighted_deal_score_v1"

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._weights)

    def rank(self, query: str, listings: Sequence[ScoreableListing]) -> RankingResult:
        """Evaluate listings, rank best → worst, and pick a recommendation."""
        cleaned_query = query.strip()
        if not listings:
            return RankingResult(
                query=cleaned_query,
                currency="",
                market_average_total_cost=0.0,
                recommended_listing_id=None,
                evaluations=(),
            )

        currencies = {listing.currency.strip().upper() for listing in listings if listing.currency}
        blank_currency = any(not listing.currency.strip() for listing in listings)
        if blank_currency:
            raise DealScoreValidationError(
                "One or more listings are missing a currency; DealScore cannot evaluate them."
            )
        if len(currencies) > 1:
            joined = ", ".join(sorted(currencies))
            raise DealScoreValidationError(
                f"Mixed currencies cannot be compared directly ({joined}). "
                "Separate results by currency; no conversion is performed."
            )

        currency = next(iter(currencies))
        peer_costs = [
            cost
            for listing in listings
            if (cost := listing.total_cost) is not None
            and listing.availability is not AvailabilityStatus.OUT_OF_STOCK
        ]
        market_average = round(fmean(peer_costs), 2) if peer_costs else 0.0

        scored: list[tuple[ScoreableListing, DealScore]] = []
        for listing in listings:
            deal_score = self._score_listing(listing, peer_costs, market_average, rank=0)
            scored.append((listing, deal_score))

        scored.sort(key=self._sort_key)

        evaluations: list[ListingEvaluation] = []
        for rank, (listing, provisional) in enumerate(scored, start=1):
            ranked = DealScore(
                listing_id=provisional.listing_id,
                marketplace=provisional.marketplace,
                score=provisional.score,
                rating=provisional.rating,
                rank=rank,
                total_cost=provisional.total_cost,
                components=provisional.components,
                explanation=provisional.explanation,
                warnings=provisional.warnings,
                applied_weights=provisional.applied_weights,
            )
            source = listing.source_listing or MarketplaceListing(
                marketplace=listing.marketplace,
                product_id=listing.listing_id,
                title=listing.title,
                price=listing.price,
                currency=listing.currency,
                seller=listing.seller,
                rating=listing.seller_rating,
                url=listing.url,
                availability=listing.availability,
            )
            evaluations.append(
                ListingEvaluation(
                    listing=source,
                    attributes=DealListingAttributes(
                        shipping_cost=listing.shipping_cost,
                        is_official_store=listing.is_official_store,
                        warranty_months=listing.warranty_months,
                        return_policy_days=listing.return_policy_days,
                    ),
                    deal_score=ranked,
                )
            )

        recommended_id = self._pick_recommendation(evaluations)
        return RankingResult(
            query=cleaned_query,
            currency=currency,
            market_average_total_cost=market_average,
            recommended_listing_id=recommended_id,
            evaluations=tuple(evaluations),
        )

    def _score_listing(
        self,
        listing: ScoreableListing,
        peer_costs: Sequence[float],
        market_average: float,
        rank: int,
    ) -> DealScore:
        warnings: list[str] = []
        explanation: list[str] = []

        price_score, price_notes, price_warnings = self._price_score(
            listing, peer_costs, market_average
        )
        seller_score, seller_notes, seller_warnings = self._seller_score(listing)
        shipping_score, shipping_notes, shipping_warnings = self._shipping_score(listing)
        availability_score, availability_notes, availability_warnings = self._availability_score(
            listing
        )
        official_score, official_notes, official_warnings = self._official_store_score(listing)
        warranty_score, warranty_notes, warranty_warnings = self._warranty_score(listing)
        return_score, return_notes, return_warnings = self._return_policy_score(listing)

        for bucket in (
            price_warnings,
            seller_warnings,
            shipping_warnings,
            availability_warnings,
            official_warnings,
            warranty_warnings,
            return_warnings,
        ):
            warnings.extend(bucket)
        for bucket in (
            price_notes,
            seller_notes,
            shipping_notes,
            availability_notes,
            official_notes,
            warranty_notes,
            return_notes,
        ):
            explanation.extend(bucket)

        if listing.price < 0:
            warnings.append("Listing price is negative and was treated as invalid.")
        if listing.shipping_cost is not None and listing.shipping_cost < 0:
            warnings.append("Shipping cost is negative and was treated as invalid.")

        components = DealScoreComponents(
            price_score=_round_score(price_score),
            seller_score=_round_score(seller_score),
            shipping_score=_round_score(shipping_score),
            availability_score=_round_score(availability_score),
            official_store_score=_round_score(official_score),
            warranty_score=_round_score(warranty_score),
            return_policy_score=_round_score(return_score),
        )

        weighted = (
            components.price_score * self._weights["price"]
            + components.seller_score * self._weights["seller"]
            + components.shipping_score * self._weights["shipping"]
            + components.availability_score * self._weights["availability"]
            + components.official_store_score * self._weights["official_store"]
            + components.warranty_score * self._weights["warranty"]
            + components.return_policy_score * self._weights["return_policy"]
        )
        score = _round_score(_clamp(weighted))

        total_cost = listing.total_cost
        if total_cost is None:
            # Fall back to price alone only for display; ranking already penalizes missing shipping.
            total_cost = round(max(listing.price, 0.0), 2)
            warnings.append(
                "Total purchase cost could not include shipping; "
                "shipping data is missing or invalid."
            )

        return DealScore(
            listing_id=listing.listing_id,
            marketplace=listing.marketplace,
            score=score,
            rating=rating_for_score(score),
            rank=rank,
            total_cost=total_cost,
            components=components,
            explanation=tuple(explanation),
            warnings=tuple(dict.fromkeys(warnings)),
            applied_weights=dict(self._weights),
        )

    def _price_score(
        self,
        listing: ScoreableListing,
        peer_costs: Sequence[float],
        market_average: float,
    ) -> tuple[float, list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        total_cost = listing.total_cost

        if listing.price < 0:
            return 0.0, notes, warnings
        if total_cost is None:
            warnings.append("Price competitiveness used an incomplete total cost.")
            return _MISSING_COMPONENT_SCORE, notes, warnings
        if market_average <= 0 or not peer_costs:
            warnings.append("No valid peer total costs were available for price comparison.")
            return _MISSING_COMPONENT_SCORE, notes, warnings

        min_cost = min(peer_costs)
        max_cost = max(peer_costs)
        pct_vs_avg = ((market_average - total_cost) / market_average) * 100.0

        if max_cost == min_cost:
            score = 100.0
            notes.append("Total cost matches the other listings in this result set.")
        else:
            # Soft curve vs market average so small gaps do not dominate quality factors.
            # At average → 80; each 1% below average adds 2 pts; each 1% above subtracts 2 pts.
            score = _clamp(80.0 + pct_vs_avg * 2.0)

        if abs(pct_vs_avg) < 0.05:
            notes.append("Total cost is in line with the market average.")
        elif pct_vs_avg > 0:
            notes.append(f"Total cost is {pct_vs_avg:.1f}% below the market average.")
        else:
            notes.append(f"Total cost is {abs(pct_vs_avg):.1f}% above the market average.")
        return score, notes, warnings

    def _seller_score(
        self, listing: ScoreableListing
    ) -> tuple[float, list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        rating = listing.seller_rating
        if rating is None:
            warnings.append("Seller rating is missing; seller score was reduced.")
            return _MISSING_COMPONENT_SCORE, notes, warnings
        if rating < _SELLER_RATING_MIN or rating > _SELLER_RATING_MAX:
            warnings.append(
                f"Seller rating {rating} is outside the valid range "
                f"{_SELLER_RATING_MIN}-{_SELLER_RATING_MAX}; seller score was reduced."
            )
            return _MISSING_COMPONENT_SCORE, notes, warnings

        score = _clamp((rating / _SELLER_RATING_MAX) * 100.0)
        if rating >= 4.5:
            notes.append("The seller has a strong marketplace rating.")
        elif rating >= 4.0:
            notes.append("The seller has a solid marketplace rating.")
        elif rating >= 3.0:
            notes.append("The seller has an average marketplace rating.")
        else:
            notes.append("The seller has a weak marketplace rating.")
        return score, notes, warnings

    def _shipping_score(
        self, listing: ScoreableListing
    ) -> tuple[float, list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        shipping = listing.shipping_cost
        if shipping is None:
            warnings.append("Shipping cost is missing; shipping score was reduced.")
            return _MISSING_COMPONENT_SCORE, notes, warnings
        if shipping < 0:
            return 0.0, notes, warnings
        if shipping == 0:
            notes.append("Shipping is free.")
            return 100.0, notes, warnings

        # Paid shipping: decay relative to listing price when available.
        if listing.price > 0:
            burden = (shipping / listing.price) * 100.0
            score = _clamp(100.0 - burden * 4.0)
        else:
            score = _clamp(100.0 - shipping / 25.0)
        notes.append(f"Shipping costs {shipping:.2f} {listing.currency}.")
        return score, notes, warnings

    def _availability_score(
        self, listing: ScoreableListing
    ) -> tuple[float, list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        status = listing.availability
        if status is AvailabilityStatus.IN_STOCK:
            notes.append("The product is currently in stock.")
            return 100.0, notes, warnings
        if status is AvailabilityStatus.LIMITED:
            notes.append("Stock is limited.")
            return 70.0, notes, warnings
        if status is AvailabilityStatus.OUT_OF_STOCK:
            warnings.append("Listing is unavailable (out of stock).")
            notes.append("The product is out of stock.")
            return 0.0, notes, warnings
        warnings.append("Availability is unknown; availability score was reduced.")
        return _MISSING_COMPONENT_SCORE, notes, warnings

    def _official_store_score(
        self, listing: ScoreableListing
    ) -> tuple[float, list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        flag = listing.is_official_store
        if flag is None:
            warnings.append("Official store status is unknown; score was reduced.")
            return _MISSING_COMPONENT_SCORE, notes, warnings
        if flag:
            notes.append("Sold by an official or authorized store.")
            return 100.0, notes, warnings
        notes.append("Sold by a non-official marketplace seller.")
        return 45.0, notes, warnings

    def _warranty_score(
        self, listing: ScoreableListing
    ) -> tuple[float, list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        months = listing.warranty_months
        if months is None:
            warnings.append("Warranty information is missing; warranty score was reduced.")
            return _MISSING_COMPONENT_SCORE, notes, warnings
        if months < 0:
            warnings.append("Warranty months are invalid; warranty score was reduced.")
            return 0.0, notes, warnings
        if months >= 12:
            notes.append(f"Includes a {months}-month warranty.")
            return 100.0, notes, warnings
        if months >= 6:
            notes.append(f"Includes a {months}-month warranty.")
            return 80.0, notes, warnings
        if months > 0:
            notes.append(f"Includes a short {months}-month warranty.")
            return 55.0, notes, warnings
        warnings.append("No warranty is offered.")
        return 20.0, notes, warnings

    def _return_policy_score(
        self, listing: ScoreableListing
    ) -> tuple[float, list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        days = listing.return_policy_days
        if days is None:
            warnings.append("Return policy is missing; return policy score was reduced.")
            return _MISSING_COMPONENT_SCORE, notes, warnings
        if days < 0:
            warnings.append("Return policy days are invalid; return policy score was reduced.")
            return 0.0, notes, warnings
        if days >= 14:
            notes.append(f"Offers a {days}-day return window.")
            return 100.0, notes, warnings
        if days >= 7:
            notes.append(f"Offers a {days}-day return window.")
            return 75.0, notes, warnings
        if days > 0:
            notes.append(f"Offers a short {days}-day return window.")
            return 50.0, notes, warnings
        warnings.append("No return window is offered.")
        return 20.0, notes, warnings

    @staticmethod
    def _sort_key(
        item: tuple[ScoreableListing, DealScore],
    ) -> tuple[int, float, float, str, str]:
        listing, score = item
        unavailable = 1 if listing.availability is AvailabilityStatus.OUT_OF_STOCK else 0
        total_cost = listing.total_cost if listing.total_cost is not None else float("inf")
        # Best first: available, higher score, lower total cost, stable ids.
        return (
            unavailable,
            -score.score,
            total_cost,
            listing.listing_id,
            listing.marketplace,
        )

    @staticmethod
    def _pick_recommendation(evaluations: Sequence[ListingEvaluation]) -> str | None:
        for evaluation in evaluations:
            if evaluation.listing.availability is AvailabilityStatus.OUT_OF_STOCK:
                continue
            return evaluation.deal_score.listing_id
        return None
