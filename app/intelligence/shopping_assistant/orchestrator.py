"""Multi-model shopping explanation orchestrator (economy / balanced / maximum)."""

from __future__ import annotations

from typing import Any

from app.domain.entities.shopping_assistant import MODE_RANK, AnalysisMode
from app.domain.interfaces.shopping_assistant_repository import ShoppingExplanationProvider
from app.intelligence.shopping_assistant.consensus import ShoppingConsensusService
from app.intelligence.shopping_assistant.deterministic import (
    DeterministicShoppingExplanationProvider,
)


class ShoppingExplanationRegistry:
    """Name → explanation provider lookup with deterministic always last."""

    def __init__(
        self,
        providers: list[ShoppingExplanationProvider],
        *,
        fallback_order: list[str] | None = None,
    ) -> None:
        self._providers = {provider.provider_name: provider for provider in providers}
        order = list(fallback_order or ["openai", "anthropic", "gemini", "deterministic"])
        if "deterministic" in self._providers and "deterministic" not in order:
            order = [*order, "deterministic"]
        self._order = order

    def get(self, name: str) -> ShoppingExplanationProvider | None:
        return self._providers.get(name)

    def fallback_order(self) -> list[str]:
        return list(self._order)

    def all(self) -> list[ShoppingExplanationProvider]:
        return list(self._providers.values())


class ShoppingAssistantOrchestrator:
    """Coordinate explanation providers under server-side mode restrictions."""

    def __init__(
        self,
        registry: ShoppingExplanationRegistry,
        consensus: ShoppingConsensusService | None = None,
        *,
        ai_enabled: bool = False,
        configured_mode: AnalysisMode = "economy",
        allow_client_mode: bool = True,
        primary_provider: str = "openai",
        secondary_provider: str = "anthropic",
        max_estimated_cost: float = 0.05,
    ) -> None:
        self._registry = registry
        self._consensus = consensus or ShoppingConsensusService()
        self._ai_enabled = ai_enabled
        self._configured_mode = configured_mode
        self._allow_client_mode = allow_client_mode
        self._primary = primary_provider
        self._secondary = secondary_provider
        self._max_cost = max_estimated_cost
        self._deterministic = DeterministicShoppingExplanationProvider()

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

    def explain(
        self,
        payload: dict[str, Any],
        *,
        mode: str | None = None,
    ) -> dict[str, Any]:
        resolved = self.resolve_mode(mode)
        if not self._ai_enabled:
            result = self._deterministic.explain(payload)
            return {
                **result,
                "mode": resolved,
                "providers_used": (result["provider"],),
                "fallback_used": True,
                "fallback_reason": "ai_shopping_disabled",
                "agreement_score": None,
                "disagreements": (),
            }

        if resolved == "economy":
            return self._run_economy(payload, mode=resolved)
        if resolved == "balanced":
            return self._run_balanced(payload, mode=resolved)
        return self._run_maximum(payload, mode=resolved)

    def allowed_modes(self) -> list[str]:
        if not self._ai_enabled:
            return ["economy"]
        ceiling = MODE_RANK[self._configured_mode]
        return [name for name, rank in MODE_RANK.items() if rank <= ceiling]

    def _run_economy(self, payload: dict[str, Any], *, mode: AnalysisMode) -> dict[str, Any]:
        order = [self._primary, *self._registry.fallback_order()]
        seen: set[str] = set()
        for name in order:
            if name in seen:
                continue
            seen.add(name)
            provider = self._registry.get(name) or (
                self._deterministic if name == "deterministic" else None
            )
            if provider is None:
                continue
            if name != "deterministic" and not provider.is_available():
                continue
            if self._exceeds_cost(name):
                continue
            try:
                result = provider.explain(payload)
            except Exception:
                continue
            if result.get("status") != "ok":
                continue
            fallback = name == "deterministic"
            return {
                **result,
                "mode": mode,
                "providers_used": (result.get("provider") or name,),
                "fallback_used": fallback,
                "fallback_reason": "external_provider_unavailable" if fallback else None,
                "agreement_score": None,
                "disagreements": (),
            }
        result = self._deterministic.explain(payload)
        return {
            **result,
            "mode": mode,
            "providers_used": (result["provider"],),
            "fallback_used": True,
            "fallback_reason": "all_external_providers_failed",
            "agreement_score": None,
            "disagreements": (),
        }

    def _run_balanced(self, payload: dict[str, Any], *, mode: AnalysisMode) -> dict[str, Any]:
        primary = self._safe_explain(self._primary, payload)
        secondary = self._safe_explain(self._secondary, payload)
        ok = [item for item in (primary, secondary) if item and item.get("status") == "ok"]
        if len(ok) < 2:
            economy = self._run_economy(payload, mode="economy")
            return {
                **economy,
                "mode": mode,
                "fallback_used": True,
                "fallback_reason": economy.get("fallback_reason") or "balanced_partial_failure",
            }
        merged = self._consensus.merge(ok)
        return {
            "provider": "consensus",
            "model": "balanced-consensus",
            "status": "ok",
            "answer": merged["answer"],
            "confidence": 0.8,
            "claims": ok[0].get("claims") or [],
            "mode": mode,
            "providers_used": merged["providers_used"],
            "fallback_used": False,
            "fallback_reason": None,
            "agreement_score": merged["agreement_score"],
            "disagreements": merged["disagreements"],
        }

    def _run_maximum(self, payload: dict[str, Any], *, mode: AnalysisMode) -> dict[str, Any]:
        names = ["openai", "anthropic", "gemini"]
        results: list[dict[str, Any]] = []
        for name in names:
            item = self._safe_explain(name, payload)
            if item is not None:
                results.append(item)
        ok = [item for item in results if item.get("status") == "ok"]
        if not ok:
            economy = self._run_economy(payload, mode="economy")
            return {
                **economy,
                "mode": mode,
                "fallback_used": True,
                "fallback_reason": "all_external_providers_failed",
            }
        # Always include deterministic as a grounding voice when available.
        results.append(self._deterministic.explain(payload))
        ok = [item for item in results if item.get("status") == "ok"]
        merged = self._consensus.merge(ok)
        return {
            "provider": "consensus",
            "model": "maximum-consensus",
            "status": "ok",
            "answer": merged["answer"],
            "confidence": 0.84,
            "claims": ok[0].get("claims") or [],
            "mode": mode,
            "providers_used": merged["providers_used"],
            "fallback_used": False,
            "fallback_reason": None,
            "agreement_score": merged["agreement_score"],
            "disagreements": merged["disagreements"],
        }

    def _safe_explain(self, name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        provider = self._registry.get(name)
        if provider is None or not provider.is_available() or self._exceeds_cost(name):
            return {
                "provider": name,
                "model": "",
                "status": "unavailable",
                "answer": "",
                "error_code": "unavailable",
            }
        try:
            return provider.explain(payload)
        except Exception as exc:  # noqa: BLE001 — provider boundary
            return {
                "provider": name,
                "model": provider.model_name,
                "status": "error",
                "answer": "",
                "error_code": "provider_error",
                "error": type(exc).__name__,
            }

    def _exceeds_cost(self, name: str) -> bool:
        # Deterministic is free; external providers share the server cost ceiling.
        if name == "deterministic":
            return False
        # Without live metering, treat any positive ceiling as acceptable and
        # rely on availability / disabled transport for safety.
        return self._max_cost < 0
