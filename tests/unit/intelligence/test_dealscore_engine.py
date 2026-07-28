"""Unit tests for the weighted DealScore engine."""

from __future__ import annotations

import pytest
from app.domain.entities.deal_score import DealListingAttributes, ScoreableListing
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.exceptions import DealScoreValidationError
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.dealscore.engine import DEFAULT_WEIGHTS


def _listing(
    listing_id: str,
    *,
    price: float,
    shipping_cost: float | None = 0.0,
    seller_rating: float | None = 4.8,
    availability: AvailabilityStatus = AvailabilityStatus.IN_STOCK,
    is_official_store: bool | None = True,
    warranty_months: int | None = 12,
    return_policy_days: int | None = 7,
    marketplace: str = "shopee",
    currency: str = "PHP",
) -> ScoreableListing:
    return ScoreableListing(
        listing_id=listing_id,
        marketplace=marketplace,
        title=f"Product {listing_id}",
        price=price,
        currency=currency,
        seller="Test Seller",
        seller_rating=seller_rating,
        url=f"https://example.com/{listing_id}",
        availability=availability,
        shipping_cost=shipping_cost,
        is_official_store=is_official_store,
        warranty_months=warranty_months,
        return_policy_days=return_policy_days,
    )


def test_weights_total_one() -> None:
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9
    engine = WeightedDealScoreEngine()
    assert abs(sum(engine.weights.values()) - 1.0) < 1e-9


def test_invalid_weights_rejected() -> None:
    with pytest.raises(ValueError, match="total 1.0"):
        WeightedDealScoreEngine({"price": 0.5})


def test_cheapest_listing_with_poor_seller_reputation() -> None:
    engine = WeightedDealScoreEngine()
    cheap_poor = _listing("cheap", price=50_000.0, seller_rating=2.0, is_official_store=False)
    pricey_good = _listing(
        "pricey",
        price=55_000.0,
        seller_rating=4.9,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    )

    result = engine.rank("phones", [cheap_poor, pricey_good])
    by_id = {e.deal_score.listing_id: e.deal_score for e in result.evaluations}

    assert by_id["cheap"].components.price_score > by_id["pricey"].components.price_score
    assert by_id["cheap"].components.seller_score < by_id["pricey"].components.seller_score
    # Strong seller + official store can outrank a bare cheap listing.
    assert result.recommended_listing_id == "pricey"
    assert result.evaluations[0].deal_score.listing_id == "pricey"


def test_slightly_more_expensive_official_store() -> None:
    engine = WeightedDealScoreEngine()
    unofficial = _listing(
        "unofficial",
        price=70_000.0,
        shipping_cost=0.0,
        seller_rating=4.2,
        is_official_store=False,
        warranty_months=6,
        return_policy_days=7,
    )
    official = _listing(
        "official",
        price=70_999.0,
        shipping_cost=0.0,
        seller_rating=4.9,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    )

    result = engine.rank("iphone", [unofficial, official])
    assert result.recommended_listing_id == "official"
    assert result.evaluations[0].deal_score.components.official_store_score == 100.0
    assert result.evaluations[1].deal_score.components.official_store_score == 45.0


def test_free_versus_paid_shipping() -> None:
    engine = WeightedDealScoreEngine()
    free = _listing("free", price=10_000.0, shipping_cost=0.0)
    paid = _listing("paid", price=10_000.0, shipping_cost=500.0)

    result = engine.rank("buds", [paid, free])
    scores = {e.deal_score.listing_id: e.deal_score for e in result.evaluations}

    assert scores["free"].total_cost == 10_000.0
    assert scores["paid"].total_cost == 10_500.0
    assert scores["free"].components.shipping_score == 100.0
    assert scores["paid"].components.shipping_score < 100.0
    assert scores["free"].components.price_score > scores["paid"].components.price_score
    assert result.recommended_listing_id == "free"
    assert any("Shipping is free." in line for line in scores["free"].explanation)


def test_unavailable_listings_are_penalized() -> None:
    engine = WeightedDealScoreEngine()
    available = _listing("available", price=20_000.0)
    unavailable = _listing(
        "unavailable",
        price=18_000.0,
        availability=AvailabilityStatus.OUT_OF_STOCK,
    )

    result = engine.rank("tablet", [unavailable, available])
    assert result.recommended_listing_id == "available"
    assert result.evaluations[0].deal_score.listing_id == "available"
    unavailable_score = next(
        e.deal_score for e in result.evaluations if e.deal_score.listing_id == "unavailable"
    )
    assert unavailable_score.components.availability_score == 0.0
    assert any("out of stock" in w.lower() for w in unavailable_score.warnings)


def test_missing_seller_rating_reduces_score_and_warns() -> None:
    engine = WeightedDealScoreEngine()
    missing = _listing("missing", price=15_000.0, seller_rating=None)
    known = _listing("known", price=15_000.0, seller_rating=4.8)

    result = engine.rank("watch", [missing, known])
    by_id = {e.deal_score.listing_id: e.deal_score for e in result.evaluations}

    assert by_id["missing"].components.seller_score == 40.0
    assert any("Seller rating is missing" in w for w in by_id["missing"].warnings)
    assert by_id["known"].components.seller_score > by_id["missing"].components.seller_score


