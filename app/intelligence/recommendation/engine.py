"""Deterministic rule-based Recommendation and Explainability Engine.

Converts ranked DealScore results into clear buying advice.
No LLMs, no live marketplace APIs, and no invented price history.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.deal_score import ListingEvaluation, RankingResult
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.recommendation import (
    AlternativeRecommendation,
    PurchaseDecision,
    Recommendation,
    RecommendationConfidence,
    RecommendationReason,
    RecommendationTradeoff,
    RecommendationWarning,
)
from app.domain.interfaces.recommendation_engine import RecommendationEngine

# Decision thresholds (DealScore is 0–100).
_BUY_SCORE_MIN = 85.0
_CONSIDER_SCORE_MIN = 70.0
_AVOID_SCORE_MAX = 60.0  # best available below this → avoid
_BUY_CONFIDENCE_MIN = 0.75
_HIGH_CONFIDENCE = 0.85

# Price / wait heuristics.
_WEAK_PRICE_SCORE_MAX = 55.0
_MATERIAL_ABOVE_AVG_PCT = 10.0
_MISSING_FIELD_INSUFFICIENT = 4

_CRITICAL_WARNING_FRAGMENTS = (
    "negative and was treated as invalid",
    "critical",
    "safety",
    "cannot be evaluated",
)

# Phrases the engine must never emit (no fabricated price history).
_FORBIDDEN_HISTORY_FRAGMENTS = (
    "will fall",
    "will drop",
    "expected to fall",
    "sale is expected",
    "wait a few days",
    "wait until",
    "historically high",
    "historically low",
    "price history",
    "lowest in",
    "highest in",
)

_QUALITY_GAIN_LABELS: tuple[tuple[str, str], ...] = (
    ("official_store_score", "official-store status"),
    ("seller_score", "stronger seller protection"),
    ("warranty_score", "warranty"),
    ("return_policy_score", "returns"),
    ("shipping_score", "shipping"),
    ("availability_score", "availability"),
)


class RuleBasedRecommendationEngine(RecommendationEngine):
    """Rule-based recommendation implementation over DealScore rankings."""

    @property
    def engine_name(self) -> str:
        return "rule_based_recommendation_v1"

    def recommend(self, ranking: RankingResult) -> Recommendation:
        """Derive a deterministic purchase recommendation from rankings."""
        evaluations = list(ranking.evaluations)
        available = _available_evaluations(evaluations)
        currency = ranking.currency or ""

        if _has_mixed_currency_signal(evaluations):
            return self._insufficient(
                ranking=ranking,
                headline="Mixed currencies cannot be compared",
                summary=(
                    "Listings use more than one currency, so DealBrain cannot produce "
                    "a reliable purchase recommendation without conversion."
                ),
                warnings=(
                    RecommendationWarning(
                        text="Mixed currencies were detected; no purchase advice is offered."
                    ),
                ),
                confidence_value=0.2,
                factors=("mixed_currencies",),
            )

        if not evaluations:
            return self._insufficient(
                ranking=ranking,
                headline="No listings to evaluate",
                summary=(
                    "No marketplace listings were available for this query, "
                    "so DealBrain cannot recommend a purchase."
                ),
                warnings=(
                    RecommendationWarning(text="No comparable listings were returned."),
                ),
                confidence_value=0.15,
                factors=("no_listings",),
            )

        if not available:
            return self._build(
                ranking=ranking,
                decision=PurchaseDecision.AVOID,
                recommended=None,
                headline="No available listings",
                summary=(
                    "Every listing in this result set is unavailable, "
                    "so a purchase cannot be recommended right now."
                ),
                reasoning_texts=(
                    "All returned listings are out of stock or otherwise unavailable.",
                ),
                tradeoff_texts=(),
                warning_texts=(
                    "All compared listings are unavailable (out of stock).",
                ),
                confidence_value=0.7,
                factors=("all_unavailable", f"listing_count:{len(evaluations)}"),
                alternatives=(),
            )

        recommended = _select_recommended(ranking, available)
        confidence = self._compute_confidence(ranking, recommended, available)
        missing_count = _missing_attribute_count(recommended)
        critical = _critical_warnings(recommended)
        meaningful_tradeoffs = _has_meaningful_tradeoffs(recommended, available)
        noncritical_missing = 0 < missing_count < _MISSING_FIELD_INSUFFICIENT

        if missing_count >= _MISSING_FIELD_INSUFFICIENT and len(available) < 2:
            return self._insufficient(
                ranking=ranking,
                headline="Too much required information is missing",
                summary=(
                    "Key purchase attributes such as seller rating, shipping, warranty, "
                    "or return policy are missing, so advice would be unreliable."
                ),
                warnings=tuple(
                    RecommendationWarning(text=w) for w in recommended.deal_score.warnings
                )
                or (
                    RecommendationWarning(
                        text="Required listing attributes are missing for a safe recommendation."
                    ),
                ),
                confidence_value=min(confidence.value, 0.35),
                factors=confidence.factors + ("missing_required_attributes",),
                recommended_id=recommended.deal_score.listing_id,
            )

        score = recommended.deal_score.score
        decision = self._decide(
            score=score,
            confidence=confidence.value,
            critical=critical,
            recommended=recommended,
            available=available,
            ranking=ranking,
            meaningful_tradeoffs=meaningful_tradeoffs,
            noncritical_missing=noncritical_missing,
        )

        tied = _tied_top_scores(available)
        reasoning = self._build_reasoning(
            ranking=ranking,
            recommended=recommended,
            available=available,
            decision=decision,
            tied=tied,
            currency=currency,
            confidence=confidence.value,
        )
        tradeoffs = self._build_tradeoffs(
            recommended=recommended,
            available=available,
            currency=currency,
            tied=tied,
        )
        warnings = self._build_warnings(
            recommended=recommended,
            available=available,
            confidence=confidence.value,
            tied=tied,
        )
        alternatives = self._build_alternatives(
            recommended=recommended,
            available=available,
            currency=currency,
        )
        headline, summary = self._headline_and_summary(
            decision=decision,
            recommended=recommended,
            available=available,
            tied=tied,
            confidence=confidence.value,
        )

        recommendation = self._build(
            ranking=ranking,
            decision=decision,
            recommended=recommended,
            headline=headline,
            summary=summary,
            reasoning_texts=reasoning,
            tradeoff_texts=tradeoffs,
            warning_texts=warnings,
            confidence_value=confidence.value,
            factors=confidence.factors,
            alternatives=alternatives,
        )
        _assert_no_price_history(recommendation)
        return recommendation

    def _decide(
        self,
        *,
        score: float,
        confidence: float,
        critical: bool,
        recommended: ListingEvaluation,
        available: Sequence[ListingEvaluation],
        ranking: RankingResult,
        meaningful_tradeoffs: bool,
        noncritical_missing: bool,
    ) -> PurchaseDecision:
        if critical or score < _AVOID_SCORE_MAX:
            return PurchaseDecision.AVOID

        if _should_wait(available, ranking):
            return PurchaseDecision.WAIT

        buy_eligible = (
            score >= _BUY_SCORE_MIN
            and _is_available(recommended)
            and not critical
            and confidence >= _BUY_CONFIDENCE_MIN
            and not meaningful_tradeoffs
            and not noncritical_missing
        )
        if buy_eligible:
            return PurchaseDecision.BUY

        if score >= _CONSIDER_SCORE_MIN or meaningful_tradeoffs or noncritical_missing:
            return PurchaseDecision.CONSIDER

        if score < _AVOID_SCORE_MAX:
            return PurchaseDecision.AVOID

        return PurchaseDecision.CONSIDER

    def _compute_confidence(
        self,
        ranking: RankingResult,
        recommended: ListingEvaluation,
        available: Sequence[ListingEvaluation],
    ) -> RecommendationConfidence:
        factors: list[str] = []
        value = 0.42

        n = len(available)
        if n >= 4:
            value += 0.18
            factors.append("comparable_listings:4+")
        elif n == 3:
            value += 0.14
            factors.append("comparable_listings:3")
        elif n == 2:
            value += 0.10
            factors.append("comparable_listings:2")
        else:
            value += 0.02
            factors.append("comparable_listings:1")

        missing = _missing_attribute_count(recommended)
        completeness = max(0.0, 1.0 - (missing / 5.0))
        value += 0.16 * completeness
        factors.append(f"completeness:{completeness:.2f}")

        gap = _score_gap(available)
        if gap >= 10.0:
            value += 0.14
            factors.append("score_gap:large")
        elif gap >= 5.0:
            value += 0.10
            factors.append("score_gap:medium")
        elif gap >= 1.0:
            value += 0.06
            factors.append("score_gap:small")
        elif gap > 0.0:
            value += 0.02
            factors.append("score_gap:tiny")
        else:
            factors.append("score_gap:tie")

        warning_count = len(recommended.deal_score.warnings)
        if warning_count == 0:
            value += 0.08
            factors.append("warnings:none")
        elif warning_count <= 2:
            value -= 0.04
            factors.append("warnings:few")
        else:
            value -= 0.10
            factors.append("warnings:many")

        currencies = {
            evaluation.listing.currency.strip().upper()
            for evaluation in available
            if evaluation.listing.currency.strip()
        }
        if len(currencies) == 1:
            value += 0.06
            factors.append("currency:consistent")
        elif len(currencies) > 1:
            value -= 0.25
            factors.append("currency:mixed")

        if ranking.market_average_total_cost <= 0:
            value -= 0.08
            factors.append("market_average:unavailable")

        clamped = round(max(0.0, min(1.0, value)), 2)
        return RecommendationConfidence(value=clamped, factors=tuple(factors))

    def _build_reasoning(
        self,
        *,
        ranking: RankingResult,
        recommended: ListingEvaluation,
        available: Sequence[ListingEvaluation],
        decision: PurchaseDecision,
        tied: bool,
        currency: str,
        confidence: float,
    ) -> tuple[str, ...]:
        ds = recommended.deal_score
        attrs = recommended.attributes
        listing = recommended.listing
        reasons: list[str] = []

        if tied:
            peers = _tied_peer_ids(available, ds.score)
            reasons.append(
                "The top listings have effectively tied DealScores "
                f"({_format_score(ds.score)}); total cost and listing ID were used "
                f"as deterministic tie-breakers among {', '.join(peers)}."
            )
        else:
            reasons.append(
                f"It has a DealScore of {_format_score(ds.score)}, "
                "the highest among the available listings."
            )

        cheapest = _cheapest(available)
        if cheapest is not None and cheapest.deal_score.listing_id != ds.listing_id:
            delta = ds.total_cost - cheapest.deal_score.total_cost
            if delta > 0:
                reasons.append(
                    f"Its total cost is {_money(delta, currency)} higher than "
                    "the cheapest listing."
                )
                tradeoff = _price_quality_tradeoff(recommended, cheapest, currency)
                if tradeoff:
                    reasons.append(tradeoff)
            elif delta < 0:
                reasons.append(
                    f"Its total cost is {_money(abs(delta), currency)} lower than "
                    "the next compared option."
                )
            else:
                reasons.append("Its total cost matches the cheapest available listing.")
        else:
            reasons.append("It also has the lowest total cost among available listings.")

        if ranking.market_average_total_cost > 0:
            avg = ranking.market_average_total_cost
            diff_pct = ((avg - ds.total_cost) / avg) * 100.0
            if abs(diff_pct) < 0.5:
                reasons.append(
                    "Its total cost is in line with the market average for this set."
                )
            elif diff_pct > 0:
                reasons.append(
                    f"Its total cost is {diff_pct:.1f}% below the market average "
                    f"({_money(avg, currency)})."
                )
            else:
                reasons.append(
                    f"Its total cost is {abs(diff_pct):.1f}% above the market average "
                    f"({_money(avg, currency)})."
                )

        if attrs.is_official_store is True:
            reasons.append("It is sold by an official or authorized store.")
        if listing.rating is not None and listing.rating >= 4.5:
            reasons.append(f"The seller rating is strong ({listing.rating:.2f}/5).")
        if attrs.shipping_cost == 0.0:
            reasons.append("Shipping is free.")
        elif attrs.shipping_cost is not None and attrs.shipping_cost > 0:
            reasons.append(
                f"Shipping adds {_money(attrs.shipping_cost, currency)} to the total cost."
            )
        if attrs.warranty_months is not None and attrs.warranty_months >= 12:
            reasons.append(f"Warranty coverage is {attrs.warranty_months} months.")
        if attrs.return_policy_days is not None and attrs.return_policy_days >= 14:
            reasons.append(f"Return policy allows {attrs.return_policy_days} days.")

        if decision is PurchaseDecision.WAIT:
            reasons.append(
                "Price competitiveness across available listings is weak enough that "
                "an immediate purchase looks unattractive based on current DealScore data."
            )
        if decision is PurchaseDecision.AVOID:
            reasons.append(
                "The best available option does not clear DealBrain's quality threshold "
                "for a confident purchase."
            )

        if confidence < _HIGH_CONFIDENCE:
            reasons.append(
                "Confidence is moderated because comparable evidence is limited "
                "or some listing attributes are incomplete."
            )

        deduped = tuple(dict.fromkeys(r.strip() for r in reasons if r.strip()))
        return deduped

    def _build_tradeoffs(
        self,
        *,
        recommended: ListingEvaluation,
        available: Sequence[ListingEvaluation],
        currency: str,
        tied: bool,
    ) -> tuple[str, ...]:
        tradeoffs: list[str] = []
        ds = recommended.deal_score
        cheapest = _cheapest(available)

        if tied:
            tradeoffs.append(
                "No listing is clearly superior on DealScore alone; "
                "the choice reflects deterministic tie-breakers."
            )

        if cheapest is not None and cheapest.deal_score.listing_id != ds.listing_id:
            delta = ds.total_cost - cheapest.deal_score.total_cost
            if delta > 0:
                tradeoffs.append("It is not the cheapest listing.")
                save = _money(delta, currency)
                weaker = _weaker_protection_note(cheapest)
                if weaker:
                    tradeoffs.append(
                        f"The lowest-priced alternative saves {save} but {weaker}."
                    )
                else:
                    tradeoffs.append(
                        f"The lowest-priced alternative saves {save}."
                    )

        if recommended.attributes.is_official_store is False:
            tradeoffs.append("It is not an official-store listing.")
        if (
            recommended.attributes.warranty_months is not None
            and recommended.attributes.warranty_months < 12
        ):
            tradeoffs.append(
                f"Warranty coverage is only {recommended.attributes.warranty_months} months."
            )
        if (
            recommended.attributes.return_policy_days is not None
            and recommended.attributes.return_policy_days < 14
        ):
            tradeoffs.append(
                "The return window is shorter than the strongest option in this set."
            )

        return tuple(dict.fromkeys(tradeoffs))

    def _build_warnings(
        self,
        *,
        recommended: ListingEvaluation,
        available: Sequence[ListingEvaluation],
        confidence: float,
        tied: bool,
    ) -> tuple[str, ...]:
        warnings: list[str] = [
            "Marketplace results are based on mocked connector data, not live marketplace APIs."
        ]
        warnings.extend(recommended.deal_score.warnings)

        if len(available) == 1:
            warnings.append(
                "Only one available listing was compared; treat this advice cautiously."
            )
        if confidence < _HIGH_CONFIDENCE:
            warnings.append(
                "Recommendation confidence is below 85%; review alternatives before buying."
            )
        if tied:
            warnings.append(
                "Top DealScores are tied; the recommended listing is not clearly superior."
            )
        if _missing_attribute_count(recommended) > 0:
            warnings.append(
                "Some seller, shipping, warranty, or return attributes are missing "
                "or incomplete on the recommended listing."
            )
        return tuple(dict.fromkeys(w for w in warnings if w.strip()))

    def _build_alternatives(
        self,
        *,
        recommended: ListingEvaluation,
        available: Sequence[ListingEvaluation],
        currency: str,
    ) -> tuple[AlternativeRecommendation, ...]:
        recommended_id = recommended.deal_score.listing_id
        others = [e for e in available if e.deal_score.listing_id != recommended_id]
        if not others:
            return ()

        alternatives: list[AlternativeRecommendation] = []
        used_ids: set[str] = set()

        cheapest_overall = _cheapest(available)
        if (
            cheapest_overall is not None
            and cheapest_overall.deal_score.listing_id != recommended_id
        ):
            alternatives.append(
                AlternativeRecommendation(
                    listing_id=cheapest_overall.deal_score.listing_id,
                    label="Lowest total cost",
                    reason=(
                        "Choose this when minimizing immediate cost is the highest priority "
                        f"(total cost {_money(cheapest_overall.deal_score.total_cost, currency)})."
                    ),
                )
            )
            used_ids.add(cheapest_overall.deal_score.listing_id)

        best_seller = max(
            others,
            key=lambda e: (
                e.listing.rating if e.listing.rating is not None else -1.0,
                -e.deal_score.total_cost,
                e.deal_score.listing_id,
            ),
        )
        if (
            best_seller.listing.rating is not None
            and best_seller.deal_score.listing_id not in used_ids
            and (
                recommended.listing.rating is None
                or best_seller.listing.rating > recommended.listing.rating
            )
        ):
            alternatives.append(
                AlternativeRecommendation(
                    listing_id=best_seller.deal_score.listing_id,
                    label="Best seller reputation",
                    reason=(
                        "Choose this when seller rating is the deciding factor "
                        f"({best_seller.listing.rating:.2f}/5)."
                    ),
                )
            )
            used_ids.add(best_seller.deal_score.listing_id)

        best_warranty = max(
            others,
            key=lambda e: (
                e.attributes.warranty_months
                if e.attributes.warranty_months is not None
                else -1,
                -e.deal_score.total_cost,
                e.deal_score.listing_id,
            ),
        )
        rec_warranty = recommended.attributes.warranty_months
        alt_warranty = best_warranty.attributes.warranty_months
        if (
            alt_warranty is not None
            and best_warranty.deal_score.listing_id not in used_ids
            and (rec_warranty is None or alt_warranty > rec_warranty)
        ):
            alternatives.append(
                AlternativeRecommendation(
                    listing_id=best_warranty.deal_score.listing_id,
                    label="Best warranty",
                    reason=(
                        f"Choose this for longer warranty coverage ({alt_warranty} months)."
                    ),
                )
            )
            used_ids.add(best_warranty.deal_score.listing_id)

        best_returns = max(
            others,
            key=lambda e: (
                e.attributes.return_policy_days
                if e.attributes.return_policy_days is not None
                else -1,
                -e.deal_score.total_cost,
                e.deal_score.listing_id,
            ),
        )
        rec_returns = recommended.attributes.return_policy_days
        alt_returns = best_returns.attributes.return_policy_days
        if (
            alt_returns is not None
            and best_returns.deal_score.listing_id not in used_ids
            and (rec_returns is None or alt_returns > rec_returns)
        ):
            alternatives.append(
                AlternativeRecommendation(
                    listing_id=best_returns.deal_score.listing_id,
                    label="Best return policy",
                    reason=(
                        f"Choose this for a longer return window ({alt_returns} days)."
                    ),
                )
            )
            used_ids.add(best_returns.deal_score.listing_id)

        official = next(
            (
                e
                for e in sorted(
                    others,
                    key=lambda e: (e.deal_score.total_cost, e.deal_score.listing_id),
                )
                if e.attributes.is_official_store is True
                and e.deal_score.listing_id not in used_ids
                and recommended.attributes.is_official_store is not True
            ),
            None,
        )
        if official is not None:
            alternatives.append(
                AlternativeRecommendation(
                    listing_id=official.deal_score.listing_id,
                    label="Official-store option",
                    reason="Choose this when buying from an official store is required.",
                )
            )
            used_ids.add(official.deal_score.listing_id)

        # Budget alternative: lowest-cost near-score option that is not the recommendation.
        budget_candidates = [
            e
            for e in others
            if e.deal_score.score >= recommended.deal_score.score - 10.0
            and e.deal_score.total_cost <= recommended.deal_score.total_cost
        ] or [
            e
            for e in others
            if e.deal_score.total_cost < recommended.deal_score.total_cost
        ]
        if budget_candidates:
            budget = min(
                budget_candidates,
                key=lambda e: (e.deal_score.total_cost, e.deal_score.listing_id),
            )
            if budget.deal_score.listing_id not in used_ids:
                alternatives.append(
                    AlternativeRecommendation(
                        listing_id=budget.deal_score.listing_id,
                        label="Best budget alternative",
                        reason=(
                            "Choose this for a lower total cost while staying relatively close "
                            f"in DealScore ({_format_score(budget.deal_score.score)})."
                        ),
                    )
                )

        return tuple(alternatives)

    def _headline_and_summary(
        self,
        *,
        decision: PurchaseDecision,
        recommended: ListingEvaluation,
        available: Sequence[ListingEvaluation],
        tied: bool,
        confidence: float,
    ) -> tuple[str, str]:
        listing = recommended.listing
        marketplace = listing.marketplace.title()
        official = recommended.attributes.is_official_store is True
        store_bit = "official-store " if official else ""
        cautious = confidence < _HIGH_CONFIDENCE or len(available) == 1

        if decision is PurchaseDecision.BUY:
            headline = "Best overall value" if not tied else "Strong tied option"
            if cautious:
                summary = (
                    f"Based on available mocked marketplace data, the {marketplace} "
                    f"{store_bit}listing appears to be the strongest overall purchase."
                )
            else:
                summary = (
                    f"The {marketplace} {store_bit}listing is the strongest overall purchase."
                ).replace("  ", " ")
            return headline, summary

        if decision is PurchaseDecision.CONSIDER:
            headline = "Worth considering"
            summary = (
                f"The {marketplace} listing is a reasonable option among the compared results, "
                "but tradeoffs or incomplete attributes mean it is not a clear buy."
            )
            return headline, summary

        if decision is PurchaseDecision.WAIT:
            headline = "Waiting looks wiser for now"
            summary = (
                "Available listings show weak price competitiveness relative to this result set, "
                "so an immediate purchase is unattractive based on current DealScore evidence."
            )
            return headline, summary

        if decision is PurchaseDecision.AVOID:
            headline = "No strong purchase option"
            summary = (
                f"The best available listing scores {_format_score(recommended.deal_score.score)} "
                "and does not meet DealBrain's threshold for a sound purchase."
            )
            return headline, summary

        headline = "Not enough information"
        summary = (
            "DealBrain does not have enough comparable listing data to give "
            "trustworthy buying advice for this query."
        )
        return headline, summary

    def _insufficient(
        self,
        *,
        ranking: RankingResult,
        headline: str,
        summary: str,
        warnings: tuple[RecommendationWarning, ...],
        confidence_value: float,
        factors: tuple[str, ...],
        recommended_id: str | None = None,
    ) -> Recommendation:
        return self._build(
            ranking=ranking,
            decision=PurchaseDecision.INSUFFICIENT_INFORMATION,
            recommended=None,
            headline=headline,
            summary=summary,
            reasoning_texts=(
                "There are not enough valid comparable listings to support a purchase decision.",
            ),
            tradeoff_texts=(),
            warning_texts=tuple(w.text for w in warnings),
            confidence_value=confidence_value,
            factors=factors,
            alternatives=(),
            recommended_id_override=recommended_id,
        )

    def _build(
        self,
        *,
        ranking: RankingResult,
        decision: PurchaseDecision,
        recommended: ListingEvaluation | None,
        headline: str,
        summary: str,
        reasoning_texts: Sequence[str],
        tradeoff_texts: Sequence[str],
        warning_texts: Sequence[str],
        confidence_value: float,
        factors: Sequence[str],
        alternatives: Sequence[AlternativeRecommendation],
        recommended_id_override: str | None = None,
    ) -> Recommendation:
        listing_id = recommended_id_override
        if listing_id is None and recommended is not None:
            listing_id = recommended.deal_score.listing_id
        return Recommendation(
            decision=decision,
            recommended_listing_id=listing_id,
            headline=headline,
            summary=summary,
            reasoning=tuple(
                RecommendationReason(text=text, rank=index)
                for index, text in enumerate(reasoning_texts, start=1)
            ),
            tradeoffs=tuple(RecommendationTradeoff(text=text) for text in tradeoff_texts),
            warnings=tuple(RecommendationWarning(text=text) for text in warning_texts),
            confidence=RecommendationConfidence(
                value=round(confidence_value, 2),
                factors=tuple(factors),
            ),
            alternatives=tuple(alternatives),
        )


def _available_evaluations(
    evaluations: Sequence[ListingEvaluation],
) -> list[ListingEvaluation]:
    return [e for e in evaluations if _is_available(e)]


def _is_available(evaluation: ListingEvaluation) -> bool:
    return evaluation.listing.availability is not AvailabilityStatus.OUT_OF_STOCK


def _select_recommended(
    ranking: RankingResult,
    available: Sequence[ListingEvaluation],
) -> ListingEvaluation:
    if ranking.recommended_listing_id:
        for evaluation in available:
            if evaluation.deal_score.listing_id == ranking.recommended_listing_id:
                return evaluation
    # Deterministic fallback: DealScore order already prefers score, cost, id.
    return sorted(
        available,
        key=lambda e: (
            -e.deal_score.score,
            e.deal_score.total_cost,
            e.deal_score.listing_id,
        ),
    )[0]


def _score_gap(available: Sequence[ListingEvaluation]) -> float:
    if len(available) < 2:
        return 0.0
    ordered = sorted(available, key=lambda e: -e.deal_score.score)
    return round(ordered[0].deal_score.score - ordered[1].deal_score.score, 1)


def _tied_top_scores(available: Sequence[ListingEvaluation]) -> bool:
    if len(available) < 2:
        return False
    ordered = sorted(available, key=lambda e: -e.deal_score.score)
    return ordered[0].deal_score.score == ordered[1].deal_score.score


def _tied_peer_ids(available: Sequence[ListingEvaluation], score: float) -> list[str]:
    peers = [
        e.deal_score.listing_id
        for e in sorted(available, key=lambda e: e.deal_score.listing_id)
        if e.deal_score.score == score
    ]
    return peers


def _cheapest(available: Sequence[ListingEvaluation]) -> ListingEvaluation | None:
    if not available:
        return None
    return min(
        available,
        key=lambda e: (e.deal_score.total_cost, e.deal_score.listing_id),
    )


def _missing_attribute_count(evaluation: ListingEvaluation) -> int:
    listing = evaluation.listing
    attrs = evaluation.attributes
    missing = 0
    if listing.rating is None:
        missing += 1
    if attrs.shipping_cost is None:
        missing += 1
    if attrs.is_official_store is None:
        missing += 1
    if attrs.warranty_months is None:
        missing += 1
    if attrs.return_policy_days is None:
        missing += 1
    return missing


def _critical_warnings(evaluation: ListingEvaluation) -> bool:
    for warning in evaluation.deal_score.warnings:
        lowered = warning.lower()
        if any(fragment in lowered for fragment in _CRITICAL_WARNING_FRAGMENTS):
            return True
    return False


def _has_meaningful_tradeoffs(
    recommended: ListingEvaluation,
    available: Sequence[ListingEvaluation],
) -> bool:
    cheapest = _cheapest(available)
    if cheapest is None:
        return False
    if cheapest.deal_score.listing_id == recommended.deal_score.listing_id:
        return False
    cost_delta = recommended.deal_score.total_cost - cheapest.deal_score.total_cost
    score_delta = recommended.deal_score.score - cheapest.deal_score.score
    # Expensive upgrade with only a tiny score gain is a meaningful tradeoff.
    if cost_delta >= 500 and score_delta < 3.0:
        return True
    # Large premium relative to score gain.
    return bool(cost_delta >= 2000 and score_delta < 8.0)


def _should_wait(
    available: Sequence[ListingEvaluation],
    ranking: RankingResult,
) -> bool:
    if not available:
        return False

    price_scores = [e.deal_score.components.price_score for e in available]
    if price_scores and all(score < _WEAK_PRICE_SCORE_MAX for score in price_scores):
        return True

    if ranking.market_average_total_cost <= 0:
        return True

    avg = ranking.market_average_total_cost
    above = []
    for evaluation in available:
        if evaluation.deal_score.total_cost <= 0:
            continue
        pct_above = ((evaluation.deal_score.total_cost - avg) / avg) * 100.0
        above.append(pct_above >= _MATERIAL_ABOVE_AVG_PCT)
    # With a peer-derived average this is rare; keep the rule for synthetic inputs
    # where every listing can sit above a provided market average.
    if above and all(above):
        return True

    incomplete_costs = sum(
        1
        for evaluation in available
        if any(
            "incomplete total cost" in warning.lower()
            or "shipping data is missing" in warning.lower()
            for warning in evaluation.deal_score.warnings
        )
    )
    return incomplete_costs == len(available)


def _has_mixed_currency_signal(evaluations: Sequence[ListingEvaluation]) -> bool:
    currencies = {
        evaluation.listing.currency.strip().upper()
        for evaluation in evaluations
        if evaluation.listing.currency and evaluation.listing.currency.strip()
    }
    return len(currencies) > 1


def _price_quality_tradeoff(
    recommended: ListingEvaluation,
    cheaper: ListingEvaluation,
    currency: str,
) -> str | None:
    cost_delta = recommended.deal_score.total_cost - cheaper.deal_score.total_cost
    score_delta = recommended.deal_score.score - cheaper.deal_score.score
    if cost_delta <= 0:
        return None

    gains: list[str] = []
    rec_c = recommended.deal_score.components
    cheap_c = cheaper.deal_score.components
    for attr, label in _QUALITY_GAIN_LABELS:
        if getattr(rec_c, attr) > getattr(cheap_c, attr):
            gains.append(label)

    gain_clause = ", ".join(gains) if gains else "stronger overall DealScore components"
    # Oxford-style join for readability when multiple gains.
    if len(gains) > 1:
        gain_clause = ", ".join(gains[:-1]) + f", and {gains[-1]}"

    score_bit = (
        f"gains {_format_score(score_delta)} DealScore points"
        if score_delta > 0
        else "offers a stronger overall DealScore profile"
    )
    return (
        f"The recommended listing costs {_money(cost_delta, currency)} more than "
        f"the cheapest option, but {score_bit} from {gain_clause}."
    )


def _weaker_protection_note(evaluation: ListingEvaluation) -> str:
    parts: list[str] = []
    if evaluation.attributes.is_official_store is False:
        parts.append("no official-store status")
    if evaluation.listing.rating is not None and evaluation.listing.rating < 4.5:
        parts.append("a weaker seller rating")
    if (
        evaluation.attributes.warranty_months is not None
        and evaluation.attributes.warranty_months < 12
    ):
        parts.append("shorter warranty")
    if (
        evaluation.attributes.return_policy_days is not None
        and evaluation.attributes.return_policy_days < 14
    ):
        parts.append("a shorter return window")
    if not parts:
        return "has a weaker overall protection profile"
    if len(parts) == 1:
        return f"has {parts[0]}"
    return "has " + ", ".join(parts[:-1]) + f", and {parts[-1]}"


def _money(amount: float, currency: str) -> str:
    code = (currency or "").strip().upper()
    rounded = round(amount)
    formatted = f"{rounded:,.0f}" if abs(amount - rounded) < 0.05 else f"{amount:,.2f}"
    if code == "PHP":
        return f"₱{formatted}"
    if code:
        return f"{formatted} {code}"
    return formatted


def _format_score(score: float) -> str:
    return f"{score:.1f}"


def _assert_no_price_history(recommendation: Recommendation) -> None:
    corpus = " ".join(
        [
            recommendation.headline,
            recommendation.summary,
            *[reason.text for reason in recommendation.reasoning],
            *[tradeoff.text for tradeoff in recommendation.tradeoffs],
            *[warning.text for warning in recommendation.warnings],
            *[alt.reason for alt in recommendation.alternatives],
        ]
    ).lower()
    for fragment in _FORBIDDEN_HISTORY_FRAGMENTS:
        if fragment in corpus:
            raise RuntimeError(
                f"Recommendation text must not invent price history (found '{fragment}')."
            )
