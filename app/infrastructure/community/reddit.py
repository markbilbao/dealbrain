"""Reddit connector — API-backed transport abstraction with fixture fallback.

Does not hardcode scraping. Live access requires an enabled connector and a
non-disabled transport. Default DI uses fixtures via MockCommunityTransport.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.entities.community_intelligence import CommunityEvidence
from app.domain.interfaces.community_intelligence_repository import CommunityTransport
from app.infrastructure.community.base import BaseCommunityProvider
from app.infrastructure.community.transports import DisabledCommunityTransport, MockCommunityTransport
from app.intelligence.community.fixtures import REDDIT_FIXTURES, get_product_meta
from app.intelligence.community.normalizer import EvidenceNormalizer
from app.intelligence.community.validator import EvidenceValidator


class RedditCommunityProvider(BaseCommunityProvider):
    """Full Reddit connector with product / thread / comment extraction."""

    source = "reddit"  # type: ignore[assignment]

    def __init__(
        self,
        *,
        enabled: bool = True,
        transport: CommunityTransport | None = None,
        use_fixtures_when_unavailable: bool = True,
        normalizer: EvidenceNormalizer | None = None,
        validator: EvidenceValidator | None = None,
        client_id: str = "",
        client_secret: str = "",
        user_agent: str = "DealBrainCommunityBot/1.0",
    ) -> None:
        # Never store secrets for API responses — keep only for transport auth shape.
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_agent = user_agent
        if transport is None:
            transport = MockCommunityTransport() if (enabled or use_fixtures_when_unavailable) else DisabledCommunityTransport()
        super().__init__(
            enabled=enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures_when_unavailable,
            normalizer=normalizer,
            validator=validator,
        )

    def is_available(self) -> bool:
        if self._use_fixtures:
            return True
        return self._enabled and not isinstance(self._transport, DisabledCommunityTransport)

    def search_product(self, product_id: str, *, product_label: str | None = None) -> list[dict[str, Any]]:
        return self._load_threads(product_id, product_label=product_label)

    def search_threads(self, product_id: str, *, query: str | None = None) -> list[dict[str, Any]]:
        threads = self._load_threads(product_id)
        if not query:
            return threads
        needle = query.lower()
        return [
            thread
            for thread in threads
            if needle in str(thread.get("title", "")).lower()
            or needle in str(thread.get("body", "")).lower()
            or needle in str(thread.get("subreddit", "")).lower()
        ]

    def extract_comments(self, thread_id: str) -> list[dict[str, Any]]:
        for threads in REDDIT_FIXTURES.values():
            for thread in threads:
                if thread.get("thread_id") == thread_id:
                    return list(thread.get("comments") or [])
        # API-shaped path for future live transport.
        try:
            payload = self._transport.fetch(f"/reddit/comments/{thread_id}")
            return list(payload.get("items") or payload.get("comments") or [])
        except Exception:  # noqa: BLE001
            return []

    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[CommunityEvidence]:
        meta = get_product_meta(product_id, product_label)
        threads = self._load_threads(product_id, product_label=product_label)
        evidence: list[CommunityEvidence] = []
        for thread in threads:
            thread_raw = {
                **thread,
                "evidence_id": f"reddit:{thread.get('thread_id')}",
                "permalink": thread.get("permalink") or thread.get("url"),
            }
            evidence.append(
                self._normalizer.normalize(
                    thread_raw,
                    source="reddit",
                    product_id=meta["product_id"],
                    product_name=meta["product_name"],
                )
            )
            for comment in thread.get("comments") or []:
                comment_raw = {
                    "title": f"Comment on: {thread.get('title', '')}",
                    "body": comment.get("body", ""),
                    "author": comment.get("author"),
                    "upvotes": comment.get("upvotes", 0),
                    "comment_count": 0,
                    "thread_id": thread.get("thread_id"),
                    "permalink": thread.get("permalink"),
                    "url": thread.get("url"),
                    "created_utc": comment.get("created_utc"),
                    "evidence_id": f"reddit:{comment.get('comment_id')}",
                    "subreddit": thread.get("subreddit"),
                }
                evidence.append(
                    self._normalizer.normalize(
                        comment_raw,
                        source="reddit",
                        product_id=meta["product_id"],
                        product_name=meta["product_name"],
                    )
                )
        return self._validator.validate_many(evidence)

    def thread_metadata(self, thread_id: str) -> dict[str, Any]:
        for threads in REDDIT_FIXTURES.values():
            for thread in threads:
                if thread.get("thread_id") == thread_id:
                    created = thread.get("created_utc")
                    age_hours = None
                    if created is not None:
                        age_hours = round(
                            (datetime.now(UTC).timestamp() - float(created)) / 3600.0,
                            2,
                        )
                    return {
                        "thread_id": thread_id,
                        "title": thread.get("title"),
                        "subreddit": thread.get("subreddit"),
                        "author": thread.get("author"),
                        "upvotes": thread.get("upvotes", 0),
                        "comment_count": thread.get("comment_count", 0),
                        "age_hours": age_hours,
                        "permalink": thread.get("permalink"),
                        "url": thread.get("url"),
                    }
        return {"thread_id": thread_id}

    def _load_threads(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[dict[str, Any]]:
        meta = get_product_meta(product_id, product_label)
        pid = meta["product_id"]
        # Prefer transport when enabled; fall back to fixtures.
        if self._enabled and not isinstance(self._transport, DisabledCommunityTransport):
            try:
                payload = self._transport.fetch(
                    "/reddit/search",
                    params={"product_id": pid, "q": meta["product_name"]},
                )
                items = list(payload.get("items") or payload.get("threads") or [])
                if items:
                    return items
            except Exception:  # noqa: BLE001
                if not self._use_fixtures:
                    return []
        if not self._use_fixtures:
            return []
        return list(REDDIT_FIXTURES.get(pid, []))

    def _raw_for_product(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._load_threads(product_id, product_label=product_label)

    def _fixture_map(self) -> dict[str, list[dict[str, Any]]]:
        return REDDIT_FIXTURES
