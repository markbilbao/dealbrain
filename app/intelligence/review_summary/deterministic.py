"""Deterministic mock review summarizer — no external AI calls.

Future providers (OpenAI, Claude, Gemini) can replace this class behind the
``ReviewSummarizer`` port without changing SummaryService or the API.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime

from app.domain.entities.review_summary import (
    Cons,
    Pros,
    Recommendation,
    ReviewInsight,
    ReviewSummary,
    Warning,
)
from app.domain.interfaces.review_summary_repository import ReviewSummarizer
from app.intelligence.review_summary.fixtures import THEME_LEXICON


def classify_sentiment(average_rating: float | None) -> str:
    """Map average rating to an overall sentiment label."""
    if average_rating is None:
        return "Mixed"
    if average_rating > 4.6:
        return "Very Positive"
    if average_rating >= 4.2:
        return "Positive"
    if average_rating >= 3.8:
        return "Mixed"
    return "Negative"


def recommendation_for_sentiment(sentiment: str) -> str:
    """Map sentiment to a purchase recommendation label."""
    mapping = {
        "Very Positive": "Highly Recommended",
        "Positive": "Recommended",
        "Mixed": "Consider Carefully",
        "Negative": "Not Recommended",
    }
    return mapping.get(sentiment, "Consider Carefully")


def extract_theme_counts(review_texts: Sequence[str]) -> Counter[str]:
    """Count lexicon theme hits across review texts (case-insensitive).

    Each ``(polarity, label)`` theme is counted at most once per review text
    so synonym keywords (e.g. heat/heats/warm) do not inflate frequency.
    """
    counts: Counter[str] = Counter()
    # Longer keywords first so "heats" wins over "heat" within one text.
    keywords = sorted(THEME_LEXICON.keys(), key=len, reverse=True)
    for text in review_texts:
        lowered = text.lower()
        seen_labels: set[tuple[str, str]] = set()
        for keyword in keywords:
            if keyword not in lowered:
                continue
            polarity, label = THEME_LEXICON[keyword]
            theme_key = (polarity, label)
            if theme_key in seen_labels:
                continue
            seen_labels.add(theme_key)
            counts[label] += 1
    return counts


def rank_insights(
    counts: Counter[str],
    *,
    top_n: int = 6,
) -> list[ReviewInsight]:
    """Convert theme label counts into ranked ReviewInsight objects."""
    label_to_polarity = {
        label: polarity for polarity, label in THEME_LEXICON.values()
    }
    insights: list[ReviewInsight] = []
    for label, frequency in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        polarity = label_to_polarity.get(label, "pro")
        insights.append(
            ReviewInsight(
                theme=label,
                label=label,
                polarity=polarity,
                frequency=frequency,
            )
        )
        if len(insights) >= top_n * 2:
            break
    return insights


def _join_phrases(items: Sequence[str]) -> str:
    cleaned = [item.lower() for item in items if item]
    if not cleaned:
        return "overall quality"
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])} and {cleaned[-1]}"


def build_summary_paragraph(
    *,
    sentiment: str,
    pros: Sequence[str],
    cons: Sequence[str],
) -> str:
    """Compose a deterministic summary paragraph from ranked themes."""
    pro_phrase = _join_phrases(list(pros[:3]))

    if sentiment in {"Very Positive", "Positive"}:
        opener = f"Most buyers are satisfied with {pro_phrase}."
    elif sentiment == "Mixed":
        opener = f"Buyers report mixed experiences around {pro_phrase}."
    else:
        opener = f"Many buyers raise concerns despite notes about {pro_phrase}."

    if cons:
        closer = f" Some users report {_join_phrases(list(cons[:2]))}."
    else:
        closer = " Few recurring complaints were detected."

    return (opener + closer).strip()


class DeterministicMockReviewSummarizer(ReviewSummarizer):
    """Rule-based summarizer using rating thresholds and keyword frequency."""

    @property
    def provider_name(self) -> str:
        return "deterministic-mock"

    def summarize(
        self,
        *,
        product_id: str,
        product: str,
        review_texts: Sequence[str],
        average_rating: float | None,
        total_review_count: int,
        summary_id: str,
        generated_at: datetime,
    ) -> ReviewSummary:
        sentiment = classify_sentiment(average_rating)
        counts = extract_theme_counts(review_texts)
        insights = rank_insights(counts)

        pro_labels = [item.label for item in insights if item.polarity == "pro"][:4]
        con_labels = [item.label for item in insights if item.polarity == "con"][:3]
        warning_msgs = [
            Warning(message=item.label)
            for item in insights
            if item.polarity == "warning"
        ][:3]

        # Stable defaults when fixtures miss a polarity bucket.
        if not pro_labels:
            pro_labels = ["Solid quality"]
        if not con_labels and sentiment in {"Mixed", "Negative"}:
            con_labels = ["Inconsistent experiences"]

        paragraph = build_summary_paragraph(
            sentiment=sentiment,
            pros=pro_labels,
            cons=con_labels,
        )

        return ReviewSummary(
            summary_id=summary_id,
            product_id=product_id,
            product=product,
            overall_sentiment=sentiment,
            summary=paragraph,
            pros=Pros(items=tuple(pro_labels)),
            cons=Cons(items=tuple(con_labels)),
            warnings=tuple(warning_msgs),
            recommendation=Recommendation(label=recommendation_for_sentiment(sentiment)),
            insights=tuple(insights),
            average_rating=average_rating,
            total_review_count=total_review_count,
            provider=self.provider_name,
            generated_at=generated_at,
        )