def test_missing_warranty_reduces_score_and_warns() -> None:
    engine = WeightedDealScoreEngine()
    missing = _listing("missing", price=15_000.0, warranty_months=None)
    known = _listing("known", price=15_000.0, warranty_months=12)

    result = engine.rank("watch", [missing, known])
    by_id = {e.deal_score.listing_id: e.deal_score for e in result.evaluations}

    assert by_id["missing"].components.warranty_score == 40.0
    assert any("Warranty information is missing" in w for w in by_id["missing"].warnings)


def test_equal_prices_share_price_score() -> None:
    engine = WeightedDealScoreEngine()
    a = _listing("a", price=12_000.0, shipping_cost=0.0)
    b = _listing("b", price=12_000.0, shipping_cost=0.0)

    result = engine.rank("equal", [a, b])
    scores = [e.deal_score.components.price_score for e in result.evaluations]
    assert scores[0] == scores[1] == 100.0
    assert result.market_average_total_cost == 12_000.0


def test_mixed_currencies_raise_validation_error() -> None:
    engine = WeightedDealScoreEngine()
    php = _listing("php", price=10_000.0, currency="PHP")
    usd = _listing("usd", price=200.0, currency="USD")

    with pytest.raises(DealScoreValidationError, match="Mixed currencies"):
        engine.rank("mixed", [php, usd])


def test_missing_currency_raises_validation_error() -> None:
    engine = WeightedDealScoreEngine()
    listing = _listing("blank", price=10_000.0, currency="  ")

    with pytest.raises(DealScoreValidationError, match="missing a currency"):
        engine.rank("blank", [listing])


def test_negative_and_invalid_values() -> None:
    engine = WeightedDealScoreEngine()
    valid = _listing("valid", price=10_000.0)
    negative_price = _listing("neg_price", price=-100.0)
    negative_shipping = _listing("neg_ship", price=10_000.0, shipping_cost=-50.0)
    bad_rating = _listing("bad_rating", price=10_000.0, seller_rating=9.5)

    result = engine.rank(
        "invalid",
        [valid, negative_price, negative_shipping, bad_rating],
    )
    by_id = {e.deal_score.listing_id: e.deal_score for e in result.evaluations}

    assert by_id["neg_price"].components.price_score == 0.0
    assert any("negative" in w.lower() for w in by_id["neg_price"].warnings)
    assert by_id["neg_ship"].components.shipping_score == 0.0
    assert any("negative" in w.lower() for w in by_id["neg_ship"].warnings)
    assert by_id["bad_rating"].components.seller_score == 40.0
    assert any("outside the valid range" in w for w in by_id["bad_rating"].warnings)
    assert result.recommended_listing_id == "valid"


def test_deterministic_ranking() -> None:
    engine = WeightedDealScoreEngine()
    listings = [
        _listing("b", price=21_000.0, seller_rating=4.1),
        _listing("a", price=20_000.0, seller_rating=4.9, is_official_store=True),
        _listing("c", price=22_000.0, seller_rating=3.5, is_official_store=False),
    ]

    first = engine.rank("det", listings)
    second = engine.rank("det", list(reversed(listings)))

    assert [e.deal_score.listing_id for e in first.evaluations] == [
        e.deal_score.listing_id for e in second.evaluations
    ]
    assert [e.deal_score.score for e in first.evaluations] == [
        e.deal_score.score for e in second.evaluations
    ]
    assert first.recommended_listing_id == second.recommended_listing_id


def test_tied_deal_scores_break_ties_deterministically() -> None:
    engine = WeightedDealScoreEngine()
    twin_a = _listing("alpha", price=15_000.0)
    twin_b = _listing("beta", price=15_000.0)

    result = engine.rank("tie", [twin_b, twin_a])
    # Identical inputs → identical scores; listing_id breaks the tie.
    assert result.evaluations[0].deal_score.score == result.evaluations[1].deal_score.score
    assert [e.deal_score.listing_id for e in result.evaluations] == ["alpha", "beta"]


def test_rating_bands() -> None:
    engine = WeightedDealScoreEngine()
    # Construct near-perfect listing to land in excellent band.
    excellent = _listing(
        "ex",
        price=10_000.0,
        seller_rating=5.0,
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    )
    result = engine.rank("bands", [excellent])
    score = result.evaluations[0].deal_score
    assert score.score >= 90.0
    assert score.rating.value == "excellent"
    assert "price" in score.applied_weights


def test_total_cost_equals_price_plus_shipping() -> None:
    engine = WeightedDealScoreEngine()
    listing = _listing("x", price=70_000.0, shipping_cost=999.0)
    result = engine.rank("cost", [listing])
    assert result.evaluations[0].deal_score.total_cost == 70_999.0


def test_empty_listings_return_empty_ranking() -> None:
    engine = WeightedDealScoreEngine()
    result = engine.rank("empty", [])
    assert result.recommended_listing_id is None
    assert result.evaluations == ()
    assert result.market_average_total_cost == 0.0


def test_deal_listing_attributes_dataclass() -> None:
    attrs = DealListingAttributes(shipping_cost=10.0, is_official_store=True)
    assert attrs.warranty_months is None
    assert attrs.return_policy_days is None
