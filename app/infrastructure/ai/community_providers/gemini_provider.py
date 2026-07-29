"""Gemini community summary provider adapter."""

from __future__ import annotations

from app.infrastructure.ai.community_providers.base import TransportBackedCommunityProvider
from app.infrastructure.ai.transports import ProviderTransport


class GeminiCommunityProvider(TransportBackedCommunityProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: ProviderTransport,
        live_http_enabled: bool = False,
        ai_enabled: bool = False,
        timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(
            provider_name="gemini",
            api_key=api_key,
            model=model,
            transport=transport,
            live_http_enabled=live_http_enabled,
            ai_enabled=ai_enabled,
            timeout_seconds=timeout_seconds,
        )
