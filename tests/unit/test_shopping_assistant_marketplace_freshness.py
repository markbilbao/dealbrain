"""Fail-closed marketplace freshness provenance for shopping ranking."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.shopping_assistant import ShoppingCandidate
from app.intelligence.shopping_assistant.candidates import ProductCandidateService
from app.intelligence.shopping_assistant.intent import ShoppingIntentService
from app.intelligence.shopping_assistant.recommendation import ShoppingRecommendationRanker
from app.services.shopping_assistant_service import (
    ShoppingAssistantService,
    _authoritative_marketplace_enrichment,
    _normalize_identity_title,
    _resolve_marketplace_enrichment_status,
)

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
GAMING_QUERY = "What is the best gaming laptop under ₱60,000?"
TUF_NAME = "ASUS TUF Gaming A15 Ryzen 7 RTX 4050"
LOQ_NAME = "Lenovo LOQ 15 RTX 4060"
AIRPODS_NAME = "Apple AirPods Pro 2 USB-C"
GENERIC_AIRPODS_TITLE = "Apple AirPods Pro 2"
IPHONE_128_NAME = "Apple iPhone 16 Pro 128GB White Titanium"
IPHONE_512_TITLE = "Apple iPhone 16 Pro 512GB White Titanium"


class _StaticEnrichment:
    def __init__(self, items: list[dict]) -> None:
        self._items = items

    def shopping_enrichment(self, product_name: str | None = None) -> list[dict]:
        del product_name
        return list(self._items)


def _enrichment(
    title: str,
    *,
    data_status: str,
    is_current_live_price: bool,
    freshness_warning: str | None = None,
    product_id: str | None = None,
) -> dict:
    payload = {
        "title": title,
        "data_status": data_status,
        "is_current_live_price": is_current_live_price,
        "freshness_warning": freshness_warning,
        "notes": ["Marketplace provenance note for tests."],
        "total_price": 1.0,
    }
    if product_id is not None:
        payload["product_id"] = product_id
    return payload


def _assistant(items: list[dict] | None) -> ShoppingAssistantService:
    return ShoppingAssistantService(
        marketplace_data_service=_StaticEnrichment(items) if items is not None else None,
        clock=lambda: FIXED_NOW,
    )


def _candidates(query: str = GAMING_QUERY) -> list[ShoppingCandidate]:
    intent = ShoppingIntentService().parse(query)
    return ProductCandidateService().find_candidates(intent)


def test_stale_live_does_not_promote_or_boost() -> None:
    status, boost = _resolve_marketplace_enrichment_status(
        "mock",
        {"data_status": "live", "is_current_live_price": False},
    )
    assert status == "mock"
    assert boost == 0.0


def test_fresh_current_live_keeps_existing_boost() -> None:
    status, boost = _resolve_marketplace_enrichment_status(
        "mock",
        {"data_status": "live", "is_current_live_price": True},
    )
    assert status == "live"
    assert boost == 0.15


def test_imported_does_not_downgrade_live() -> None:
    status, boost = _resolve_marketplace_enrichment_status(
        "live",
        {"data_status": "imported", "is_current_live_price": False},
    )
    assert status == "live"
    assert boost == 0.0


def test_imported_still_promotes_mock() -> None:
    status, boost = _resolve_marketplace_enrichment_status(
        "mock",
        {"data_status": "imported", "is_current_live_price": False},
    )
    assert status == "imported"
    assert boost == 0.03


def test_stale_live_enrichment_does_not_convert_mock_response_to_live() -> None:
    assistant = _assistant(
        [
            _enrichment(
                TUF_NAME,
                data_status="live",
                is_current_live_price=False,
                freshness_warning="Price/inventory data is stale",
            )
        ]
    )
    baseline = _assistant(None).query({"query": GAMING_QUERY})
    response = assistant.query({"query": GAMING_QUERY})
    tuf = next(item for item in _apply(assistant) if item.product_name == TUF_NAME)
    assert tuf.data_status == "mock"
    assert response.data_status == "mock"
    assert baseline.data_status == "mock"
    assert any(item.code == "marketplace_data_freshness" for item in response.warnings)
    assert any("stale" in item.message.lower() for item in response.warnings)
    assert any(item.code == "non_live_price_claim" for item in response.warnings)
    assert tuf.known_price == next(
        item.known_price for item in _candidates() if item.product_name == TUF_NAME
    )


def test_stale_live_gets_no_ranking_authority_boost() -> None:
    stale = _assistant(
        [
            _enrichment(
                TUF_NAME,
                data_status="live",
                is_current_live_price=False,
                freshness_warning="Price/inventory data is stale",
            )
        ]
    )
    none = _assistant(None)
    stale_ranked = _rank(stale)
    baseline_ranked = _rank(none)
    assert [item.product_id for item in stale_ranked] == [
        item.product_id for item in baseline_ranked
    ]
    stale_tuf = next(item for item in _apply(stale) if item.product_name == TUF_NAME)
    baseline_tuf = next(item for item in _apply(none) if item.product_name == TUF_NAME)
    assert stale_tuf.match_score == baseline_tuf.match_score
    assert stale.query({"query": GAMING_QUERY}).top_recommendation.product_name == LOQ_NAME


def test_fresh_current_live_receives_normal_treatment() -> None:
    fresh = _assistant(
        [
            _enrichment(
                TUF_NAME,
                data_status="live",
                is_current_live_price=True,
            )
        ]
    )
    none = _assistant(None)
    fresh_tuf = next(item for item in _apply(fresh) if item.product_name == TUF_NAME)
    baseline_tuf = next(item for item in _apply(none) if item.product_name == TUF_NAME)
    assert fresh_tuf.data_status == "live"
    assert fresh_tuf.match_score == baseline_tuf.match_score + 0.15
    response = fresh.query({"query": GAMING_QUERY})
    assert response.data_status == "live"
    assert response.top_recommendation is not None
    assert response.top_recommendation.product_name == TUF_NAME
    assert not any(item.code == "marketplace_data_freshness" for item in response.warnings)
    assert not any(item.code == "non_live_price_claim" for item in response.warnings)
    assert fresh_tuf.known_price == baseline_tuf.known_price


def _candidate_named(name: str) -> ShoppingCandidate:
    intent = ShoppingIntentService().parse(name, overrides={"products": [name]})
    found = ProductCandidateService().find_candidates(intent)
    match = next(item for item in found if item.product_name == name)
    return match


def _apply_named(assistant: ShoppingAssistantService, name: str) -> ShoppingCandidate:
    updated, _warnings = assistant._apply_marketplace_data_provenance([_candidate_named(name)])
    return updated[0]


def test_normalized_title_equality_is_not_substring() -> None:
    assert _normalize_identity_title("  Apple AirPods Pro 2 USB-C  ") == (
        "apple airpods pro 2 usb-c"
    )
    candidate = _candidate_named(AIRPODS_NAME)
    generic = _enrichment(
        GENERIC_AIRPODS_TITLE,
        data_status="live",
        is_current_live_price=True,
    )
    assert _authoritative_marketplace_enrichment(candidate, [generic]) is None


def test_exact_title_fresh_live_enrichment_is_authoritative() -> None:
    exact = _assistant(
        [
            _enrichment(
                f"  {AIRPODS_NAME}  ",
                data_status="live",
                is_current_live_price=True,
            )
        ]
    )
    none = _assistant(None)
    enriched = _apply_named(exact, AIRPODS_NAME)
    baseline = _apply_named(none, AIRPODS_NAME)
    assert enriched.data_status == "live"
    assert enriched.match_score == baseline.match_score + 0.15
    assert enriched.known_price == baseline.known_price


def test_exact_product_id_fresh_live_is_authoritative() -> None:
    candidate = _candidate_named(AIRPODS_NAME)
    assistant = _assistant(
        [
            _enrichment(
                "Unrelated marketplace listing title",
                data_status="live",
                is_current_live_price=True,
                product_id=candidate.product_id,
            )
        ]
    )
    none = _assistant(None)
    enriched = _apply_named(assistant, AIRPODS_NAME)
    baseline = _apply_named(none, AIRPODS_NAME)
    assert enriched.data_status == "live"
    assert enriched.match_score == baseline.match_score + 0.15
    assert enriched.known_price == baseline.known_price


def test_generic_substring_title_does_not_grant_live_authority() -> None:
    generic = _assistant(
        [
            _enrichment(
                GENERIC_AIRPODS_TITLE,
                data_status="live",
                is_current_live_price=True,
            )
        ]
    )
    none = _assistant(None)
    enriched = _apply_named(generic, AIRPODS_NAME)
    baseline = _apply_named(none, AIRPODS_NAME)
    assert enriched.data_status == "mock"
    assert enriched.match_score == baseline.match_score
    assert enriched.known_price == baseline.known_price
    response = generic.query({"query": "Is the cheapest seller trustworthy for AirPods Pro 2?"})
    assert response.data_status == "mock"
    top = response.top_recommendation
    assert top is None or top.product_name != AIRPODS_NAME or response.data_status != "live"


def test_different_storage_variant_does_not_grant_live_authority() -> None:
    wrong_variant = _assistant(
        [
            _enrichment(
                IPHONE_512_TITLE,
                data_status="live",
                is_current_live_price=True,
            )
        ]
    )
    none = _assistant(None)
    enriched = _apply_named(wrong_variant, IPHONE_128_NAME)
    baseline = _apply_named(none, IPHONE_128_NAME)
    assert enriched.data_status == "mock"
    assert enriched.match_score == baseline.match_score
    assert enriched.known_price == baseline.known_price


def test_stale_and_current_warnings_remain_correct() -> None:
    mixed = _assistant(
        [
            _enrichment(
                TUF_NAME,
                data_status="live",
                is_current_live_price=False,
                freshness_warning="Price/inventory data is stale",
            ),
            _enrichment(
                LOQ_NAME,
                data_status="live",
                is_current_live_price=True,
            ),
        ]
    )
    updated, warnings = mixed._apply_marketplace_data_provenance(_candidates())
    by_name = {item.product_name: item for item in updated}
    assert by_name[TUF_NAME].data_status == "mock"
    assert by_name[LOQ_NAME].data_status == "live"
    assert any("stale" in item.message.lower() for item in warnings)
    assert any(item.code == "non_live_price_claim" for item in warnings)
    response = mixed.query({"query": GAMING_QUERY})
    assert response.data_status == "live"
    assert any(item.code == "marketplace_data_freshness" for item in response.warnings)


def _apply(assistant: ShoppingAssistantService) -> list[ShoppingCandidate]:
    updated, _warnings = assistant._apply_marketplace_data_provenance(_candidates())
    return updated


def _rank(assistant: ShoppingAssistantService):
    intent = ShoppingIntentService().parse(GAMING_QUERY)
    candidates = _apply(assistant)
    return ShoppingRecommendationRanker().rank(candidates, [], intent)
