"""Provider availability / health snapshots (no secrets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.interfaces.ai_review_provider import AIReviewProvider


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider: str
    model: str
    available: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
            "reason": self.reason,
        }


class ProviderHealthService:
    """Report availability of registered AI review providers."""

    def __init__(self, providers: list[AIReviewProvider]) -> None:
        self._providers = list(providers)

    def snapshot(self) -> list[ProviderHealth]:
        rows: list[ProviderHealth] = []
        for provider in self._providers:
            available = provider.is_available()
            reason = "ready" if available else "unavailable"
            if provider.provider_name != "deterministic" and not available:
                reason = "disabled_or_missing_credentials"
            rows.append(
                ProviderHealth(
                    provider=provider.provider_name,
                    model=provider.model_name,
                    available=available,
                    reason=reason,
                )
            )
        return rows

    def available_providers(self) -> list[str]:
        return [item.provider for item in self.snapshot() if item.available]
