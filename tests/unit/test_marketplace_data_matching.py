"""Unit tests for Sprint 18 marketplace product matching."""

from __future__ import annotations

from app.domain.entities.marketplace_data import MatchAmbiguityStatus
from app.marketplace.matching.matcher import CatalogEntry, MarketplaceProductMatcher


def catalog() -> MarketplaceProductMatcher:
    matcher = MarketplaceProductMatcher()
    matcher.register(
        CatalogEntry(
            product_id="canon-iphone-15-pro-256",
            brand="Apple",
            model="iPhone 15 Pro",
            title="Apple iPhone 15 Pro 256GB",
            sku="IP15PRO-256",
            upc="194253431413",
            aliases=("iphone 15 pro 256",),
        )
    )
    matcher.register(
        CatalogEntry(
            product_id="canon-galaxy-s24-256",
            brand="Samsung",
            model="Galaxy S24",
            title="Samsung Galaxy S24 256GB",
            sku="SGS24-256",
            upc="887276798012",
        )
    )
    return matcher


def test_exact_upc_match() -> None:
    decision = catalog().match(
        title="Something",
        upc="194253431413",
    )
    assert decision.ambiguity == MatchAmbiguityStatus.MATCHED
    assert decision.matched_product_id == "canon-iphone-15-pro-256"
    assert decision.confidence >= 0.85


def test_brand_model_match() -> None:
    decision = catalog().match(
        brand="Apple",
        model="iPhone 15 Pro",
        title="Apple iPhone 15 Pro 256GB Natural Titanium",
    )
    assert decision.ambiguity == MatchAmbiguityStatus.MATCHED
    assert decision.matched_product_id == "canon-iphone-15-pro-256"


def test_unmatched_product() -> None:
    decision = catalog().match(title="Unknown Gadget XYZ", brand="NoBrand")
    assert decision.ambiguity == MatchAmbiguityStatus.UNMATCHED
    assert decision.matched_product_id is None


def test_ambiguous_near_candidates() -> None:
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
    assert len(decision.candidate_ids) >= 2


def test_low_confidence_stays_ambiguous_or_unmatched() -> None:
    decision = catalog().match(title="galaxy")
    assert decision.ambiguity in {
        MatchAmbiguityStatus.AMBIGUOUS,
        MatchAmbiguityStatus.UNMATCHED,
    }
    assert decision.matched_product_id is None
