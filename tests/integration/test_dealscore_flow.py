"""Integration tests for DealScore recommendation flow."""

from __future__ import annotations

import pytest
from app.domain.entities.deal_score import DealListingAttributes
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.exceptions import DealScoreValidationError
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService


def _service() -> DealRecommendationService:
    marketplace = MarketplaceIntelligenceService(
        connectors=[ShopeeConnector(), LazadaConnector()]
    )
    return DealRecommendationService(marketplace, WeightedDealScoreEngine())


def test_integration_iphone_recommendation_uses_total_cost() -> None:
    result = _service().recommend("iPhone 17 Pro Max")

    assert result.currency == "PHP"
    assert len(result.evaluations) >= 2
    assert result.recommended_listing_id is not None
    assert result.market_average_total_cost > 0

    recommended = result.recommended
    assert recommended is not None
    assert recommended.deal_score.rank == 1
    assert recommended.attributes.shipping_cost is not None
    assert recommended.deal_score.total_cost == pytest.approx(
        recommended.listing.price + recommended.attributes.shipping_cost,
        abs=0.01,
    )


def test_integration_out_of_stock_samsung_not_recommended() -> None:
    result = _service().recommend("Samsung Galaxy")
    assert result.evaluations
    for evaluation in result.evaluations:
        if evaluation.listing.availability is AvailabilityStatus.OUT_OF_STOCK:
            assert evaluation.deal_score.listing_id != result.recommended_listing_id
            assert evaluation.deal_score.components.availability_score == 0.0


def test_integration_free_vs_paid_shipping_scenario() -> None:
    service = DealRecommendationService(
        MarketplaceIntelligenceService(connectors=[]),
        WeightedDealScoreEngine(),
    )
    listings = [
        MarketplaceListing(
            marketplace="shopee",
            product_id="free",
            title="Free ship",
            price=10_000.0,
            currency="PHP",
            seller="Official Store",
            rating=4.8,
            url="https://example.com/free",
            availability=AvailabilityStatus.IN_STOCK,
        ),
        MarketplaceListing(
            marketplace="lazada",
            product_id="paid",
            title="Paid ship",
            price=10_000.0,
            currency="PHP",
            seller="Official Store",
            rating=4.8,
            url="https://example.com/paid",
            availability=AvailabilityStatus.IN_STOCK,
        ),
    ]
    attrs = {
        "free": DealListingAttributes(
            shipping_cost=0.0,
            is_official_store=True,
            warranty_months=12,
            return_policy_days=7,
        ),
        "paid": DealListingAttributes(
            shipping_cost=400.0,
            is_official_store=True,
            warranty_months=12,
            return_policy_days=7,
        ),
    }

    result = service.evaluate_listings("buds", listings, attrs)
    assert result.recommended_listing_id == "free"
    assert result.evaluations[0].deal_score.total_cost == 10_000.0
    assert result.evaluations[1].deal_score.total_cost == 10_400.0


def test_integration_mixed_currencies_rejected() -> None:
    service = DealRecommendationService(
        MarketplaceIntelligenceService(connectors=[]),
        WeightedDealScoreEngine(),
    )
    listings = [
        MarketplaceListing(
            marketplace="shopee",
            product_id="php",
            title="PHP item",
            price=10_000.0,
            currency="PHP",
            seller="Store",
            rating=4.5,
            url="https://example.com/php",
            availability=AvailabilityStatus.IN_STOCK,
        ),
        MarketplaceListing(
            marketplace="lazada",
            product_id="usd",
            title="USD item",
            price=200.0,
            currency="USD",
            seller="Store",
            rating=4.5,
            url="https://example.com/usd",
            availability=AvailabilityStatus.IN_STOCK,
        ),
    ]
    with pytest.raises(DealScoreValidationError, match="Mixed currencies"):
        service.evaluate_listings("mixed", listings)
