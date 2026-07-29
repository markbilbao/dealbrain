"""Deterministic Community Trust Score (0–100)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.community_intelligence import (
    CommunityEvidence,
    CommunityTrustScore,
    ConfidenceBand,
)


def _band(score: int) -> ConfidenceBand:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


class CommunityTrustCalculator:
    """Calculate community trust using deterministic factors only."""

    def calculate(
        self,
        evidence: list[CommunityEvidence],
        *,
        ai_agreement: float | None = None,
        now: datetime | None = None,
    ) -> CommunityTrustScore:
        now = now or datetime.now(UTC)
        if not evidence:
            return CommunityTrustScore(
                score=0,
                factors={
                    "evidence_count": 0.0,
                    "independent_threads": 0.0,
                    "independent_users": 0.0,
                    "source_diversity": 0.0,
                    "topic_consistency": 0.0,
                    "ai_agreement": 0.0,
                    "data_freshness": 0.0,
                    "coverage": 0.0,
                },
                band="Low",
                explanation="No community evidence available.",
            )

        evidence_count = len(evidence)
        threads = {item.thread_id or item.evidence_id for item in evidence}
        users = {item.author for item in evidence if item.author}
        sources = {item.source for item in evidence}
        topics = {item.topic for item in evidence if item.topic}

        # Factor scores in 0–1
        evidence_factor = min(1.0, evidence_count / 20.0)
        threads_factor = min(1.0, len(threads) / 8.0)
        users_factor = min(1.0, len(users) / 8.0)
        diversity_factor = min(1.0, len(sources) / 4.0)

        # Topic consistency: share of top topic among all mentions.
        topic_counts: dict[str, int] = {}
        for item in evidence:
            topic_counts[item.topic] = topic_counts.get(item.topic, 0) + 1
        top_share = max(topic_counts.values()) / evidence_count if topic_counts else 0.0
        # Prefer moderate consistency (not single-topic spam, not total chaos).
        topic_consistency = 1.0 - abs(top_share - 0.35)
        topic_consistency = max(0.0, min(1.0, topic_consistency))

        agreement = 0.55 if ai_agreement is None else max(0.0, min(1.0, ai_agreement))

        ages = []
        for item in evidence:
            ts = item.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            ages.append(max(0.0, (now - ts).total_seconds() / 3600.0))
        median_age = sorted(ages)[len(ages) // 2] if ages else 9999.0
        # Fresher than ~45 days scores higher.
        freshness = max(0.0, min(1.0, 1.0 - (median_age / (45 * 24))))

        coverage = min(1.0, len(topics) / 8.0)

        factors = {
            "evidence_count": round(evidence_factor, 3),
            "independent_threads": round(threads_factor, 3),
            "independent_users": round(users_factor, 3),
            "source_diversity": round(diversity_factor, 3),
            "topic_consistency": round(topic_consistency, 3),
            "ai_agreement": round(agreement, 3),
            "data_freshness": round(freshness, 3),
            "coverage": round(coverage, 3),
        }
        weights = {
            "evidence_count": 0.16,
            "independent_threads": 0.14,
            "independent_users": 0.14,
            "source_diversity": 0.14,
            "topic_consistency": 0.10,
            "ai_agreement": 0.10,
            "data_freshness": 0.12,
            "coverage": 0.10,
        }
        weighted = sum(factors[key] * weights[key] for key in factors)
        score = int(round(max(0.0, min(1.0, weighted)) * 100))
        explanation = (
            f"Trust derived from {evidence_count} evidence items across "
            f"{len(sources)} sources and {len(threads)} threads."
        )
        return CommunityTrustScore(
            score=score,
            factors=factors,
            band=_band(score),
            explanation=explanation,
        )


# Alias matching architecture naming.
CommunityTrustScoreService = CommunityTrustCalculator
