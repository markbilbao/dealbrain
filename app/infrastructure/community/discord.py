"""Discord community adapter — architecture only, disabled by default."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import CommunityEvidence
from app.domain.interfaces.community_intelligence_repository import CommunityTransport
from app.infrastructure.community.base import BaseCommunityProvider
from app.infrastructure.community.transports import DisabledCommunityTransport
from app.intelligence.community.fixtures import DISCORD_FIXTURES, get_product_meta


class DiscordCommunityProvider(BaseCommunityProvider):
    """Provider-ready Discord adapter. Disabled unless explicitly configured."""

    source = "discord"  # type: ignore[assignment]

    def __init__(
        self,
        *,
        enabled: bool = False,
        transport: CommunityTransport | None = None,
        use_fixtures_when_unavailable: bool = False,
        **kwargs: Any,
    ) -> None:
        # Architecture only: default to disabled + no fixture leakage in production DI.
        super().__init__(
            enabled=enabled,
            transport=transport or DisabledCommunityTransport(),
            use_fixtures_when_unavailable=use_fixtures_when_unavailable,
            **kwargs,
        )

    def is_available(self) -> bool:
        return bool(self._enabled)

    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[CommunityEvidence]:
        if not self._enabled:
            return []
        return super().collect(product_id, product_label=product_label)

    def _raw_for_product(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._enabled:
            return []
        if not self._use_fixtures:
            return []
        meta = get_product_meta(product_id, product_label)
        items = list(DISCORD_FIXTURES.get(meta["product_id"], []))
        return [
            {
                **item,
                "title": f"Discord #{item.get('channel')}",
                "body": item.get("body"),
                "author": item.get("author"),
                "created_at": item.get("created_at"),
                "url": item.get("url"),
                "evidence_id": f"discord:{item.get('message_id')}",
            }
            for item in items
        ]

    def _fixture_map(self) -> dict[str, list[dict[str, Any]]]:
        return DISCORD_FIXTURES
