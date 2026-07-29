"""Multi-model community summary orchestrator (economy / balanced / maximum)."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import MODE_RANK, AnalysisMode
from app.domain.interfaces.community_intelligence_repository import CommunitySummaryProvider
from app.intelligence.community.ai_registry import CommunitySummaryRegistry
from app.intelligence.community.consensus import CommunityConsensusService
from app.intelligence.community.deterministic import DeterministicCommunitySummaryProvider


class CommunityAIOrchestrator:
    """Coordinate community summary providers under server-side mode restrictions."""

    def __init__(
        self,
        registry: CommunitySummaryRegistry,
        consensus: CommunityConsensusService | None = None,
        *,
        ai_enabled: bool = False,
        configured_mode: AnalysisMode = "economy",
        allow_client_mode: bool = True,
        primary_provider: str = "openai",
        secondary_provider: str = "anthropic",
        max_estimated_cost: float = 0.05,
    ) -> None:
        self._registry = registry
        self._consensus = consensus or CommunityConsensusService()
        self._ai_enabled = ai_enabled
        self._configured_mode = configured_mode
        self._allow_client_mode = allow_client_mode
        self._primary = primary_provider
        self._secondary = secondary_provider
        self._max_cost = max_estimated_cost
        self._deterministic = DeterministicCommunitySummaryProvider()

    def resolve_mode(self, requested: str | None) -> AnalysisMode:
        configured = self._configured_mode
        if not self._ai_enabled:
            return "economy"
        if not requested or not self._allow_client_mode:
            return configured
        cleaned = requested.strip().lower()
        if cleaned not in MODE_RANK:
            raise ValueError(f"Unsupported analysis mode: {requested}")
        if MODE_RANK[cleaned] > MODE_RANK[configured]:
            return configured
        return cleaned  # type: ignore[return-value]

    def summarize(self, payload: dict[str, Any], *, mode: str | None = None) -> dict[str, Any]:
        resolved = self.resolve_mode(mode)
        if not self._ai_enabled:
            result = self._deterministic.summarize(
                {**payload, "fallback_reason": "ai_community_disabled"}
            )
            summary = result.get("summary")
            if summary is not None:
                from app.domain.entities.community_intelligence import CommunitySummary

                if isinstance(summary, CommunitySummary):
                    summary = CommunitySummary(
                        product_id=summary.product_id,
                        product_name=summary.product_name,
                        most_praised=summary.most_praised,
                        most_complaints=summary.most_complaints,
                        common_questions=summary.common_questions,
                        who_should_buy=summary.who_should_buy,
                        who_should_avoid=summary.who_should_avoid,
                        buying_advice=summary.buying_advice,
                        limitations=summary.limitations,
                        provider=summary.provider,
                        model=summary.model,
                        mode=resolved,
                        providers_used=(summary.provider,),
                        fallback_used=True,
                        fallback_reason="ai_community_disabled",
                        agreement_score=None,
                    )
                    result = {**result, "summary": summary}
            return {
                **result,
                "mode": resolved,
                "providers_used": (result.get("provider") or "deterministic",),
                "fallback_used": True,
                "fallback_reason": "ai_community_disabled",
                "agreement_score": None,
            }

        if resolved == "economy":
            return self._run_economy(payload, mode=resolved)
        if resolved == "balanced":
            return self._run_balanced(payload, mode=resolved)
        return self._run_maximum(payload, mode=resolved)

    def allowed_modes(self) -> list[str]:
        if not self._ai_enabled:
            return ["economy"]
        rank = MODE_RANK[self._configured_mode]
        return [name for name, value in MODE_RANK.items() if value <= rank]

    def _run_economy(self, payload: dict[str, Any], *, mode: AnalysisMode) -> dict[str, Any]:
        for name in [self._primary, *self._registry.fallback_order()]:
            result = self._safe_summarize(name, payload)
            if result.get("status") == "ok":
                return {
                    **result,
                    "mode": mode,
                    "providers_used": (result.get("provider") or name,),
                    "fallback_used": name != self._primary,
                    "fallback_reason": None if name == self._primary else f"fallback_to_{name}",
                    "agreement_score": None,
                }
        result = self._deterministic.summarize(
            {**payload, "fallback_reason": "all_providers_unavailable"}
        )
        return {
            **result,
            "mode": mode,
            "providers_used": ("deterministic",),
            "fallback_used": True,
            "fallback_reason": "all_providers_unavailable",
            "agreement_score": None,
        }

    def _run_balanced(self, payload: dict[str, Any], *, mode: AnalysisMode) -> dict[str, Any]:
        results = [
            self._safe_summarize(self._primary, payload),
            self._safe_summarize(self._secondary, payload),
        ]
        ok = [item for item in results if item.get("status") == "ok"]
        if len(ok) >= 2:
            merged = self._consensus.merge(ok)
            return {**merged, "mode": mode, "fallback_used": False, "fallback_reason": None}
        return self._run_economy(payload, mode=mode)

    def _run_maximum(self, payload: dict[str, Any], *, mode: AnalysisMode) -> dict[str, Any]:
        names = ["openai", "anthropic", "gemini", "deterministic"]
        results = [self._safe_summarize(name, payload) for name in names]
        ok = [item for item in results if item.get("status") == "ok"]
        if not ok:
            return self._run_economy(payload, mode=mode)
        merged = self._consensus.merge(ok)
        return {**merged, "mode": mode, "fallback_used": False, "fallback_reason": None}

    def _safe_summarize(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self._max_cost < 0:
            return {"provider": name, "status": "unavailable", "summary": None}
        provider: CommunitySummaryProvider | None = self._registry.get(name)
        if provider is None:
            if name == "deterministic":
                return self._deterministic.summarize(payload)
            return {"provider": name, "status": "unavailable", "summary": None}
        if not provider.is_available() and name != "deterministic":
            return {"provider": name, "status": "unavailable", "summary": None}
        try:
            return provider.summarize(payload)
        except Exception:  # noqa: BLE001
            return {"provider": name, "status": "unavailable", "summary": None}
