"""AI Shopping Assistant domain entities and value objects.

Evidence-first shopping answers derived from DealBrain intelligence modules.
Identifiers and timestamps are injected by callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.domain.entities.research_authorization import ResearchAuthorization
from app.domain.entities.research_proposal import ResearchProposal
from app.domain.entities.session_refinement import SessionRecommendationRefinement

ShoppingIntentType = Literal[
    "recommendation",
    "comparison",
    "worth_buying",
    "best_offer",
    "complaints",
    "buy_now_or_wait",
    "use_case",
    "seller_trust",
    "general",
]

EvidenceType = Literal[
    "price",
    "rating",
    "review",
    "deal_score",
    "marketplace",
    "price_history",
    "product_identity",
    "recommendation",
    "seller",
    "watchlist",
    "community",
    "graph_path",
    "related_product",
    "cross_source_support",
    "contradiction",
    "compatibility",
    "community_topic",
]

DataStatus = Literal["mock", "imported", "live"]
ConfidenceBand = Literal["High", "Medium", "Low"]
AnalysisMode = Literal["economy", "balanced", "maximum"]
ConversationPrincipalType = Literal["guest", "account"]
ConversationActionType = Literal[
    "answer_from_evidence",
    "refine_session_recommendation",
    "propose_research",
]

MODE_RANK: dict[str, int] = {"economy": 0, "balanced": 1, "maximum": 2}


@dataclass(frozen=True, slots=True)
class ShoppingConstraint:
    """Structured constraint extracted from a shopping question."""

    category: str | None = None
    products: tuple[str, ...] = ()
    budget_min: float | None = None
    budget_max: float | None = None
    currency: str | None = None
    preferred_marketplace: str | None = None
    use_cases: tuple[str, ...] = ()
    preferred_features: tuple[str, ...] = ()
    excluded_features: tuple[str, ...] = ()
    brand_preference: str | None = None
    urgency: str | None = None
    location: str | None = None
    priorities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "products": list(self.products),
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "currency": self.currency,
            "preferred_marketplace": self.preferred_marketplace,
            "use_cases": list(self.use_cases),
            "preferred_features": list(self.preferred_features),
            "excluded_features": list(self.excluded_features),
            "brand_preference": self.brand_preference,
            "urgency": self.urgency,
            "location": self.location,
            "priorities": list(self.priorities),
        }


@dataclass(frozen=True, slots=True)
class ShoppingIntent:
    """Detected shopping intent with extracted constraints."""

    intent: ShoppingIntentType
    constraints: ShoppingConstraint
    raw_query: str
    parser: str = "deterministic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            **self.constraints.to_dict(),
            "raw_query": self.raw_query,
            "parser": self.parser,
        }


@dataclass(frozen=True, slots=True)
class ShoppingQuery:
    """Normalized shopping assistant request."""

    query: str
    mode: AnalysisMode | None = None
    conversation_id: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    currency: str | None = None
    use_cases: tuple[str, ...] = ()
    category: str | None = None
    products: tuple[str, ...] = ()
    profile_id: str | None = None
    user_id: str | None = None
    decision_id: str | None = None
    context_version: int | None = None
    surface: str | None = None
    proposal_id: str | None = None
    proposal_version: int | None = None
    confirmation_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode,
            "conversation_id": self.conversation_id,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "currency": self.currency,
            "use_cases": list(self.use_cases),
            "category": self.category,
            "products": list(self.products),
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "decision_id": self.decision_id,
            "context_version": self.context_version,
            "surface": self.surface,
            "proposal_id": self.proposal_id,
            "proposal_version": self.proposal_version,
            "confirmation_token": self.confirmation_token,
        }


@dataclass(frozen=True, slots=True)
class ShoppingEvidence:
    """Single evidence item supporting a shopping claim."""

    evidence_id: str
    type: EvidenceType
    source_id: str
    description: str
    product_id: str | None = None
    value: str | float | int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "type": self.type,
            "source_id": self.source_id,
            "description": self.description,
            "product_id": self.product_id,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class AssistantConfidence:
    """Deterministic confidence score with display band."""

    score: float
    band: ConfidenceBand
    factors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band,
            "factors": list(self.factors),
        }


@dataclass(frozen=True, slots=True)
class AssistantWarning:
    """Buyer-facing caution or data limitation."""

    message: str
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"message": self.message, "code": self.code}


@dataclass(frozen=True, slots=True)
class ShoppingCandidate:
    """Product candidate considered for an answer."""

    product_id: str
    product_name: str
    category: str
    known_price: float | None
    currency: str
    marketplace: str | None
    deal_score: float | None
    rating: float | None
    review_count: int
    brand: str | None = None
    use_cases: tuple[str, ...] = ()
    features: tuple[str, ...] = ()
    seller_name: str | None = None
    seller_trust_score: float | None = None
    price_near_low: bool | None = None
    recent_price_direction: str | None = None
    complaints: tuple[str, ...] = ()
    strengths: tuple[str, ...] = ()
    data_status: DataStatus = "mock"
    match_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "category": self.category,
            "known_price": self.known_price,
            "currency": self.currency,
            "marketplace": self.marketplace,
            "deal_score": self.deal_score,
            "rating": self.rating,
            "review_count": self.review_count,
            "brand": self.brand,
            "use_cases": list(self.use_cases),
            "features": list(self.features),
            "seller_name": self.seller_name,
            "seller_trust_score": self.seller_trust_score,
            "price_near_low": self.price_near_low,
            "recent_price_direction": self.recent_price_direction,
            "complaints": list(self.complaints),
            "strengths": list(self.strengths),
            "data_status": self.data_status,
            "match_score": self.match_score,
        }


@dataclass(frozen=True, slots=True)
class ShoppingRecommendation:
    """Ranked product recommendation with evidence references."""

    product_id: str
    product_name: str
    reason: str
    known_price: float | None
    currency: str
    marketplace: str | None
    deal_score: float | None
    confidence: float
    evidence_ids: tuple[str, ...] = ()
    rating: float | None = None
    review_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "reason": self.reason,
            "known_price": self.known_price,
            "currency": self.currency,
            "marketplace": self.marketplace,
            "deal_score": self.deal_score,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "rating": self.rating,
            "review_count": self.review_count,
        }


@dataclass(frozen=True, slots=True)
class CategoryWinner:
    """Which product wins a comparison dimension."""

    category: str
    product_id: str
    product_name: str
    reason: str
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "reason": self.reason,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class ProductComparison:
    """Structured comparison between two or more products."""

    product_ids: tuple[str, ...]
    product_names: tuple[str, ...]
    category_winners: tuple[CategoryWinner, ...]
    strengths: dict[str, tuple[str, ...]]
    weaknesses: dict[str, tuple[str, ...]]
    price_difference: float | None
    currency: str | None
    review_differences: tuple[str, ...]
    recommended_use_case: str | None
    overall_recommendation: str
    unresolved_uncertainty: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_ids": list(self.product_ids),
            "product_names": list(self.product_names),
            "category_winners": [item.to_dict() for item in self.category_winners],
            "strengths": {key: list(values) for key, values in self.strengths.items()},
            "weaknesses": {key: list(values) for key, values in self.weaknesses.items()},
            "price_difference": self.price_difference,
            "currency": self.currency,
            "review_differences": list(self.review_differences),
            "recommended_use_case": self.recommended_use_case,
            "overall_recommendation": self.overall_recommendation,
            "unresolved_uncertainty": list(self.unresolved_uncertainty),
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class AssistantDisagreement:
    """Meaningful multi-provider disagreement on an explanation claim."""

    field: str
    providers: tuple[str, ...]
    values: tuple[str, ...]
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "providers": list(self.providers),
            "values": list(self.values),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class ConversationOwner:
    """Server-validated principal binding for a conversation session."""

    principal_type: ConversationPrincipalType
    principal_id: str
    session_id: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.principal_type not in {"guest", "account"}:
            raise ValueError("principal_type must be guest or account")
        if not self.principal_id or len(self.principal_id) > 128:
            raise ValueError("principal_id must contain 1 to 128 characters")
        if not self.session_id or len(self.session_id) > 128:
            raise ValueError("session_id must contain 1 to 128 characters")
        if self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")

    def to_dict(self) -> dict[str, Any]:
        return {
            "principal_type": self.principal_type,
            "principal_id": self.principal_id,
            "session_id": self.session_id,
            "expires_at": self.expires_at.isoformat(),
        }

    def has_same_identity(self, other: ConversationOwner) -> bool:
        """Compare principal/session identity without treating expiry as identity."""

        return (
            self.principal_type,
            self.principal_id,
            self.session_id,
        ) == (
            other.principal_type,
            other.principal_id,
            other.session_id,
        )


@dataclass(frozen=True, slots=True)
class DecisionContextReference:
    """Immutable reference to one server-owned canonical decision snapshot.

    The digests are opaque integrity values. This value object never calculates
    PiqScore or Recommendation output and cannot replace either authority.
    """

    decision_id: str
    context_version: int
    evaluated_product_ids: tuple[str, ...]
    canonical_piqscore_snapshot_sha256: str
    recommendation_snapshot_sha256: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if self.context_version < 1:
            raise ValueError("context_version must be at least 1")
        if not self.evaluated_product_ids:
            raise ValueError("evaluated_product_ids must not be empty")
        if len(self.evaluated_product_ids) != len(set(self.evaluated_product_ids)):
            raise ValueError("evaluated_product_ids must be unique")
        if any(not product_id for product_id in self.evaluated_product_ids):
            raise ValueError("evaluated_product_ids must not contain empty values")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must be unique")
        for field_name, digest in (
            (
                "canonical_piqscore_snapshot_sha256",
                self.canonical_piqscore_snapshot_sha256,
            ),
            ("recommendation_snapshot_sha256", self.recommendation_snapshot_sha256),
        ):
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "context_version": self.context_version,
            "evaluated_product_ids": list(self.evaluated_product_ids),
            "canonical_piqscore_snapshot_sha256": self.canonical_piqscore_snapshot_sha256,
            "recommendation_snapshot_sha256": self.recommendation_snapshot_sha256,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """Minimum safe structured context for a follow-up turn."""

    role: str
    intent: ShoppingIntentType | None
    product_ids: tuple[str, ...]
    product_names: tuple[str, ...]
    query: str
    created_at: datetime
    turn_id: str | None = None
    decision_id: str | None = None
    context_version: int | None = None
    action: ConversationActionType | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "intent": self.intent,
            "product_ids": list(self.product_ids),
            "product_names": list(self.product_names),
            "query": self.query,
            "created_at": self.created_at.isoformat(),
            "turn_id": self.turn_id,
            "decision_id": self.decision_id,
            "context_version": self.context_version,
            "action": self.action,
        }


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """In-session conversation context (no secrets / prompts)."""

    conversation_id: str
    turns: tuple[ConversationTurn, ...]
    expires_at: datetime
    last_intent: ShoppingIntentType | None = None
    last_product_ids: tuple[str, ...] = ()
    last_product_names: tuple[str, ...] = ()
    last_category: str | None = None
    owner: ConversationOwner | None = None
    decision_context: DecisionContextReference | None = None
    session_refinement: SessionRecommendationRefinement | None = None
    research_proposal: ResearchProposal | None = None
    research_authorizations: tuple[ResearchAuthorization, ...] = ()
    persistence_version: int = 0

    def __post_init__(self) -> None:
        if self.decision_context is not None and self.owner is None:
            raise ValueError("a decision-bound conversation requires an owner")
        if self.persistence_version < 0:
            raise ValueError("persistence_version must not be negative")

    @property
    def research_authorization(self) -> ResearchAuthorization | None:
        return self.research_authorizations[-1] if self.research_authorizations else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "turns": [item.to_dict() for item in self.turns],
            "expires_at": self.expires_at.isoformat(),
            "last_intent": self.last_intent,
            "last_product_ids": list(self.last_product_ids),
            "last_product_names": list(self.last_product_names),
            "last_category": self.last_category,
            "owner": self.owner.to_dict() if self.owner else None,
            "decision_context": (
                self.decision_context.to_dict() if self.decision_context else None
            ),
            "session_refinement": (
                self.session_refinement.to_dict() if self.session_refinement else None
            ),
            "research_proposal": (
                self.research_proposal.to_dict() if self.research_proposal else None
            ),
            "research_authorizations": [item.to_dict() for item in self.research_authorizations],
            "persistence_version": self.persistence_version,
        }


@dataclass(frozen=True, slots=True)
class ShoppingAssistantResponse:
    """Normalized shopping assistant API / domain response."""

    query: str
    intent: ShoppingIntentType
    answer: str
    top_recommendation: ShoppingRecommendation | None
    alternatives: tuple[ShoppingRecommendation, ...]
    evidence: tuple[ShoppingEvidence, ...]
    warnings: tuple[AssistantWarning, ...]
    data_status: DataStatus
    providers_used: tuple[str, ...]
    fallback_used: bool
    confidence: AssistantConfidence
    mode: AnalysisMode = "economy"
    comparison: ProductComparison | None = None
    conversation_id: str | None = None
    disagreements: tuple[AssistantDisagreement, ...] = ()
    fallback_reason: str | None = None
    buy_now_or_wait: str | None = None
    processing: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime | None = None
    personal_recommendation: dict[str, Any] | None = None
    profile_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "answer": self.answer,
            "top_recommendation": (
                self.top_recommendation.to_dict() if self.top_recommendation else None
            ),
            "alternatives": [item.to_dict() for item in self.alternatives],
            "evidence": [item.to_dict() for item in self.evidence],
            "warnings": [item.to_dict() for item in self.warnings],
            "data_status": self.data_status,
            "providers_used": list(self.providers_used),
            "fallback_used": self.fallback_used,
            "confidence": self.confidence.to_dict(),
            "mode": self.mode,
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "conversation_id": self.conversation_id,
            "disagreements": [item.to_dict() for item in self.disagreements],
            "fallback_reason": self.fallback_reason,
            "buy_now_or_wait": self.buy_now_or_wait,
            "processing": dict(self.processing),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "personal_recommendation": self.personal_recommendation,
            "profile_id": self.profile_id,
        }
