"""Build community activity timelines."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from app.domain.entities.community_intelligence import (
    CommunityEvidence,
    CommunityTimelineEvent,
)


class CommunityTimelineService:
    """Bucket evidence into chronological timeline events."""

    def build(
        self,
        evidence: list[CommunityEvidence],
        *,
        bucket: str = "day",
    ) -> list[CommunityTimelineEvent]:
        groups: dict[str, list[CommunityEvidence]] = defaultdict(list)
        for item in evidence:
            ts = item.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            key = ts.strftime("%Y-%m-%d") if bucket == "day" else ts.strftime("%Y-%m")
            groups[key].append(item)

        events: list[CommunityTimelineEvent] = []
        for key in sorted(groups.keys()):
            items = groups[key]
            ts = datetime.fromisoformat(key).replace(tzinfo=UTC)
            events.append(
                CommunityTimelineEvent(
                    timestamp=ts,
                    evidence_count=len(items),
                    positive_count=sum(
                        1 for item in items if item.sentiment.label == "positive"
                    ),
                    negative_count=sum(
                        1 for item in items if item.sentiment.label == "negative"
                    ),
                    topics=tuple(sorted({item.topic for item in items if item.topic})),
                    sources=tuple(sorted({item.source for item in items})),
                )
            )
        return events
