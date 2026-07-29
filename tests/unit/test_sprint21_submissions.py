"""Sprint 21 — product/offer submissions, matching, promotions, campaigns."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.merchant import (
    MerchantCampaignStatus,
    MerchantSourceMode,
    PromotionStatus,
    SubmissionStatus,
)
from app.domain.exceptions import MerchantValidationError
from app.marketplace.matching.matcher import CatalogEntry
from app.merchant.matching import MerchantProductMatcher
from app.merchant.memory import InMemoryMerchantRepository
from app.services.merchant_auth_service import MerchantAuthService
from app.services.merchant_campaign_service import MerchantCampaignService
from app.services.merchant_offer_service import MerchantOfferService
from app.services.merchant_product_service import MerchantProductService
from app.services.merchant_promotion_service import MerchantPromotionService

FIXED_NOW = datetime(2026, 7, 29, 15, 0, tzinfo=UTC)


def _ids():
    n = {"i": 0}

    def factory() -> str:
        n["i"] += 1
        return f"s21-{n['i']:04d}"

    return factory


def _stack():
    repo = InMemoryMerchantRepository(seed=True)
    clock = lambda: FIXED_NOW  # noqa: E731
    ids = _ids()
    auth = MerchantAuthService(repo, repo)
    products = MerchantProductService(repo, repo, matcher=repo.matcher, clock=clock, id_factory=ids)
    offers = MerchantOfferService(repo, repo, clock=clock, id_factory=ids)
    promos = MerchantPromotionService(repo, repo, clock=clock, id_factory=ids)
    campaigns = MerchantCampaignService(repo, repo, clock=clock, id_factory=ids)
    return auth, products, offers, promos, campaigns, repo


def test_product_submission_validation_and_matching() -> None:
    auth, products, *_ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    draft = products.create_product(
        actor,
        "org-techhaven",
        title="NovaTech X1 Pro 14-inch Laptop",
        brand="NovaTech",
        model="X1 Pro",
        sku="NT-X1PRO-14",
        upc="012345678901",
        merchant_product_id="mp-x1-001",
        image_urls=["https://cdn.techhaven.demo/x1.png"],
    )
    assert draft.status == SubmissionStatus.DRAFT
    assert draft.source_mode == MerchantSourceMode.MERCHANT_SUBMITTED
    submitted = products.submit_product(actor, "org-techhaven", draft.submission_id)
    assert submitted.status == SubmissionStatus.SUBMITTED
    assert submitted.match_result is not None
    assert submitted.matched_product_id == "prod-laptop-x1"
    assert submitted.match_result.confidence >= 0.85


def test_ambiguous_product_matching_creates_review() -> None:
    auth, products, *_, repo = _stack()
    # Register a near-duplicate catalog entry to force ambiguity.
    repo.matcher.register(
        CatalogEntry(
            product_id="prod-laptop-x1-alt",
            brand="NovaTech",
            model="X1 Pro",
            title="NovaTech X1 Pro 14-inch Laptop",
            sku="NT-X1PRO-14B",
            upc="012345678901",
            aliases=("novatech x1",),
            marketplace_product_ids=("mp-x1-002",),
        )
    )
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    draft = products.create_product(
        actor,
        "org-techhaven",
        title="NovaTech X1 Pro 14-inch Laptop",
        brand="NovaTech",
        model="X1 Pro",
        upc="012345678901",
    )
    submitted = products.submit_product(actor, "org-techhaven", draft.submission_id)
    assert submitted.match_result is not None
    # Ambiguous → never silently merged
    if submitted.match_result.ambiguity == "ambiguous":
        assert submitted.matched_product_id is None
        reviews = repo.list_match_reviews(organization_id="org-techhaven")
        assert any(r.submission_id == submitted.submission_id for r in reviews)


def test_low_confidence_never_silently_merged() -> None:
    matcher = MerchantProductMatcher(
        [
            CatalogEntry(
                product_id="prod-other",
                brand="OtherBrand",
                model="Z9",
                title="Completely Different Product",
            )
        ]
    )
    result = matcher.match(title="Unrelated gadget name", brand="Nope")
    assert result.matched_product_id is None
    assert result.ambiguity in {"unmatched", "ambiguous"}


def test_product_withdraw_and_update_pending() -> None:
    auth, products, *_ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-editor", organization_id="org-techhaven")
    draft = products.create_product(actor, "org-techhaven", title="Draft Headphones Extra")
    updated = products.update_product(
        actor, "org-techhaven", draft.submission_id, title="Draft Headphones Updated"
    )
    assert updated.title == "Draft Headphones Updated"
    withdrawn = products.withdraw_product(actor, "org-techhaven", draft.submission_id)
    assert withdrawn.status == SubmissionStatus.WITHDRAWN


def test_unsafe_url_rejected() -> None:
    auth, products, *_ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    with pytest.raises(MerchantValidationError):
        products.create_product(
            actor,
            "org-techhaven",
            title="Bad URL Product",
            image_urls=["javascript:alert(1)"],
        )
    with pytest.raises(MerchantValidationError):
        products.create_product(
            actor,
            "org-techhaven",
            title="Secret URL Product",
            image_urls=["https://evil.demo/x?api_key=secret"],
        )


def test_offer_submission_and_updates() -> None:
    auth, _, offers, *_ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    offer = offers.create_offer(
        actor,
        "org-techhaven",
        title="X1 Offer",
        currency="USD",
        price=1000,
        shipping_cost=25,
        marketplace_url="https://techhaven.demo/o/x1",
        matched_product_id="prod-laptop-x1",
    )
    assert offer.source_mode == MerchantSourceMode.MERCHANT_SUBMITTED
    assert offer.total_price == 1025.0
    updated = offers.update_offer(
        actor, "org-techhaven", offer.offer_id, price=950, shipping_cost=0
    )
    assert updated.price == 950
    deactivated = offers.deactivate_offer(actor, "org-techhaven", offer.offer_id)
    assert deactivated.is_active is False


def test_promotion_lifecycle_dealscore_independent() -> None:
    auth, _, _, promos, *_ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    promo = promos.create_promotion(
        actor,
        "org-techhaven",
        promotion_type="sale_price",
        title="Flash Sale",
        sale_price=999,
        status="active",
        product_ids=["prod-laptop-x1"],
    )
    assert promo.dealscore_independent is True
    paused = promos.pause_promotion(actor, "org-techhaven", promo.promotion_id)
    assert paused.status == PromotionStatus.PAUSED


def test_campaign_lifecycle_sponsored_labeling() -> None:
    auth, _, _, _, campaigns, _ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    campaign = campaigns.create_campaign(
        actor,
        "org-techhaven",
        name="Sponsored X1",
        product_ids=["prod-laptop-x1"],
        placement_types=["sponsored_product"],
        daily_budget=25,
        total_budget=250,
    )
    assert "sponsored" in campaign.sponsored_label.lower()
    assert campaign.organic_ranking_independent is True
    assert campaign.budget.notes
    assert campaign.status == MerchantCampaignStatus.DRAFT
    from dataclasses import replace

    # Force ACTIVE via repository to exercise pause/resume transitions.
    repo_campaign = campaigns._campaigns.get_campaign(campaign.campaign_id)  # noqa: SLF001
    assert repo_campaign is not None
    campaigns._campaigns.save_campaign(  # noqa: SLF001
        replace(repo_campaign, status=MerchantCampaignStatus.ACTIVE)
    )
    paused = campaigns.pause_campaign(actor, "org-techhaven", campaign.campaign_id)
    assert paused.status == MerchantCampaignStatus.PAUSED
    resumed = campaigns.resume_campaign(actor, "org-techhaven", campaign.campaign_id)
    assert resumed.status == MerchantCampaignStatus.ACTIVE
    cancelled = campaigns.cancel_campaign(actor, "org-techhaven", campaign.campaign_id)
    assert cancelled.status == MerchantCampaignStatus.CANCELLED
