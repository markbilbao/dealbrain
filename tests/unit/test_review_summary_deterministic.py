"""Unit tests for deterministic review summarization helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from app.intelligence.review_summary.deterministic import (
    DeterministicMockReviewSummarizer,
    build_summary_paragraph,
    classify_sentiment,
    extract_theme_counts,
    recommendation_for_sentiment,
)
from app.intelligence.review_summary.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
    get_mock_review_texts,
)

FIXED_NOW = datetime(2026, 7, 29, 11, 0, tzinfo=UTC)


def test_classify_sentiment_thresholds() -> None:
    assert classify_sentiment(4.7) == "Very Positive"
    assert classify_sentiment(4.61) == "Very Positive"
    assert classify_sentiment(4.6) == "Positive"
    assert classify_sentiment(4.2) == "Positive"
    assert classify_sentiment(4.0) == "Mixed"
    assert classify_sentiment(3.8) == "Mixed"
    assert classify_sentiment(3.79) == "Negative"
    assert classify_sentiment(None) == "Mixed"


def test_recommendation_mapping() -> None:
    assert recommendation_for_sentiment("Very Positive") == "Highly Recommended"
    assert recommendation_for_sentiment("Positive") == "Recommended"
    assert recommendation_for_sentiment("Mixed") == "Consider Carefully"
    assert recommendation_for_sentiment("Negative") == "Not Recommended"


def test_extract_theme_counts_ranks_keywords() -> None:
    texts = get_mock_review_texts(IPHONE_DEMO_PRODUCT_ID)
    counts = extract_theme_counts(texts)
    assert counts["Excellent camera"] >= 2
    assert counts["Long battery life"] >= 2
    assert counts["Warms under heavy gaming"] >= 2
    assert counts["Some complaints about accessories"] >= 1


def test_build_summary_paragraph_joins_themes() -> None:
    paragraph = build_summary_paragraph(
        sentiment="Very Positive",
        pros=["Excellent camera", "Long battery life", "Premium build"],
        cons=["Expensive", "Warms under heavy gaming"],
    )
    assert "Most buyers are satisfied" in paragraph
    assert "excellent camera" in paragraph
    assert "long battery life" in paragraph
    assert "premium build" in paragraph
    assert "expensive" in paragraph


def test_deterministic_summarizer_iphone_shape() -> None:
    summarizer = DeterministicMockReviewSummarizer()
    summary = summarizer.summarize(
        product_id=IPHONE_DEMO_PRODUCT_ID,
        product=IPHONE_DEMO_PRODUCT_LABEL,
        review_texts=get_mock_review_texts(IPHONE_DEMO_PRODUCT_ID),
        average_rating=4.64,
        total_review_count=43364,
        summary_id="sum-1",
        generated_at=FIXED_NOW,
    )
    assert summary.product == IPHONE_DEMO_PRODUCT_LABEL
    assert summary.overall_sentiment == "Very Positive"
    assert summary.recommendation.label == "Highly Recommended"
    assert "Excellent camera" in summary.pros.items
    assert "Long battery life" in summary.pros.items
    assert "Premium build" in summary.pros.items
    assert "Fast delivery" in summary.pros.items
    assert "Expensive" in summary.cons.items
    assert "Warms under heavy gaming" in summary.cons.items
    assert any("accessories" in w.message.lower() for w in summary.warnings)
    assert summary.provider == "deterministic-mock"
    assert summary.summary


def test_deterministic_summarizer_is_stable() -> None:
    summarizer = DeterministicMockReviewSummarizer()
    texts = get_mock_review_texts(IPHONE_DEMO_PRODUCT_ID)
    first = summarizer.summarize(
        product_id=IPHONE_DEMO_PRODUCT_ID,
        product=IPHONE_DEMO_PRODUCT_LABEL,
        review_texts=texts,
        average_rating=4.64,
        total_review_count=43364,
        summary_id="a",
        generated_at=FIXED_NOW,
    )
    second = summarizer.summarize(
        product_id=IPHONE_DEMO_PRODUCT_ID,
        product=IPHONE_DEMO_PRODUCT_LABEL,
        review_texts=texts,
        average_rating=4.64,
        total_review_count=43364,
        summary_id="b",
        generated_at=FIXED_NOW,
    )
    assert first.overall_sentiment == second.overall_sentiment
    assert first.summary == second.summary
    assert first.pros.items == second.pros.items
    assert first.cons.items == second.cons.items
    assert [w.message for w in first.warnings] == [w.message for w in second.warnings]


def test_negative_sentiment_path() -> None:
    summarizer = DeterministicMockReviewSummarizer()
    summary = summarizer.summarize(
        product_id="low-rated",
        product="Budget Phone",
        review_texts=(
            "Heats during gaming.",
            "Packaging was poor.",
            "Expensive for what you get.",
            "Accessories missing.",
        ),
        average_rating=3.2,
        total_review_count=40,
        summary_id="sum-neg",
        generated_at=FIXED_NOW,
    )
    assert summary.overall_sentiment == "Negative"
    assert summary.recommendation.label == "Not Recommended"
    assert summary.cons.items
