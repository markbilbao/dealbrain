"""Search / filter community evidence."""

from __future__ import annotations

from app.domain.entities.community_intelligence import CommunityEvidence


class CommunitySearchService:
    """Filter evidence by topic, source, sentiment, or free text."""

    def search(
        self,
        evidence: list[CommunityEvidence],
        *,
        query: str | None = None,
        topic: str | None = None,
        source: str | None = None,
        sentiment: str | None = None,
        evidence_id: str | None = None,
        limit: int = 50,
    ) -> list[CommunityEvidence]:
        results = list(evidence)
        if evidence_id:
            results = [item for item in results if item.evidence_id == evidence_id]
        if topic:
            needle = topic.lower()
            results = [item for item in results if item.topic.lower() == needle]
        if source:
            results = [item for item in results if item.source == source]
        if sentiment:
            results = [item for item in results if item.sentiment.label == sentiment]
        if query:
            q = query.lower()
            results = [
                item
                for item in results
                if q in item.title.lower()
                or q in item.body.lower()
                or q in item.topic.lower()
                or q in item.evidence_id.lower()
            ]
        results.sort(key=lambda item: item.engagement.score, reverse=True)
        return results[: max(0, limit)]

    def get_by_id(
        self,
        evidence: list[CommunityEvidence],
        evidence_id: str,
    ) -> CommunityEvidence | None:
        for item in evidence:
            if item.evidence_id == evidence_id:
                return item
        return None
