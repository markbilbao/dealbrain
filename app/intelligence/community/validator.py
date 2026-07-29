"""Validate normalized community evidence before aggregation."""

from __future__ import annotations

from app.domain.entities.community_intelligence import CommunityEvidence
from app.domain.exceptions import CommunityIntelligenceValidationError

ALLOWED_SOURCES = {
    "reddit",
    "youtube",
    "amazon_qa",
    "marketplace_questions",
    "manufacturer_forums",
    "discord",
}


class EvidenceValidator:
    """Structural validation for CommunityEvidence items."""

    def validate(self, evidence: CommunityEvidence) -> CommunityEvidence:
        if not evidence.evidence_id or not str(evidence.evidence_id).strip():
            raise CommunityIntelligenceValidationError("evidence_id is required")
        if evidence.source not in ALLOWED_SOURCES:
            raise CommunityIntelligenceValidationError(f"unsupported source: {evidence.source}")
        if not evidence.product or not str(evidence.product).strip():
            raise CommunityIntelligenceValidationError("product is required")
        if not evidence.title and not evidence.body:
            raise CommunityIntelligenceValidationError("title or body is required")
        if evidence.confidence < 0 or evidence.confidence > 1:
            raise CommunityIntelligenceValidationError("confidence must be between 0 and 1")
        if evidence.sentiment.label not in {"positive", "neutral", "negative", "mixed"}:
            raise CommunityIntelligenceValidationError("invalid sentiment label")
        return evidence

    def validate_many(self, items: list[CommunityEvidence]) -> list[CommunityEvidence]:
        return [self.validate(item) for item in items]

    def is_valid(self, evidence: CommunityEvidence) -> bool:
        try:
            self.validate(evidence)
            return True
        except CommunityIntelligenceValidationError:
            return False
