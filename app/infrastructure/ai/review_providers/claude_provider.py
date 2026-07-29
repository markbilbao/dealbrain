"""Anthropic Claude review analysis adapter (transport-backed)."""

from __future__ import annotations

from app.infrastructure.ai.review_providers.base import TransportBackedReviewProvider
from app.infrastructure.ai.transports import DisabledTransport, ProviderTransport


class ClaudeReviewProvider(TransportBackedReviewProvider):
    """Claude adapter — isolated Anthropic-specific wiring only."""

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "claude-sonnet-4-20250514",
        transport: ProviderTransport | None = None,
        live_http_enabled: bool = False,
        ai_review_enabled: bool = False,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            transport=transport or DisabledTransport(),
            live_http_enabled=live_http_enabled,
            ai_review_enabled=ai_review_enabled,
        )

    @property
    def provider_name(self) -> str:
        return "anthropic"
