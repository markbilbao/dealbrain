"""Repeat-query stability for the existing Shopping Assistant fixture catalog."""

from __future__ import annotations

from datetime import UTC, datetime

from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.services.shopping_assistant_service import ShoppingAssistantService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
RUNS = 3
QUERIES = (
    "What is the best gaming laptop under ₱60,000?",
    "Compare iPhone 17 Pro Max and Samsung Galaxy S25 Ultra for camera and battery",
    "Which product is best for photography under ₱50,000?",
    "Is the cheapest seller trustworthy for AirPods Pro 2?",
    "Recommend a laptop for my budget and needs under ₱60,000 for gaming",
)
_UNSUPPORTED_LIVE_CLAIMS = (
    "currently available",
    "currently in stock",
    "in stock now",
    "available now",
    "live availability",
    "current availability",
    "current live price",
    "currently live",
    "live marketplace price",
)


def _service() -> ShoppingAssistantService:
    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
    )
    return ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=600),
        clock=lambda: FIXED_NOW,
    )


def _top_three(response) -> list[tuple[str, str, float | None]]:
    rows = []
    if response.top_recommendation is not None:
        top = response.top_recommendation
        rows.append((top.product_id, top.product_name, top.known_price))
    for alt in response.alternatives:
        rows.append((alt.product_id, alt.product_name, alt.known_price))
    return rows[:3]


def _evidence_sources(response) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((item.source_id, item.type) for item in response.evidence))


def _rank_ids(response) -> tuple[str, ...]:
    return tuple(item[0] for item in _top_three(response))


def _overlap(left: set[str], right: set[str]) -> float | None:
    if not left or not right:
        return None
    return len(left & right) / len(left | right)


def _unsupported_live_claims(response) -> int:
    if response.data_status == "live":
        return 0
    blob = " ".join(
        [
            response.answer,
            response.buy_now_or_wait or "",
            *(item.description for item in response.evidence),
        ]
    ).lower()
    return sum(1 for phrase in _UNSUPPORTED_LIVE_CLAIMS if phrase in blob)


def test_repeat_queries_are_stable_on_unchanged_fixture_catalog() -> None:
    metrics = {
        "top_three_overlap": [],
        "rank_changes": 0,
        "evidence_source_changes": 0,
        "product_identity_mismatches": 0,
        "known_price_mismatches": 0,
        "unsupported_current_live_claims": 0,
        "availability_accuracy": "unavailable",
    }
    for query in QUERIES:
        runs = [_service().query({"query": query}) for _ in range(RUNS)]
        first = runs[0]
        first_ids = set(_rank_ids(first))
        first_rows = _top_three(first)
        first_sources = _evidence_sources(first)
        for later in runs[1:]:
            later_ids = set(_rank_ids(later))
            overlap = _overlap(first_ids, later_ids)
            if overlap is not None:
                metrics["top_three_overlap"].append(overlap)
                assert overlap == 1.0
            assert _rank_ids(later) == _rank_ids(first)
            if _rank_ids(later) != _rank_ids(first):
                metrics["rank_changes"] += 1
            later_rows = _top_three(later)
            if later_rows != first_rows:
                if [row[0] for row in later_rows] != [row[0] for row in first_rows] or [
                    row[1] for row in later_rows
                ] != [row[1] for row in first_rows]:
                    metrics["product_identity_mismatches"] += 1
                if [row[2] for row in later_rows] != [row[2] for row in first_rows]:
                    metrics["known_price_mismatches"] += 1
            later_sources = _evidence_sources(later)
            if later_sources != first_sources:
                metrics["evidence_source_changes"] += 1
            metrics["unsupported_current_live_claims"] += _unsupported_live_claims(later)
        metrics["unsupported_current_live_claims"] += _unsupported_live_claims(first)
        assert first.data_status == "mock"
        assert not any(item.product_id is None for item in [first.top_recommendation, *first.alternatives] if item)

    assert metrics["top_three_overlap"]
    assert min(metrics["top_three_overlap"]) == 1.0
    assert metrics["rank_changes"] == 0
    assert metrics["evidence_source_changes"] == 0
    assert metrics["product_identity_mismatches"] == 0
    assert metrics["known_price_mismatches"] == 0
    assert metrics["unsupported_current_live_claims"] == 0
    assert metrics["availability_accuracy"] == "unavailable"


def test_fixture_catalog_has_no_first_class_availability_observation() -> None:
    from app.intelligence.shopping_assistant.fixtures import get_catalog

    catalog = get_catalog()
    assert catalog
    for item in catalog:
        assert "availability" not in item
        assert "in_stock" not in item
        assert item["data_status"] == "mock"
