"""Integration flow tests for AI Shopping Assistant (in-memory, no HTTP)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.services.shopping_assistant_service import ShoppingAssistantService


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
        clock=lambda: datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
    )


def test_end_to_end_recommendation_flow() -> None:
    service = _service()
    result = service.query(
        {
            "query": "What is the best gaming laptop under ₱60,000?",
            "mode": "economy",
        }
    )
    assert result.intent == "recommendation"
    assert result.top_recommendation is not None
    assert result.top_recommendation.known_price <= 60000
    assert result.evidence
    assert result.confidence.band in {"High", "Medium", "Low"}
    assert result.data_status == "mock"
    assert result.fallback_used is True


def test_end_to_end_comparison_and_follow_up() -> None:
    service = _service()
    first = service.query(
        {"query": ("Compare iPhone 17 Pro Max and Samsung Galaxy S25 Ultra for camera and battery")}
    )
    assert first.comparison is not None
    second = service.query(
        {
            "query": "Which one has the better battery?",
            "conversation_id": first.conversation_id,
        }
    )
    assert second.intent == "comparison"
    assert second.answer


def test_end_to_end_buy_now_or_wait() -> None:
    service = _service()
    result = service.query({"query": "Should I buy the Lenovo LOQ 15 now or wait?"})
    assert result.intent == "buy_now_or_wait"
    assert result.buy_now_or_wait
    assert "uncertain" in result.buy_now_or_wait.lower() or "guarantee" in result.answer.lower()


def test_end_to_end_complaints_and_seller_trust() -> None:
    service = _service()
    complaints = service.query({"query": "What are the main complaints about Galaxy S25 Ultra?"})
    assert complaints.intent == "complaints"
    assert "complaint" in complaints.answer.lower() or "heavy" in complaints.answer.lower()

    trust = service.query({"query": "Is the cheapest seller trustworthy for AirPods Pro 2?"})
    assert trust.intent == "seller_trust"
    assert "authenticity" in trust.answer.lower() or "trust" in trust.answer.lower()


def test_end_to_end_photography_use_case() -> None:
    service = _service()
    result = service.query(
        {
            "query": "Which product is best for photography under ₱50,000?",
            "budget_max": 50000,
            "currency": "PHP",
            "use_cases": ["photography"],
        }
    )
    assert result.top_recommendation is not None
    assert result.top_recommendation.known_price <= 50000
