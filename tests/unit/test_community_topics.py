"""Topic extraction tests."""

from __future__ import annotations

import pytest

from app.domain.entities.community_intelligence import DEFAULT_TOPICS
from app.intelligence.community.topics import TopicExtractor

EXTRACTOR = TopicExtractor()

TOPIC_CASES = [
    ("Battery lasts 6 hours", "Battery"),
    ("The camera is excellent in low light", "Camera"),
    ("Great for 1080p gaming with RTX", "Gaming"),
    ("Display brightness is average", "Display"),
    ("CPU performance is snappy", "Performance"),
    ("Heat and thermals under load", "Heat"),
    ("Fans are loud — noise complaint", "Noise"),
    ("Build durability feels solid", "Durability"),
    ("Warranty RMA took two weeks", "Warranty"),
    ("Shipping delivery was slow", "Shipping"),
    ("Packaging box arrived sealed", "Packaging"),
    ("Accessories charger not included", "Accessories"),
    ("Software bloat in Armoury Crate", "Software"),
    ("Firmware BIOS update helped", "Firmware"),
    ("HDMI compatibility with monitors", "Compatibility"),
    ("Customer service support was slow", "Customer Service"),
    ("Great value worth it", "Value"),
    ("Price is expensive in PHP", "Price"),
]


@pytest.mark.parametrize(("text", "expected"), TOPIC_CASES)
def test_primary_topic(text, expected):
    assert EXTRACTOR.primary_topic(text) == expected


@pytest.mark.parametrize("topic", list(DEFAULT_TOPICS))
def test_default_topics_configured(topic):
    assert topic in EXTRACTOR.topics


@pytest.mark.parametrize(
    "text",
    [
        "How is the battery?",
        "What about warranty?",
        "Does shipping include packaging?",
        "Is price worth it?",
        "Can firmware improve noise?",
    ],
)
def test_extract_questions_true(text):
    assert EXTRACTOR.extract_questions(text) is True


@pytest.mark.parametrize("text", ["Battery is fine", "", "Solid laptop overall"])
def test_extract_questions_false(text):
    assert EXTRACTOR.extract_questions(text) is False


def test_extract_multiple_topics():
    found = EXTRACTOR.extract("Battery and heat with loud fan noise during gaming")
    assert "Battery" in found
    assert "Heat" in found
    assert "Noise" in found
    assert "Gaming" in found


def test_custom_topics_configurable():
    extractor = TopicExtractor(
        topics=("CustomTopic",),
        keywords={"CustomTopic": ("widget",)},
    )
    assert extractor.primary_topic("this widget rocks") == "CustomTopic"


def test_count_topics():
    counts = EXTRACTOR.count_topics(["good battery", "bad battery", "nice camera"])
    assert counts["Battery"] == 2
    assert counts["Camera"] == 1


def test_empty_text_returns_empty():
    assert EXTRACTOR.extract("   ") == []
    assert EXTRACTOR.primary_topic("", default="Value") == "Value"
