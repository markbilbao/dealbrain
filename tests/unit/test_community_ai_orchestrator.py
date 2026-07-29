"""Community AI summary orchestrator / provider tests."""

from __future__ import annotations

from typing import Any

import pytest

from app.domain.entities.community_intelligence import CommunitySummary
from app.infrastructure.ai.community_providers import (
    ClaudeCommunityProvider,
    DeterministicCommunityProviderAdapter,
    GeminiCommunityProvider,
    OpenAICommunityProvider,
)
from app.infrastructure.ai.transports import DisabledTransport, ScriptedTransport
from app.intelligence.community.ai_orchestrator import CommunityAIOrchestrator
from app.intelligence.community.ai_registry import CommunitySummaryRegistry
from app.intelligence.community.deterministic import DeterministicCommunitySummaryProvider
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID, DEMO_PRODUCT_LABEL
from app.intelligence.community.orchestrator import CommunityOrchestrator
from app.core.dependencies import get_community_registry


class _ScriptedSummary:
    def __init__(self, name: str, ok: bool = True) -> None:
        self.provider_name = name
        self.model_name = f"{name}-model"
        self._ok = ok

    def is_available(self) -> bool:
        return self._ok

    def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._ok:
            return {"provider": self.provider_name, "status": "unavailable", "summary": None}
        summary = DeterministicCommunitySummaryProvider().summarize(payload)["summary"]
        assert isinstance(summary, CommunitySummary)
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "status": "ok",
            "summary": summary,
        }


def _payload() -> dict[str, Any]:
    orch = CommunityOrchestrator(get_community_registry())
    product = orch.analyze_product(DEMO_PRODUCT_ID)
    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "evidence": list(product.evidence),
        "topics": list(product.topics),
        "evidence_dicts": [item.to_dict() for item in product.evidence],
        "topic_dicts": [item.to_dict() for item in product.topics],
    }


def test_deterministic_always_available():
    provider = DeterministicCommunitySummaryProvider()
    assert provider.is_available()
    result = provider.summarize(
        {
            "product_id": DEMO_PRODUCT_ID,
            "product_name": DEMO_PRODUCT_LABEL,
            "evidence": [],
            "topics": [],
        }
    )
    assert result["status"] == "ok"
    assert isinstance(result["summary"], CommunitySummary)


def test_ai_disabled_uses_deterministic():
    registry = CommunitySummaryRegistry(
        [_ScriptedSummary("openai"), DeterministicCommunityProviderAdapter()]
    )
    orch = CommunityAIOrchestrator(registry, ai_enabled=False)
    result = orch.summarize(_payload(), mode="maximum")
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "ai_community_disabled"
    assert "deterministic" in result["providers_used"]


def test_economy_primary_then_fallback():
    registry = CommunitySummaryRegistry(
        [
            _ScriptedSummary("openai", ok=False),
            _ScriptedSummary("anthropic", ok=True),
            DeterministicCommunityProviderAdapter(),
        ],
        fallback_order=["openai", "anthropic", "deterministic"],
    )
    orch = CommunityAIOrchestrator(
        registry,
        ai_enabled=True,
        configured_mode="economy",
        primary_provider="openai",
    )
    result = orch.summarize(_payload(), mode="economy")
    assert result["status"] == "ok"
    assert result["fallback_used"] is True


def test_balanced_consensus():
    registry = CommunitySummaryRegistry(
        [
            _ScriptedSummary("openai"),
            _ScriptedSummary("anthropic"),
            DeterministicCommunityProviderAdapter(),
        ]
    )
    orch = CommunityAIOrchestrator(
        registry,
        ai_enabled=True,
        configured_mode="balanced",
        primary_provider="openai",
        secondary_provider="anthropic",
    )
    result = orch.summarize(_payload(), mode="balanced")
    assert result["status"] == "ok"
    assert result.get("agreement_score") is not None or result.get("provider")


def test_mode_ceiling():
    registry = CommunitySummaryRegistry([DeterministicCommunityProviderAdapter()])
    orch = CommunityAIOrchestrator(
        registry,
        ai_enabled=True,
        configured_mode="economy",
        allow_client_mode=True,
    )
    assert orch.resolve_mode("maximum") == "economy"
    assert orch.allowed_modes() == ["economy"]


def test_transport_providers_unavailable_without_keys():
    transport = DisabledTransport()
    for cls in (OpenAICommunityProvider, ClaudeCommunityProvider, GeminiCommunityProvider):
        provider = cls(
            api_key="",
            model="x",
            transport=transport,
            live_http_enabled=True,
            ai_enabled=True,
        )
        assert provider.is_available() is False
        result = provider.summarize(_payload())
        assert result["status"] == "unavailable"


def test_transport_provider_parses_scripted_json():
    content = (
        '{"most_praised":[{"statement":"Battery praised","evidence_ids":["reddit:r_tuf_battery_1"]}],'
        '"most_complaints":[],"common_questions":[],"who_should_buy":[],'
        '"who_should_avoid":[],"buying_advice":[],"limitations":["mock"],"confidence":0.7}'
    )
    transport = ScriptedTransport(content=content)
    provider = OpenAICommunityProvider(
        api_key="test",
        model="gpt",
        transport=transport,
        live_http_enabled=True,
        ai_enabled=True,
    )
    result = provider.summarize(_payload())
    assert result["status"] == "ok"
    assert result["summary"].most_praised


@pytest.mark.parametrize("mode", ["economy", "balanced", "maximum"])
def test_invalid_mode_raises(mode):
    registry = CommunitySummaryRegistry([DeterministicCommunityProviderAdapter()])
    orch = CommunityAIOrchestrator(
        registry,
        ai_enabled=True,
        configured_mode="maximum",
        allow_client_mode=True,
    )
    with pytest.raises(ValueError):
        orch.resolve_mode("nope")
    assert orch.resolve_mode(mode) == mode
