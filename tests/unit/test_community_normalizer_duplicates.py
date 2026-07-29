"""Normalization and duplicate detection tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.community_intelligence import (
    CommunityEngagement,
    CommunityEvidence,
    CommunitySentiment,
)
from app.intelligence.community.duplicates import DuplicateDetector, fingerprint
from app.intelligence.community.normalizer import EvidenceNormalizer
from app.intelligence.community.validator import EvidenceValidator

NORMALIZER = EvidenceNormalizer()
VALIDATOR = EvidenceValidator()
DETECTOR = DuplicateDetector()


def _evidence(**kwargs) -> CommunityEvidence:
    defaults = dict(
        source="reddit",
        product="Demo",
        product_id="demo",
        evidence_id="e1",
        url="https://example.com",
        title="Battery life",
        body="Battery lasts a long time",
        topic="Battery",
        sentiment=CommunitySentiment(label="positive", score=0.5),
        confidence=0.7,
        engagement=CommunityEngagement(score=10, upvotes=5),
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    defaults.update(kwargs)
    return CommunityEvidence(**defaults)


SOURCES = [
    "reddit",
    "youtube",
    "amazon_qa",
    "marketplace_questions",
    "manufacturer_forums",
    "discord",
]


@pytest.mark.parametrize("source", SOURCES)
def test_normalize_common_fields(source):
    item = NORMALIZER.normalize(
        {
            "title": "Battery discussion",
            "body": "Battery is excellent for school use",
            "url": "https://example.com/x",
            "upvotes": 10,
            "created_utc": datetime(2026, 6, 1, tzinfo=UTC).timestamp(),
        },
        source=source,  # type: ignore[arg-type]
        product_id="p1",
        product_name="Product 1",
        evidence_id=f"{source}:1",
    )
    assert item.source == source
    assert item.product == "Product 1"
    assert item.evidence_id == f"{source}:1"
    assert item.topic == "Battery"
    assert item.url
    assert 0 <= item.confidence <= 1
    VALIDATOR.validate(item)


@pytest.mark.parametrize(
    ("raw", "expected_topic"),
    [
        ({"title": "Camera test", "body": "photos are sharp"}, "Camera"),
        ({"question": "How is shipping?", "answer": "delivery was fine"}, "Shipping"),
        ({"title": "Firmware notes", "discussion": "bios update"}, "Firmware"),
        ({"title": "Value check", "summary": "worth it at this price"}, "Value"),
    ],
)
def test_normalize_topic_inference(raw, expected_topic):
    item = NORMALIZER.normalize(raw, source="reddit", product_id="p", product_name="P")
    assert item.topic == expected_topic


def test_normalize_youtube_engagement():
    item = NORMALIZER.normalize(
        {"title": "Review", "body": "gaming performance", "likes": 100, "views": 50000},
        source="youtube",
        product_id="p",
        product_name="P",
    )
    assert item.engagement.likes == 100
    assert item.engagement.views == 50000
    assert item.engagement.score > 0


def test_validator_rejects_blank_id():
    with pytest.raises(Exception):
        VALIDATOR.validate(_evidence(evidence_id=""))


def test_validator_rejects_bad_confidence():
    with pytest.raises(Exception):
        VALIDATOR.validate(_evidence(confidence=1.5))


def test_validator_is_valid_true():
    assert VALIDATOR.is_valid(_evidence()) is True


def test_duplicate_fingerprint_stable():
    a = _evidence()
    b = _evidence(evidence_id="other", engagement=CommunityEngagement(score=99))
    assert fingerprint(a) == fingerprint(b)


def test_duplicate_merge_keeps_stronger():
    weak = _evidence(evidence_id="weak", engagement=CommunityEngagement(score=1))
    strong = _evidence(evidence_id="strong", engagement=CommunityEngagement(score=50))
    merged = DETECTOR.merge([weak, strong])
    assert len(merged) == 1
    assert merged[0].evidence_id == "strong"


def test_duplicate_different_topics_not_merged():
    a = _evidence(topic="Battery", title="Battery", body="Battery good")
    b = _evidence(
        evidence_id="e2",
        topic="Heat",
        title="Heat",
        body="Heat bad",
    )
    assert len(DETECTOR.merge([a, b])) == 2


def test_duplicate_is_duplicate():
    a = _evidence()
    b = _evidence(evidence_id="x")
    assert DETECTOR.is_duplicate(a, b) is True


def test_duplicate_group():
    items = [_evidence(evidence_id="a"), _evidence(evidence_id="b")]
    groups = DETECTOR.group(items)
    assert len(groups) == 1
    assert len(next(iter(groups.values()))) == 2


def test_normalize_many():
    items = NORMALIZER.normalize_many(
        [{"title": "A", "body": "battery"}, {"title": "B", "body": "camera"}],
        source="reddit",
        product_id="p",
        product_name="P",
    )
    assert len(items) == 2


@pytest.mark.parametrize("n", list(range(1, 21)))
def test_merge_idempotent_for_identical_copies(n):
    base = _evidence()
    copies = [_evidence(evidence_id=f"e{i}") for i in range(n)]
    merged = DETECTOR.merge(copies)
    assert len(merged) == 1
    assert fingerprint(merged[0]) == fingerprint(base)
