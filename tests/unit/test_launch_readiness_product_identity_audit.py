"""Confirm existing product-identity and evidence invariants still hold."""

from __future__ import annotations

import pytest
from app.domain.entities.deal_score import ScoreableListing
from app.domain.entities.marketplace_data import MatchAmbiguityStatus
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.product_match import MatchType
from app.domain.exceptions import KnowledgeGraphValidationError
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.knowledge_graph.evidence import EvidenceValidationService
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.marketplace.matching.matcher import CatalogEntry, MarketplaceProductMatcher


def _match(title_a: str, title_b: str):
    return ExactVariantProductMatcher().match_products(
        RuleBasedProductParser().parse(title_a),
        RuleBasedProductParser().parse(title_b),
    )


def test_pro_versus_pro_max_is_a_different_product() -> None:
    result = _match("iPhone 17 Pro 256GB", "iPhone 17 Pro Max 256GB")
    assert result.is_match is False
    assert result.match_type == MatchType.DIFFERENT_PRODUCT
    assert any(conflict.field == "model" for conflict in result.conflicts)


def test_storage_conflict_is_same_product_different_variant() -> None:
    result = _match("iPhone 17 Pro Max 256GB", "iPhone 17 Pro Max 512GB")
    assert result.is_match is False
    assert result.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT
    assert any(conflict.field == "storage" for conflict in result.conflicts)


def test_color_conflict_is_different_variant() -> None:
    result = _match(
        "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "Apple IP17PM 256 WT",
    )
    assert result.is_match is False
    assert result.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT
    assert any(conflict.field == "color" for conflict in result.conflicts)


def test_ambiguous_marketplace_matches_are_held_for_review() -> None:
    matcher = MarketplaceProductMatcher(
        [
            CatalogEntry(
                product_id="a-phone",
                brand="Acme",
                model="Phone X",
                title="Acme Phone X 128GB",
                sku="APX-128",
            ),
            CatalogEntry(
                product_id="b-phone",
                brand="Acme",
                model="Phone X",
                title="Acme Phone X 256GB",
                sku="APX-256",
            ),
        ]
    )
    decision = matcher.match(brand="Acme", model="Phone X", title="Acme Phone X")
    assert decision.ambiguity == MatchAmbiguityStatus.AMBIGUOUS
    assert decision.matched_product_id is None
    low = MarketplaceProductMatcher(
        [
            CatalogEntry(
                product_id="canon-galaxy-s24-256",
                brand="Samsung",
                model="Galaxy S24",
                title="Samsung Galaxy S24 256GB",
            )
        ]
    ).match(title="galaxy")
    assert low.ambiguity in {MatchAmbiguityStatus.AMBIGUOUS, MatchAmbiguityStatus.UNMATCHED}
    assert low.matched_product_id is None


def test_unsupported_graph_claims_are_rejected() -> None:
    validator = EvidenceValidationService()
    with pytest.raises(KnowledgeGraphValidationError):
        validator.reject_unsupported_claim("some claim", supported=False)
    validator.reject_unsupported_claim("some claim", supported=True)


def test_piqscore_scores_listing_specific_attributes_without_variant_merge() -> None:
    engine = WeightedDealScoreEngine()
    listing_256 = ScoreableListing(
        listing_id="iphone-256",
        marketplace="shopee",
        title="iPhone 17 Pro Max 256GB",
        price=70_000.0,
        currency="PHP",
        seller="Official A",
        seller_rating=4.9,
        url="https://example.com/256",
        availability=AvailabilityStatus.IN_STOCK,
        shipping_cost=0.0,
        is_official_store=True,
        warranty_months=12,
        return_policy_days=14,
    )
    listing_512 = ScoreableListing(
        listing_id="iphone-512",
        marketplace="lazada",
        title="iPhone 17 Pro Max 512GB",
        price=85_000.0,
        currency="PHP",
        seller="Third Party B",
        seller_rating=2.8,
        url="https://example.com/512",
        availability=AvailabilityStatus.IN_STOCK,
        shipping_cost=199.0,
        is_official_store=False,
        warranty_months=0,
        return_policy_days=0,
    )
    result = engine.rank("iPhone 17 Pro Max", [listing_256, listing_512])
    by_id = {item.deal_score.listing_id: item.deal_score for item in result.evaluations}
    assert by_id["iphone-256"].score != by_id["iphone-512"].score
    assert by_id["iphone-256"].components.seller_score > by_id["iphone-512"].components.seller_score
    assert by_id["iphone-256"].components.price_score > by_id["iphone-512"].components.price_score
    assert by_id["iphone-512"].listing_id == "iphone-512"
    assert by_id["iphone-256"].listing_id == "iphone-256"
