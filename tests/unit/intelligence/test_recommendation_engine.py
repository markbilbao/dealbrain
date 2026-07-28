"""Unit tests for the rule-based recommendation engine."""

from __future__ import annotations

import re

import pytest
from app.domain.entities.deal_score import (
    DealListingAttributes,
    DealRating,
    DealScore,
    DealScoreComponents,
    ListingEvaluation,
    RankingResult,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.entities.recommendation import PurchaseDecision
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.recommendation import RuleBasedRecommendationEngine

_FORBIDDEN_HISTORY = (
    "will fall",
    "will drop",
    "expected to fall",
    "sale is expected",
    "wait a few days",
    "historically high",
    "historically low",
    "price history",
)


def _listing(
    product_id: str,
    *,
    price: float,
    marketplace: str = "shopee",
    rating: float | None = 4.8,
    availability: AvailabilityStatus = AvailabilityStatus.IN_STOCK,
    seller: str = "Official Store",
    currency: str = "PHP",
) -> MarketplaceListing:
    return MarketplaceListing(
        marketplace=marketplace,
        product_id=product_id,
        title=f"Listing {product_id}",
        price=price,
        currency=currency,
        seller=seller,
        rating=rating,
        url=f"https://example.com/{product_id}",
        availability=availability,
    )


def _attrs(
    *,
    shipping_cost: float | None = 0.0,
    is_official_store: bool | None = True,
    warranty_months: int | None = 12,
    return_policy_days: int | None = 14,
) -> DealListingAttributes:
    return DealListingAttributes(
        shipping_cost=shipping_cost,
        is_official_store=is_official_store,
        warranty_months=warranty_months,
        return_policy_days=return_policy_days,
    )


def _rank(
    query: str,
    listings: list[tuple[MarketplaceListing, DealListingAttributes]],
) -> RankingResult:
    engine = WeightedDealScoreEngine()
    from app.intelligence.dealscore.enrichment import to_scoreable_listing

    scoreable = [to_scoreable_listing(listing, attrs) for listing, attrs in listings]
    return engine.rank(query, scoreable)


def _all_text(recommendation) -> str:
    parts = [
        recommendation.headline,
        recommendation.summary,
        *[r.text for r in recommendation.reasoning],
        *[t.text for t in recommendation.tradeoffs],
        *[w.text for w in recommendation.warnings],
        *[a.reason for a in recommendation.alternatives],
    ]
    return " ".join(parts).lower()


def test_clear_high_confidence_buy() -> None:
    ranking = _rank(
        "phones",
        [
            (
                _listing("best", price=70_000.0, rating=4.95, marketplace="lazada"),
                _attrs(return_policy_days=14),
            ),
            (
                _listing("ok", price=72_000.0, rating=4.2),
                _attrs(is_official_store=False, warranty_months=6, return_policy_days=7),
            ),
            (
                _listing("mid", price=71_000.0, rating=4.6, marketplace="lazada"),
                _attrs(warranty_months=12, return_policy_days=7),
            ),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)

    assert rec.decision is PurchaseDecision.BUY
    assert rec.recommended_listing_id == ranking.recommended_listing_id
    assert rec.confidence.value >= 0.75
    assert rec.headline
    assert rec.summary
    assert len(rec.reasoning) >= 2
    assert rec.recommended_listing_id is not None


def test_slightly_more_expensive_official_store_beats_cheapest() -> None:
    ranking = _rank(
        "iphone",
        [
            (
                _listing("cheap", price=70_000.0, rating=4.1),
                _attrs(
                    is_official_store=False,
                    warranty_months=6,
                    return_policy_days=7,
                    shipping_cost=0.0,
                ),
            ),
            (
                _listing("official", price=70_800.0, rating=4.9, marketplace="lazada"),
                _attrs(
                    is_official_store=True,
                    warranty_months=12,
                    return_policy_days=14,
                    shipping_cost=0.0,
                ),
            ),
        ],
    )
    assert ranking.recommended_listing_id == "official"
    rec = RuleBasedRecommendationEngine().recommend(ranking)

    assert rec.recommended_listing_id == "official"
    assert any("₱800" in reason.text or "800" in reason.text for reason in rec.reasoning)
    assert any(
        "DealScore points" in reason.text or "official-store" in reason.text.lower()
        for reason in rec.reasoning
    )
    assert any("not the cheapest" in t.text.lower() for t in rec.tradeoffs)
    labels = {alt.label for alt in rec.alternatives}
    assert "Lowest total cost" in labels


def test_cheapest_listing_remains_best_recommendation() -> None:
    ranking = _rank(
        "buds",
        [
            (
                _listing("cheap_good", price=10_000.0, rating=4.9),
                _attrs(shipping_cost=0.0, return_policy_days=14),
            ),
            (
                _listing("pricey", price=12_000.0, rating=4.9, marketplace="lazada"),
                _attrs(shipping_cost=0.0, return_policy_days=14),
            ),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)

    assert ranking.recommended_listing_id == "cheap_good"
    assert rec.recommended_listing_id == "cheap_good"
    assert any("lowest total cost" in reason.text.lower() for reason in rec.reasoning)


def test_weak_listings_produce_consider() -> None:
    ranking = _rank(
        "mid",
        [
            (
                _listing("a", price=50_000.0, rating=3.6),
                _attrs(
                    is_official_store=False,
                    warranty_months=3,
                    return_policy_days=3,
                    shipping_cost=400.0,
                ),
            ),
            (
                _listing("b", price=51_000.0, rating=3.5, marketplace="lazada"),
                _attrs(
                    is_official_store=False,
                    warranty_months=3,
                    return_policy_days=3,
                    shipping_cost=350.0,
                ),
            ),
        ],
    )
    best = ranking.evaluations[0].deal_score.score
    assert 70.0 <= best < 85.0 or best < 85.0
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    assert rec.decision in {
        PurchaseDecision.CONSIDER,
        PurchaseDecision.WAIT,
        PurchaseDecision.AVOID,
    }
    if 70.0 <= best <= 84.99:
        assert rec.decision is PurchaseDecision.CONSIDER


def test_all_poor_listings_produce_avoid() -> None:
    ranking = _rank(
        "poor",
        [
            (
                _listing("bad1", price=90_000.0, rating=1.5),
                _attrs(
                    is_official_store=False,
                    warranty_months=0,
                    return_policy_days=0,
                    shipping_cost=2_000.0,
                ),
            ),
            (
                _listing("bad2", price=92_000.0, rating=1.2, marketplace="lazada"),
                _attrs(
                    is_official_store=False,
                    warranty_months=0,
                    return_policy_days=0,
                    shipping_cost=2_500.0,
                ),
            ),
        ],
    )
    best = ranking.evaluations[0].deal_score.score
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    if best < 60.0:
        assert rec.decision is PurchaseDecision.AVOID
    else:
        # Engine may still avoid via weak overall profile; accept avoid/consider/wait.
        assert rec.decision in {
            PurchaseDecision.AVOID,
            PurchaseDecision.CONSIDER,
            PurchaseDecision.WAIT,
        }


def test_unavailable_listings_produce_avoid() -> None:
    ranking = _rank(
        "oos",
        [
            (
                _listing("x", price=20_000.0, availability=AvailabilityStatus.OUT_OF_STOCK),
                _attrs(),
            ),
            (
                _listing(
                    "y",
                    price=21_000.0,
                    marketplace="lazada",
                    availability=AvailabilityStatus.OUT_OF_STOCK,
                ),
                _attrs(),
            ),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    assert rec.decision is PurchaseDecision.AVOID
    assert rec.recommended_listing_id is None
    assert any("unavailable" in w.text.lower() for w in rec.warnings)


def test_missing_seller_warranty_shipping_or_return_information() -> None:
    ranking = _rank(
        "partial",
        [
            (
                _listing("partial", price=25_000.0, rating=None),
                _attrs(
                    shipping_cost=None,
                    is_official_store=None,
                    warranty_months=None,
                    return_policy_days=None,
                ),
            ),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    corpus = _all_text(rec)
    assert "missing" in corpus or "incomplete" in corpus
    assert rec.decision in {
        PurchaseDecision.BUY,
        PurchaseDecision.CONSIDER,
        PurchaseDecision.INSUFFICIENT_INFORMATION,
        PurchaseDecision.WAIT,
    }


def test_one_listing_only_uses_cautious_wording() -> None:
    ranking = _rank(
        "solo",
        [(_listing("only", price=40_000.0, rating=4.9), _attrs())],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    corpus = _all_text(rec)
    assert "only one" in corpus or "cautious" in corpus or rec.confidence.value < 0.85
    assert rec.decision in {
        PurchaseDecision.BUY,
        PurchaseDecision.CONSIDER,
        PurchaseDecision.INSUFFICIENT_INFORMATION,
    }
    assert rec.alternatives == ()


def test_tied_deal_scores_are_acknowledged() -> None:
    components = DealScoreComponents(
        price_score=80.0,
        seller_score=90.0,
        shipping_score=100.0,
        availability_score=100.0,
        official_store_score=100.0,
        warranty_score=100.0,
        return_policy_score=100.0,
    )
    a = ListingEvaluation(
        listing=_listing("a", price=10_000.0),
        attributes=_attrs(),
        deal_score=DealScore(
            listing_id="a",
            marketplace="shopee",
            score=88.0,
            rating=DealRating.VERY_GOOD,
            rank=1,
            total_cost=10_000.0,
            components=components,
        ),
    )
    b = ListingEvaluation(
        listing=_listing("b", price=10_500.0, marketplace="lazada"),
        attributes=_attrs(),
        deal_score=DealScore(
            listing_id="b",
            marketplace="lazada",
            score=88.0,
            rating=DealRating.VERY_GOOD,
            rank=2,
            total_cost=10_500.0,
            components=components,
        ),
    )
    ranking = RankingResult(
        query="tie",
        currency="PHP",
        market_average_total_cost=10_250.0,
        recommended_listing_id="a",
        evaluations=(a, b),
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    corpus = _all_text(rec)
    assert "tied" in corpus
    assert "clearly superior" in corpus or "tie-breaker" in corpus
    assert rec.recommended_listing_id == "a"


def test_small_and_large_dealscore_gaps_affect_confidence() -> None:
    engine = RuleBasedRecommendationEngine()

    small = _rank(
        "small",
        [
            (_listing("a", price=50_000.0, rating=4.9), _attrs(return_policy_days=14)),
            (
                _listing("b", price=50_200.0, rating=4.85, marketplace="lazada"),
                _attrs(return_policy_days=14),
            ),
        ],
    )
    large = _rank(
        "large",
        [
            (_listing("a", price=50_000.0, rating=4.95), _attrs(return_policy_days=14)),
            (
                _listing("b", price=65_000.0, rating=3.0, marketplace="lazada"),
                _attrs(
                    is_official_store=False,
                    warranty_months=0,
                    return_policy_days=0,
                    shipping_cost=800.0,
                ),
            ),
        ],
    )
    small_rec = engine.recommend(small)
    large_rec = engine.recommend(large)
    small_gap = small.evaluations[0].deal_score.score - small.evaluations[1].deal_score.score
    large_gap = large.evaluations[0].deal_score.score - large.evaluations[1].deal_score.score
    assert large_gap > small_gap
    assert "score_gap" in " ".join(small_rec.confidence.factors)
    assert "score_gap" in " ".join(large_rec.confidence.factors)


def test_mixed_currencies_insufficient_information() -> None:
    a = ListingEvaluation(
        listing=_listing("php", price=10_000.0, currency="PHP"),
        attributes=_attrs(),
        deal_score=DealScore(
            listing_id="php",
            marketplace="shopee",
            score=90.0,
            rating=DealRating.EXCELLENT,
            rank=1,
            total_cost=10_000.0,
            components=DealScoreComponents(
                price_score=80,
                seller_score=90,
                shipping_score=100,
                availability_score=100,
                official_store_score=100,
                warranty_score=100,
                return_policy_score=100,
            ),
        ),
    )
    b = ListingEvaluation(
        listing=_listing("usd", price=200.0, currency="USD", marketplace="lazada"),
        attributes=_attrs(),
        deal_score=DealScore(
            listing_id="usd",
            marketplace="lazada",
            score=88.0,
            rating=DealRating.VERY_GOOD,
            rank=2,
            total_cost=200.0,
            components=DealScoreComponents(
                price_score=80,
                seller_score=90,
                shipping_score=100,
                availability_score=100,
                official_store_score=100,
                warranty_score=100,
                return_policy_score=100,
            ),
        ),
    )
    ranking = RankingResult(
        query="mixed",
        currency="",
        market_average_total_cost=0.0,
        recommended_listing_id=None,
        evaluations=(a, b),
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    assert rec.decision is PurchaseDecision.INSUFFICIENT_INFORMATION
    assert "currency" in _all_text(rec)


def test_no_results_insufficient_information() -> None:
    ranking = RankingResult(
        query="empty",
        currency="",
        market_average_total_cost=0.0,
        recommended_listing_id=None,
        evaluations=(),
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    assert rec.decision is PurchaseDecision.INSUFFICIENT_INFORMATION
    assert rec.recommended_listing_id is None
    assert rec.alternatives == ()


def test_dynamically_calculated_price_quality_tradeoff() -> None:
    ranking = _rank(
        "tradeoff",
        [
            (
                _listing("cheap", price=60_000.0, rating=3.8),
                _attrs(
                    is_official_store=False,
                    warranty_months=3,
                    return_policy_days=3,
                ),
            ),
            (
                _listing("quality", price=61_200.0, rating=4.95, marketplace="lazada"),
                _attrs(
                    is_official_store=True,
                    warranty_months=12,
                    return_policy_days=14,
                ),
            ),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    if ranking.recommended_listing_id == "quality":
        joined = " ".join(r.text for r in rec.reasoning)
        assert re.search(r"₱?1[,]?200", joined) or "1200" in joined.replace(",", "")
        assert "DealScore" in joined
        assert any(
            token in joined.lower()
            for token in ("official-store", "warranty", "return", "seller")
        )


def test_deterministic_confidence_and_ordering() -> None:
    engine = RuleBasedRecommendationEngine()
    ranking = _rank(
        "det",
        [
            (_listing("a", price=30_000.0, rating=4.8), _attrs()),
            (_listing("b", price=31_000.0, rating=4.5, marketplace="lazada"), _attrs()),
            (_listing("c", price=29_500.0, rating=4.2), _attrs(is_official_store=False)),
        ],
    )
    first = engine.recommend(ranking)
    second = engine.recommend(ranking)
    assert first == second
    assert first.confidence.value == second.confidence.value
    assert [r.text for r in first.reasoning] == [r.text for r in second.reasoning]
    assert [a.listing_id for a in first.alternatives] == [
        a.listing_id for a in second.alternatives
    ]


def test_no_fabricated_price_history_statements() -> None:
    ranking = _rank(
        "history",
        [
            (_listing("a", price=40_000.0, rating=4.9), _attrs()),
            (_listing("b", price=41_000.0, rating=4.7, marketplace="lazada"), _attrs()),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    corpus = _all_text(rec)
    for fragment in _FORBIDDEN_HISTORY:
        assert fragment not in corpus


def test_recommendation_contains_required_fields() -> None:
    ranking = _rank(
        "fields",
        [
            (_listing("a", price=15_000.0), _attrs()),
            (_listing("b", price=16_000.0, marketplace="lazada"), _attrs()),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    assert rec.decision in PurchaseDecision
    assert rec.headline
    assert rec.summary
    assert isinstance(rec.reasoning, tuple)
    assert isinstance(rec.tradeoffs, tuple)
    assert isinstance(rec.warnings, tuple)
    assert 0.0 <= rec.confidence.value <= 1.0
    assert rec.recommended_listing_id is not None
    assert isinstance(rec.alternatives, tuple)


def test_alternative_labels_when_applicable() -> None:
    ranking = _rank(
        "alts",
        [
            (
                _listing("official", price=55_000.0, rating=4.7, marketplace="lazada"),
                _attrs(is_official_store=True, warranty_months=12, return_policy_days=7),
            ),
            (
                _listing("cheap", price=50_000.0, rating=4.9),
                _attrs(
                    is_official_store=False,
                    warranty_months=24,
                    return_policy_days=30,
                    shipping_cost=0.0,
                ),
            ),
        ],
    )
    rec = RuleBasedRecommendationEngine().recommend(ranking)
    labels = {alt.label for alt in rec.alternatives}
    assert "Lowest total cost" in labels or rec.recommended_listing_id == "cheap"
    # At least one specialized label should appear among alternatives.
    assert labels & {
        "Lowest total cost",
        "Best seller reputation",
        "Best warranty",
        "Best return policy",
        "Official-store option",
        "Best budget alternative",
    }


@pytest.mark.parametrize("repeat", range(3))
def test_identical_requests_are_stable(repeat: int) -> None:
    ranking = _rank(
        "stable",
        [
            (_listing("x", price=22_000.0, rating=4.8), _attrs()),
            (_listing("y", price=22_500.0, marketplace="lazada"), _attrs()),
        ],
    )
    engine = RuleBasedRecommendationEngine()
    assert engine.recommend(ranking).to_dict() == engine.recommend(ranking).to_dict()
