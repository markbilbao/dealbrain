"""Map Shopping Assistant domain objects to HTTP schemas."""

from __future__ import annotations

from app.core.public_brand import present_consumer_text
from app.domain.entities.shopping_assistant import ShoppingAssistantResponse as DomainResponse
from app.schemas.shopping_assistant import (
    CategoryWinnerPayload,
    ComparisonPayload,
    ConfidencePayload,
    DisagreementPayload,
    EvidencePayload,
    RecommendationPayload,
    ShoppingAssistantResponse,
    WarningPayload,
)

_SECRET_KEYS = ("api_key", "apikey", "authorization", "secret", "token", "prompt")


def _sanitize_processing(processing: dict) -> dict:
    cleaned: dict = {}
    for key, value in processing.items():
        lowered = str(key).lower()
        if any(part in lowered for part in _SECRET_KEYS):
            continue
        cleaned[key] = value
    return cleaned


def _to_recommendation(item) -> RecommendationPayload:
    return RecommendationPayload(
        product_id=item.product_id,
        product_name=item.product_name,
        reason=present_consumer_text(item.reason),
        known_price=item.known_price,
        currency=item.currency,
        marketplace=item.marketplace,
        deal_score=item.deal_score,
        confidence=item.confidence,
        evidence_ids=list(item.evidence_ids),
        rating=item.rating,
        review_count=item.review_count,
    )


def to_assistant_response(
    response: DomainResponse,
    *,
    allowed_modes: list[str] | None = None,
) -> ShoppingAssistantResponse:
    comparison = None
    if response.comparison is not None:
        comparison = ComparisonPayload(
            product_ids=list(response.comparison.product_ids),
            product_names=list(response.comparison.product_names),
            category_winners=[
                CategoryWinnerPayload(
                    category=item.category,
                    product_id=item.product_id,
                    product_name=item.product_name,
                    reason=present_consumer_text(item.reason),
                    evidence_ids=list(item.evidence_ids),
                )
                for item in response.comparison.category_winners
            ],
            strengths={
                key: [present_consumer_text(v) for v in values]
                for key, values in response.comparison.strengths.items()
            },
            weaknesses={
                key: [present_consumer_text(v) for v in values]
                for key, values in response.comparison.weaknesses.items()
            },
            price_difference=response.comparison.price_difference,
            currency=response.comparison.currency,
            review_differences=[
                present_consumer_text(item) for item in response.comparison.review_differences
            ],
            recommended_use_case=(
                present_consumer_text(response.comparison.recommended_use_case)
                if response.comparison.recommended_use_case
                else None
            ),
            overall_recommendation=present_consumer_text(
                response.comparison.overall_recommendation
            ),
            unresolved_uncertainty=[
                present_consumer_text(item) for item in response.comparison.unresolved_uncertainty
            ],
            evidence_ids=list(response.comparison.evidence_ids),
        )

    return ShoppingAssistantResponse(
        query=response.query,
        intent=response.intent,
        answer=present_consumer_text(response.answer),
        top_recommendation=(
            _to_recommendation(response.top_recommendation) if response.top_recommendation else None
        ),
        alternatives=[_to_recommendation(item) for item in response.alternatives],
        evidence=[
            EvidencePayload(
                type=item.type,
                source_id=item.source_id,
                description=present_consumer_text(item.description),
                evidence_id=item.evidence_id,
                product_id=item.product_id,
                value=item.value,
            )
            for item in response.evidence
        ],
        warnings=[
            WarningPayload(
                message=present_consumer_text(item.message),
                code=item.code,
            )
            for item in response.warnings
        ],
        data_status=response.data_status,
        providers_used=list(response.providers_used),
        fallback_used=response.fallback_used,
        confidence=ConfidencePayload(
            score=response.confidence.score,
            band=response.confidence.band,
            factors=list(response.confidence.factors),
        ),
        mode=response.mode,
        comparison=comparison,
        conversation_id=response.conversation_id,
        disagreements=[
            DisagreementPayload(
                field=item.field,
                providers=list(item.providers),
                values=list(item.values),
                detail=item.detail,
            )
            for item in response.disagreements
        ],
        fallback_reason=(
            present_consumer_text(response.fallback_reason) if response.fallback_reason else None
        ),
        buy_now_or_wait=(
            present_consumer_text(response.buy_now_or_wait) if response.buy_now_or_wait else None
        ),
        processing=_sanitize_processing(dict(response.processing)),
        generated_at=response.generated_at.isoformat() if response.generated_at else None,
        allowed_modes=list(allowed_modes or response.processing.get("allowed_modes") or []),
        personal_recommendation=response.personal_recommendation,
        profile_id=response.profile_id,
        action=response.processing.get("action"),
        answer_status=response.processing.get("answer_status"),
        decision_id=response.processing.get("decision_id"),
        session_best_piq_product_id=response.processing.get("session_best_piq_product_id"),
        original_best_piq_product_id=response.processing.get("original_best_piq_product_id"),
        recommendation_changed=response.processing.get("recommendation_changed"),
        requires_research_confirmation=response.processing.get("requires_research_confirmation"),
        research_proposal=response.processing.get("research_proposal"),
    )
