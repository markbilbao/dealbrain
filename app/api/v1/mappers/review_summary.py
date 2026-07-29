"""Map Review Summary domain objects to HTTP schemas."""

from __future__ import annotations

from app.domain.entities.review_summary import ReviewSummary
from app.schemas.review_summary import (
    DisagreementPayload,
    EvidenceBundlePayload,
    EvidenceClaimPayload,
    ReviewInsightPayload,
    ReviewSummaryResponse,
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


def to_summary_response(summary: ReviewSummary) -> ReviewSummaryResponse:
    return ReviewSummaryResponse(
        product=summary.product,
        product_id=summary.product_id,
        overall_sentiment=summary.overall_sentiment,
        summary=summary.summary,
        pros=list(summary.pros.items),
        cons=list(summary.cons.items),
        warnings=[item.message for item in summary.warnings],
        recommendation=summary.recommendation.label,
        average_rating=summary.average_rating,
        total_review_count=summary.total_review_count,
        insights=[
            ReviewInsightPayload(
                theme=item.theme,
                label=item.label,
                polarity=item.polarity,
                frequency=item.frequency,
            )
            for item in summary.insights
        ],
        provider=summary.provider,
        summary_id=summary.summary_id,
        generated_at=summary.generated_at.isoformat(),
        mode=summary.mode,
        providers_used=list(summary.providers_used),
        models_used=list(summary.models_used),
        fallback_used=summary.fallback_used,
        fallback_reason=summary.fallback_reason,
        agreement_score=summary.agreement_score,
        consensus_confidence=summary.consensus_confidence,
        disagreements=[
            DisagreementPayload(
                field=item.field,
                providers=list(item.providers),
                values=list(item.values),
                detail=item.detail,
            )
            for item in summary.disagreements
        ],
        evidence=EvidenceBundlePayload(
            pros=[
                EvidenceClaimPayload(
                    claim=item.claim,
                    evidence_review_ids=list(item.evidence_review_ids),
                    confidence=item.confidence,
                )
                for item in summary.evidence_pros
            ],
            cons=[
                EvidenceClaimPayload(
                    claim=item.claim,
                    evidence_review_ids=list(item.evidence_review_ids),
                    confidence=item.confidence,
                )
                for item in summary.evidence_cons
            ],
            warnings=[
                EvidenceClaimPayload(
                    claim=item.claim,
                    evidence_review_ids=list(item.evidence_review_ids),
                    confidence=item.confidence,
                )
                for item in summary.evidence_warnings
            ],
        ),
        processing=_sanitize_processing(dict(summary.processing)),
    )
