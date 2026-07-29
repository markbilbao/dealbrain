"""OpenAI review analysis adapter (transport-backed; HTTP off by default)."""

from __future__ import annotations

from app.infrastructure.ai.review_providers.base import TransportBackedReviewProvider
from app.infrastructure.ai.transports import DisabledTransport, ProviderTransport


class OpenAIReviewProvider(TransportBackedReviewProvider):
    """OpenAI adapter — no SDK required; uses ProviderTransport boundary."""

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "gpt-4o-mini",
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
        return "openai"
