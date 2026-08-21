"""Immutable canonical decision context for Sprint 29 conversational continuity.

These value objects preserve outputs supplied by the existing PiqScore and
Recommendation authorities. They validate and hash those outputs but never
calculate, rerank, or personalize them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.domain.entities.offer_economics import (
    CanonicalDeliveryContext,
    CanonicalOfferEconomics,
)
from app.domain.entities.shopping_assistant import (
    ConversationOwner,
    DecisionContextReference,
)

RecommendationDecision = Literal["buy", "wait", "consider", "avoid"]
EvidenceFreshness = Literal["fresh", "stale", "unknown"]
SCHEMA_VERSION_V1 = "1.0"
SCHEMA_VERSION_V1_1 = "1.1"
DATA_CLASSIFICATION_V1 = "non_live_contract_fixture"

PIQSCORE_AUTHORITY = "canonical-piqscore-dealscore-engine"
RECOMMENDATION_AUTHORITY = "canonical-recommendation-engine"


def _require_sha256(field_name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class CanonicalPiqScoreSnapshot:
    """Opaque output captured from the protected canonical PiqScore authority."""

    value: float
    authority: str
    semantics_version: str
    snapshot_sha256: str

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not 0 <= self.value <= 100:
            raise ValueError("canonical PiqScore value must be between 0 and 100")
        if self.authority != PIQSCORE_AUTHORITY:
            raise ValueError("canonical PiqScore authority is fixed")
        if not self.semantics_version:
            raise ValueError("PiqScore semantics_version is required")
        _require_sha256("canonical PiqScore snapshot_sha256", self.snapshot_sha256)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "authority": self.authority,
            "semantics_version": self.semantics_version,
            "snapshot_sha256": self.snapshot_sha256,
        }


@dataclass(frozen=True, slots=True)
class EvaluatedProductSnapshot:
    """One product/variant in the exact ordered canonical evaluated set."""

    product_id: str
    display_name: str
    variant: str
    canonical_piqscore: CanonicalPiqScoreSnapshot

    def __post_init__(self) -> None:
        if not self.product_id or len(self.product_id) > 128:
            raise ValueError("product_id must contain 1 to 128 characters")
        if not self.display_name or len(self.display_name) > 200:
            raise ValueError("display_name must contain 1 to 200 characters")
        if not self.variant or len(self.variant) > 200:
            raise ValueError("variant must contain 1 to 200 characters")

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "display_name": self.display_name,
            "variant": self.variant,
            "canonical_piqscore": self.canonical_piqscore.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CanonicalRecommendationSnapshot:
    """Opaque output captured from the protected Recommendation authority."""

    authority: str
    decision: RecommendationDecision
    best_piq_product_id: str
    alternative_product_ids: tuple[str, ...]
    snapshot_sha256: str

    def __post_init__(self) -> None:
        if self.authority != RECOMMENDATION_AUTHORITY:
            raise ValueError("canonical Recommendation authority is fixed")
        if self.decision not in {"buy", "wait", "consider", "avoid"}:
            raise ValueError("Recommendation decision is invalid")
        if not self.best_piq_product_id:
            raise ValueError("best_piq_product_id is required")
        if len(self.alternative_product_ids) != len(set(self.alternative_product_ids)):
            raise ValueError("alternative_product_ids must be unique")
        if any(not product_id for product_id in self.alternative_product_ids):
            raise ValueError("alternative_product_ids must not contain empty values")
        _require_sha256("Recommendation snapshot_sha256", self.snapshot_sha256)

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority": self.authority,
            "decision": self.decision,
            "best_piq_product_id": self.best_piq_product_id,
            "alternative_product_ids": list(self.alternative_product_ids),
            "snapshot_sha256": self.snapshot_sha256,
        }


@dataclass(frozen=True, slots=True)
class DecisionEvidenceSnapshot:
    """Evidence and provenance preserved with one canonical decision."""

    evidence_id: str
    product_id: str
    topic: str
    fact: str
    source: str
    captured_at: datetime
    freshness: EvidenceFreshness
    provenance_sha256: str

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("evidence_id", self.evidence_id, 128),
            ("product_id", self.product_id, 128),
            ("topic", self.topic, 128),
            ("fact", self.fact, 1000),
            ("source", self.source, 256),
        ):
            if not value or len(value) > maximum:
                raise ValueError(f"{field_name} must contain 1 to {maximum} characters")
        if self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        if self.freshness not in {"fresh", "stale", "unknown"}:
            raise ValueError("evidence freshness is invalid")
        _require_sha256("evidence provenance_sha256", self.provenance_sha256)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "product_id": self.product_id,
            "topic": self.topic,
            "fact": self.fact,
            "source": self.source,
            "captured_at": self.captured_at.isoformat(),
            "freshness": self.freshness,
            "provenance_sha256": self.provenance_sha256,
        }


@dataclass(frozen=True, slots=True)
class AffiliateNeutralitySnapshot:
    """Persisted proof that economics did not influence the canonical decision."""

    commission_influenced_candidates: bool = False
    commission_influenced_scores: bool = False
    commission_influenced_recommendation: bool = False
    commission_influenced_ordering: bool = False

    def __post_init__(self) -> None:
        if any(
            (
                self.commission_influenced_candidates,
                self.commission_influenced_scores,
                self.commission_influenced_recommendation,
                self.commission_influenced_ordering,
            )
        ):
            raise ValueError("affiliate influence must remain false")

    def to_dict(self) -> dict[str, bool]:
        return {
            "commission_influenced_candidates": self.commission_influenced_candidates,
            "commission_influenced_scores": self.commission_influenced_scores,
            "commission_influenced_recommendation": self.commission_influenced_recommendation,
            "commission_influenced_ordering": self.commission_influenced_ordering,
        }


@dataclass(frozen=True, slots=True)
class CanonicalDecisionSnapshot:
    """Immutable, owner-bound server snapshot used by every follow-up turn."""

    decision_id: str
    context_version: int
    owner: ConversationOwner
    evaluated_products: tuple[EvaluatedProductSnapshot, ...]
    recommendation: CanonicalRecommendationSnapshot
    evidence: tuple[DecisionEvidenceSnapshot, ...]
    unknowns: tuple[str, ...]
    affiliate_neutrality: AffiliateNeutralitySnapshot
    created_at: datetime
    updated_at: datetime
    offer_economics: tuple[CanonicalOfferEconomics, ...] = ()
    delivery_context: CanonicalDeliveryContext | None = None
    data_classification: str = DATA_CLASSIFICATION_V1

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if self.context_version < 1:
            raise ValueError("context_version must be at least 1")
        if len(self.evaluated_products) < 2:
            raise ValueError("evaluated_products must contain at least two products")
        product_ids = self.evaluated_product_ids
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("evaluated product IDs must be unique")
        if self.recommendation.best_piq_product_id not in product_ids:
            raise ValueError("Best Piq must belong to the evaluated product set")
        if self.recommendation.best_piq_product_id in self.recommendation.alternative_product_ids:
            raise ValueError("Best Piq cannot also be an alternative")
        if any(
            product_id not in product_ids
            for product_id in self.recommendation.alternative_product_ids
        ):
            raise ValueError("Recommendation alternatives must belong to the evaluated set")
        if not self.evidence:
            raise ValueError("evidence must not be empty")
        evidence_ids = self.evidence_ids
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        if any(item.product_id not in product_ids for item in self.evidence):
            raise ValueError("evidence must refer only to evaluated products")
        if len(self.unknowns) != len(set(self.unknowns)) or any(not item for item in self.unknowns):
            raise ValueError("unknowns must contain unique non-empty values")
        if self.created_at.utcoffset() is None or self.updated_at.utcoffset() is None:
            raise ValueError("decision timestamps must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.data_classification not in {
            DATA_CLASSIFICATION_V1,
            "canonical_decision",
        }:
            raise ValueError("data_classification is invalid")
        economics_ids = tuple(item.product_id for item in self.offer_economics)
        if len(economics_ids) != len(set(economics_ids)):
            raise ValueError("offer economics product IDs must be unique")
        if any(product_id not in product_ids for product_id in economics_ids):
            raise ValueError("offer economics must refer only to evaluated products")

    @property
    def evaluated_product_ids(self) -> tuple[str, ...]:
        return tuple(item.product_id for item in self.evaluated_products)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.evidence)

    @property
    def schema_version(self) -> str:
        return SCHEMA_VERSION_V1_1 if self.offer_economics else SCHEMA_VERSION_V1

    @property
    def canonical_piqscore_set_sha256(self) -> str:
        """Integrity digest over preserved PiqScore outputs, not a score calculation."""

        return _canonical_sha256(
            [
                {
                    "product_id": item.product_id,
                    "canonical_piqscore": item.canonical_piqscore.to_dict(),
                }
                for item in self.evaluated_products
            ]
        )

    @property
    def content_sha256(self) -> str:
        """Integrity digest for immutable persistence and tamper detection."""

        return _canonical_sha256(self.to_dict())

    def to_reference(self) -> DecisionContextReference:
        return DecisionContextReference(
            decision_id=self.decision_id,
            context_version=self.context_version,
            evaluated_product_ids=self.evaluated_product_ids,
            canonical_piqscore_snapshot_sha256=self.canonical_piqscore_set_sha256,
            recommendation_snapshot_sha256=self.recommendation.snapshot_sha256,
            evidence_ids=self.evidence_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": SCHEMA_VERSION_V1,
            "data_classification": DATA_CLASSIFICATION_V1,
            "decision_id": self.decision_id,
            "context_version": self.context_version,
            "owner": self.owner.to_dict(),
            "evaluated_products": [item.to_dict() for item in self.evaluated_products],
            "recommendation": self.recommendation.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "unknowns": list(self.unknowns),
            "affiliate_neutrality": self.affiliate_neutrality.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if not self.offer_economics:
            return payload
        payload["schema_version"] = SCHEMA_VERSION_V1_1
        payload["data_classification"] = self.data_classification
        payload["offer_economics"] = [item.to_dict() for item in self.offer_economics]
        if self.delivery_context is not None:
            payload["delivery_context"] = self.delivery_context.to_dict()
        return payload
