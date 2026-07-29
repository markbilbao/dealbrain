"""Sprint 20 — Shopping Assistant post-rank affiliate integration.

Affiliate links are attached AFTER recommendation selection. DealScore and
ranking order must remain commission-independent.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.affiliate.memory import InMemoryAffiliateRepository
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.services.affiliate_link_service import AffiliateLinkService
from app.services.shopping_assistant_service import ShoppingAssistantService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _assistant(with_affiliate: bool = True) -> ShoppingAssistantService:
    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
        allow_client_mode=True,
        primary_provider="openai",
        secondary_provider="anthropic",
    )
    affiliate = None
    if with_affiliate:
        repo = InMemoryAffiliateRepository(seed=True)
        affiliate = AffiliateLinkService(
            repo, repo, clock=lambda: FIXED_NOW, id_factory=lambda: "sa-aff"
        )
    return ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=60),
        affiliate_link_service=affiliate,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "sa-1",
    )


def test_affiliate_attached_after_recommendation() -> None:
    assistant = _assistant(with_affiliate=True)
    response = assistant.query({"query": "best gaming laptop under 60000"})
    assert response.top_recommendation is not None
    affiliate = response.processing.get("affiliate")
    assert affiliate is not None
    assert affiliate["applied_after_ranking"] is True
    assert affiliate["dealscore_independent"] is True
    # Top link may or may not resolve depending on marketplace match; payload exists either way.
    assert "top_link" in affiliate
    assert "disclaimer" in affiliate


def test_without_affiliate_collaborator_processing_flag_false() -> None:
    assistant = _assistant(with_affiliate=False)
    response = assistant.query({"query": "best gaming laptop under 60000"})
    assert response.processing.get("affiliate_integrated") is False
    assert "affiliate" not in response.processing


def test_affiliate_does_not_change_dealscore_on_recommendation() -> None:
    with_aff = _assistant(with_affiliate=True).query({"query": "best wireless earbuds"})
    without = _assistant(with_affiliate=False).query({"query": "best wireless earbuds"})
    assert with_aff.top_recommendation is not None
    assert without.top_recommendation is not None
    assert with_aff.top_recommendation.product_id == without.top_recommendation.product_id
    assert with_aff.top_recommendation.deal_score == without.top_recommendation.deal_score
