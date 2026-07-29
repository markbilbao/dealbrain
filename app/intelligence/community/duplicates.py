"""Merge duplicate opinions so repeated claims are not over-counted."""

from __future__ import annotations

import hashlib
import re

from app.domain.entities.community_intelligence import CommunityEvidence


_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def _normalize_text(text: str) -> str:
    cleaned = _PUNCT.sub(" ", (text or "").lower())
    return _WHITESPACE.sub(" ", cleaned).strip()


def fingerprint(evidence: CommunityEvidence) -> str:
    """Stable fingerprint for near-duplicate opinion merging."""
    base = _normalize_text(f"{evidence.topic}|{evidence.title}|{evidence.body[:280]}")
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return f"{evidence.topic}:{digest}"


class DuplicateDetector:
    """Collapse near-duplicate opinions while keeping the strongest evidence."""

    def merge(self, items: list[CommunityEvidence]) -> list[CommunityEvidence]:
        if not items:
            return []
        buckets: dict[str, CommunityEvidence] = {}
        order: list[str] = []
        for item in items:
            key = fingerprint(item)
            existing = buckets.get(key)
            if existing is None:
                buckets[key] = item
                order.append(key)
                continue
            buckets[key] = self._prefer(existing, item)
        return [buckets[key] for key in order]

    def group(self, items: list[CommunityEvidence]) -> dict[str, list[CommunityEvidence]]:
        groups: dict[str, list[CommunityEvidence]] = {}
        for item in items:
            key = fingerprint(item)
            groups.setdefault(key, []).append(item)
        return groups

    def is_duplicate(self, left: CommunityEvidence, right: CommunityEvidence) -> bool:
        return fingerprint(left) == fingerprint(right)

    def _prefer(self, left: CommunityEvidence, right: CommunityEvidence) -> CommunityEvidence:
        left_score = (left.engagement.score, left.confidence, len(left.body))
        right_score = (right.engagement.score, right.confidence, len(right.body))
        return right if right_score > left_score else left
