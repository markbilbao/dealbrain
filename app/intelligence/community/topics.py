"""Configurable topic extraction for community evidence."""

from __future__ import annotations

import re
from collections import Counter

from app.domain.entities.community_intelligence import DEFAULT_TOPICS

# Keyword → topic mapping (lowercase). Future topics are configurable via constructor.
_DEFAULT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Battery": ("battery", "batteries", "charging", "mah", "power drain", "battery life"),
    "Camera": ("camera", "photo", "photos", "lens", "selfie", "low light"),
    "Gaming": ("gaming", "fps", "esports", "rtx", "gpu", "1080p", "1440p"),
    "Display": ("display", "screen", "brightness", "oled", "panel", "nits"),
    "Performance": ("performance", "fast", "speed", "benchmark", "cpu", "snappy"),
    "Heat": ("heat", "hot", "thermal", "thermals", "temperature", "throttl"),
    "Noise": ("noise", "loud", "fan", "fans", "whine", "coil"),
    "Durability": ("durability", "build", "plasticky", "chassis", "hinge", "solid"),
    "Warranty": ("warranty", "rma", "guarantee"),
    "Shipping": ("shipping", "delivery", "courier", "eta"),
    "Packaging": ("packaging", "box", "sealed", "package"),
    "Accessories": ("accessories", "charger", "adapter", "bundle", "included"),
    "Software": ("software", "bloat", "armoury", "driver", "armoury crate"),
    "Firmware": ("firmware", "bios", "firmware update"),
    "Compatibility": ("compatibility", "compatible", "linux", "monitor", "hdmi", "usb-c"),
    "Customer Service": ("customer service", "support", "service", "seller support"),
    "Value": ("value", "worth it", "bang for"),
    "Price": ("price", "pricing", "expensive", "cheap", "budget", "cost", "₱", "php"),
}


class TopicExtractor:
    """Extract configurable topics from free text."""

    def __init__(
        self,
        topics: tuple[str, ...] | None = None,
        keywords: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._topics = topics or DEFAULT_TOPICS
        self._keywords = keywords or dict(_DEFAULT_KEYWORDS)

    @property
    def topics(self) -> tuple[str, ...]:
        return self._topics

    def extract(self, text: str) -> list[str]:
        lowered = (text or "").lower()
        if not lowered.strip():
            return []
        found: list[str] = []
        for topic in self._topics:
            keys = self._keywords.get(topic, (topic.lower(),))
            if any(self._keyword_match(lowered, key) for key in keys):
                found.append(topic)
        return found

    def _keyword_match(self, text: str, key: str) -> bool:
        cleaned = (key or "").strip().lower()
        if not cleaned:
            return False
        # Prefer word-boundary matches to avoid "os" in "bios", "charge" in "charger"
        # colliding across topics incorrectly for short tokens.
        if len(cleaned) <= 4 or " " not in cleaned:
            return re.search(rf"(?<!\w){re.escape(cleaned)}(?!\w)", text) is not None
        return cleaned in text

    def primary_topic(self, text: str, *, default: str = "Performance") -> str:
        found = self.extract(text)
        if not found:
            return default
        # Prefer first match by configured topic order.
        return found[0]

    def count_topics(self, texts: list[str]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for text in texts:
            for topic in self.extract(text):
                counter[topic] += 1
        return counter

    def extract_questions(self, text: str) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return False
        if "?" in cleaned:
            return True
        return bool(re.match(r"^(how|what|does|is|are|can|should|will)\b", cleaned.lower()))
