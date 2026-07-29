"""Sprint 20 unit tests — affiliate link generation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.affiliate.linking.builder import AffiliateLinkBuilder
from app.affiliate.memory import InMemoryAffiliateRepository
from app.domain.entities.shopping_assistant import ShoppingRecommendation
from app.domain.exceptions import AffiliateValidationError
from app.services.affiliate_link_service import AffiliateLinkService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _service() -> AffiliateLinkService:
    repo = InMemoryAffiliateRepository(seed=True)
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"{counter['n']}"

    return AffiliateLinkService(
        repo, repo, clock=lambda: FIXED_NOW, id_factory=next_id
    )


def test_generate_link_applies_template_and_tracking() -> None:
    service = _service()
    link = service.generate_link(
        product_id="prod-1",
        product_name="Phone",
        marketplace="shopee",
        country="PH",
        campaign_id="camp-1",
        sub_id="sub-1",
        click_id="clk-1",
        order_value=100.0,
        category="smartphones",
    )
    assert "DEMO_SHOPEE_AFF" in link.affiliate_url
    assert "camp-1" in link.affiliate_url or "campaign" in link.affiliate_url
    assert link.click_id == "clk-1"
    assert link.estimated_commission == 5.5
    assert link.simulated is True
    assert link.disclosure_required is True


def test_deep_link_requires_original_url() -> None:
    service = _service()
    with pytest.raises(AffiliateValidationError):
        service.generate_link(
            product_id="prod-1",
            product_name="Phone",
            marketplace="amazon",
            deep_link=True,
        )


def test_deep_link_attaches_dest() -> None:
    service = _service()
    link = service.generate_link(
        product_id="prod-1",
        product_name="Phone",
        marketplace="amazon",
        original_url="https://www.amazon.com/dp/B00DEMO",
        deep_link=True,
        campaign_id="c1",
        sub_id="s1",
        click_id="k1",
    )
    assert "dest=" in link.affiliate_url
    assert link.deep_link is True


def test_url_validation() -> None:
    builder = AffiliateLinkBuilder()
    with pytest.raises(AffiliateValidationError):
        builder.validate_url("ftp://bad.example")
    assert builder.validate_url("https://example.com/x").startswith("https://")


def test_inactive_merchant_rejected() -> None:
    service = _service()
    with pytest.raises(AffiliateValidationError):
        service.generate_link(
            product_id="prod-1",
            product_name="Item",
            merchant_id="merchant-aliexpress-global",
        )


def test_generate_for_recommendation_post_rank_helper() -> None:
    service = _service()
    rec = ShoppingRecommendation(
        product_id="prod-1",
        product_name="MacBook",
        reason="best match",
        known_price=999.0,
        currency="USD",
        marketplace="Shopee",
        deal_score=88.0,
        confidence=0.9,
    )
    link = service.generate_for_recommendation(rec, user_id="u1", country="PH")
    assert link is not None
    assert link.product_id == "prod-1"
    # DealScore on the recommendation is untouched by link generation.
    assert rec.deal_score == 88.0


def test_generate_for_recommendation_returns_none_without_marketplace() -> None:
    service = _service()
    rec = ShoppingRecommendation(
        product_id="prod-1",
        product_name="MacBook",
        reason="best match",
        known_price=999.0,
        currency="USD",
        marketplace=None,
        deal_score=88.0,
        confidence=0.9,
    )
    assert service.generate_for_recommendation(rec) is None
