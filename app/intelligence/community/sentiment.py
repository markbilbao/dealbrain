"""Deterministic sentiment labeling for community text."""

from __future__ import annotations

from app.domain.entities.community_intelligence import CommunitySentiment

_POSITIVE = (
    "excellent",
    "great",
    "good",
    "solid",
    "strong",
    "love",
    "worth",
    "surprised",
    "best",
    "praises",
    "recommended",
    "handles well",
    "impressive",
    "honored",
    "improved",
    "fine",
    "works",
)

_NEGATIVE = (
    "bad",
    "poor",
    "loud",
    "noise",
    "hot",
    "heat",
    "slow",
    "weak",
    "complaint",
    "issue",
    "bloat",
    "steep",
    "expensive",
    "damage",
    "throttl",
    "plasticky",
    "barrier",
    "mixed",
    "disappoint",
)


def analyze_sentiment(text: str) -> CommunitySentiment:
    lowered = (text or "").lower()
    pos = sum(1 for token in _POSITIVE if token in lowered)
    neg = sum(1 for token in _NEGATIVE if token in lowered)
    if pos == 0 and neg == 0:
        return CommunitySentiment(label="neutral", score=0.0)
    if pos > 0 and neg > 0:
        score = (pos - neg) / max(pos + neg, 1)
        if abs(score) < 0.25:
            return CommunitySentiment(label="mixed", score=round(score, 3))
        label = "positive" if score > 0 else "negative"
        return CommunitySentiment(label=label, score=round(score, 3))  # type: ignore[arg-type]
    if pos > neg:
        return CommunitySentiment(label="positive", score=round(min(1.0, pos / 3), 3))
    return CommunitySentiment(label="negative", score=round(-min(1.0, neg / 3), 3))
