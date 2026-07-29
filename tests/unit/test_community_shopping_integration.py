"""Shopping Assistant ↔ Community Intelligence integration."""

from __future__ import annotations

import pytest

from app.core.dependencies import (
    get_community_ai_orchestrator,
    get_community_registry,
    get_community_summary_registry,
)
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID
from app.intelligence.community.orchestrator import CommunityOrchestrator
from app.services.community_intelligence_service import CommunityIntelligenceService
from app.services.shopping_assistant_service import ShoppingAssistantService


def _community() -> CommunityIntelligenceService:
    return CommunityIntelligenceService(
        CommunityOrchestrator(
            get_community_registry(),
            ai_orchestrator=get_community_ai_orchestrator(get_community_summary_registry()),
        )
    )


def test_shopping_includes_community_evidence():
    sa = ShoppingAssistantService(community_service=_community())
    response = sa.query({"query": "Is the ASUS TUF A15 good for gaming under 60000?"})
    community = [item for item in response.evidence if item.type == "community"]
    assert community
    assert all(item.source_id == "community_intelligence" for item in community)
    assert response.processing.get("community_integrated") is True


def test_shopping_without_community_still_works():
    sa = ShoppingAssistantService(community_service=None)
    response = sa.demo()
    assert response.answer
    assert response.processing.get("community_integrated") is False
    assert not any(item.type == "community" for item in response.evidence)


def test_community_evidence_is_provider_neutral():
    """Shopping assistant evidence descriptions must not require connector-specific parsing."""
    sa = ShoppingAssistantService(community_service=_community())
    response = sa.query({"query": f"Tell me about product {DEMO_PRODUCT_ID}"})
    community = [item for item in response.evidence if item.type == "community"]
    for item in community:
        assert item.source_id == "community_intelligence"
        assert "Community" in item.description


@pytest.mark.parametrize(
    "query",
    [
        "Best gaming laptop under 60000",
        "ASUS TUF A15 battery complaints",
        "Compare TUF and Nitro for heat",
        "Should I buy Lenovo LOQ now or wait",
    ],
)
def test_shopping_queries_stay_stable_with_community(query):
    sa = ShoppingAssistantService(community_service=_community())
    response = sa.query({"query": query})
    assert response.confidence.band in {"High", "Medium", "Low"}
    assert response.data_status in {"mock", "imported", "live"}
