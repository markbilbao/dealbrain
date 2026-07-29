"""YouTube community adapter — mock transport only (provider-ready)."""

from __future__ import annotations

from typing import Any

from app.domain.interfaces.community_intelligence_repository import CommunityTransport
from app.infrastructure.community.base import BaseCommunityProvider
from app.intelligence.community.fixtures import YOUTUBE_FIXTURES, get_product_meta
from app.intelligence.community.normalizer import EvidenceNormalizer
from app.intelligence.community.validator import EvidenceValidator


class YouTubeCommunityProvider(BaseCommunityProvider):
    """Future-ready YouTube adapter for video metadata / transcripts / engagement."""

    source = "youtube"  # type: ignore[assignment]

    def __init__(
        self,
        *,
        enabled: bool = False,
        transport: CommunityTransport | None = None,
        use_fixtures_when_unavailable: bool = True,
        normalizer: EvidenceNormalizer | None = None,
        validator: EvidenceValidator | None = None,
    ) -> None:
        super().__init__(
            enabled=enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures_when_unavailable,
            normalizer=normalizer,
            validator=validator,
        )

    def _raw_for_product(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._enabled and not self._use_fixtures:
            return []
        meta = get_product_meta(product_id, product_label)
        videos = list(YOUTUBE_FIXTURES.get(meta["product_id"], []))
        return [
            {
                **video,
                "title": video.get("title"),
                "body": video.get("transcript_excerpt") or video.get("summary") or "",
                "creator": video.get("creator"),
                "likes": video.get("likes", 0),
                "views": video.get("views", 0),
                "publish_date": video.get("publish_date"),
                "summary": video.get("summary"),
                "url": video.get("url"),
                "evidence_id": f"youtube:{video.get('video_id')}",
            }
            for video in videos
        ]

    def _fixture_map(self) -> dict[str, list[dict[str, Any]]]:
        return YOUTUBE_FIXTURES
