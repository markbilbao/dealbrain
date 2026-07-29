"""Normalize connector payloads into the common CommunityEvidence model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.entities.community_intelligence import (
    CommunityEngagement,
    CommunityEvidence,
    CommunitySource,
)
from app.intelligence.community.sentiment import analyze_sentiment
from app.intelligence.community.topics import TopicExtractor


class EvidenceNormalizer:
    """Map heterogeneous connector payloads to CommunityEvidence."""

    def __init__(self, topic_extractor: TopicExtractor | None = None) -> None:
        self._topics = topic_extractor or TopicExtractor()

    def normalize(
        self,
        raw: dict[str, Any],
        *,
        source: CommunitySource,
        product_id: str,
        product_name: str,
        evidence_id: str | None = None,
    ) -> CommunityEvidence:
        title = str(raw.get("title") or raw.get("question") or "").strip()
        body = str(
            raw.get("body")
            or raw.get("answer")
            or raw.get("discussion")
            or raw.get("summary")
            or raw.get("transcript_excerpt")
            or raw.get("seller_response")
            or ""
        ).strip()
        combined = f"{title}\n{body}".strip()
        topic = str(raw.get("topic") or self._topics.primary_topic(combined))
        sentiment = raw.get("sentiment")
        if isinstance(sentiment, dict):
            from app.domain.entities.community_intelligence import CommunitySentiment

            sentiment_obj = CommunitySentiment(
                label=sentiment.get("label", "neutral"),  # type: ignore[arg-type]
                score=float(sentiment.get("score") or 0.0),
            )
        else:
            sentiment_obj = analyze_sentiment(combined)

        engagement = self._engagement(raw, source)
        timestamp = self._timestamp(raw)
        eid = evidence_id or str(
            raw.get("evidence_id")
            or raw.get("thread_id")
            or raw.get("video_id")
            or raw.get("qa_id")
            or raw.get("question_id")
            or raw.get("message_id")
            or f"{source}:{abs(hash(combined)) % 10_000_000}"
        )
        url = str(raw.get("url") or raw.get("permalink") or "")
        confidence = float(raw.get("confidence") or self._confidence(engagement, body))
        return CommunityEvidence(
            source=source,
            product=product_name,
            product_id=product_id,
            evidence_id=eid,
            url=url,
            title=title or topic,
            body=body,
            topic=topic,
            sentiment=sentiment_obj,
            confidence=max(0.0, min(1.0, confidence)),
            engagement=engagement,
            timestamp=timestamp,
            author=raw.get("author") or raw.get("creator"),
            thread_id=raw.get("thread_id") or raw.get("video_id") or raw.get("qa_id"),
            permalink=raw.get("permalink") or url or None,
            metadata={
                key: value
                for key, value in raw.items()
                if key
                not in {
                    "title",
                    "body",
                    "answer",
                    "discussion",
                    "summary",
                    "transcript_excerpt",
                    "seller_response",
                    "comments",
                    "replies",
                    "community_responses",
                }
            },
            data_status="mock",
        )

    def normalize_many(
        self,
        items: list[dict[str, Any]],
        *,
        source: CommunitySource,
        product_id: str,
        product_name: str,
    ) -> list[CommunityEvidence]:
        return [
            self.normalize(item, source=source, product_id=product_id, product_name=product_name)
            for item in items
        ]

    def _engagement(self, raw: dict[str, Any], source: CommunitySource) -> CommunityEngagement:
        upvotes = int(raw.get("upvotes") or 0)
        comments = int(raw.get("comment_count") or raw.get("comments_count") or 0)
        if isinstance(raw.get("comments"), list):
            comments = max(comments, len(raw["comments"]))
        likes = int(raw.get("likes") or 0)
        views = int(raw.get("views") or 0)
        helpful = int(raw.get("helpful_votes") or 0)
        replies = int(raw.get("replies_count") or 0)
        if isinstance(raw.get("replies"), list):
            replies = max(replies, len(raw["replies"]))
        if isinstance(raw.get("community_responses"), list):
            replies = max(replies, len(raw["community_responses"]))

        score = float(
            upvotes * 1.0
            + comments * 0.5
            + likes * 0.2
            + min(views, 100_000) / 10_000
            + helpful * 0.8
            + replies * 0.4
        )
        if source == "youtube":
            score = float(likes * 0.3 + min(views, 500_000) / 5_000)
        return CommunityEngagement(
            score=round(score, 3),
            upvotes=upvotes,
            comments=comments,
            likes=likes,
            views=views,
            helpful_votes=helpful,
            replies=replies,
        )

    def _timestamp(self, raw: dict[str, Any]) -> datetime:
        for key in ("timestamp", "publish_date", "asked_at", "created_at"):
            value = raw.get(key)
            if isinstance(value, datetime):
                return value if value.tzinfo else value.replace(tzinfo=UTC)
            if isinstance(value, str) and value:
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
                except ValueError:
                    continue
        created = raw.get("created_utc")
        if created is not None:
            try:
                return datetime.fromtimestamp(float(created), tz=UTC)
            except (TypeError, ValueError, OSError):
                pass
        return datetime.now(UTC)

    def _confidence(self, engagement: CommunityEngagement, body: str) -> float:
        base = 0.45
        if len(body) > 40:
            base += 0.15
        if engagement.score >= 20:
            base += 0.2
        elif engagement.score >= 5:
            base += 0.1
        return min(0.95, base)
