"""Map Personal Agent domain objects to HTTP schemas."""

from __future__ import annotations

from app.domain.entities.personal_agent import (
    BuyingAdvice,
    CustomerProfile,
    PersonalDealScore,
    PersonalDemoPayload,
    PersonalDealsResult,
    PersonalRecommendation,
)
from app.schemas.personal_agent import (
    BuyingAdvicePayload,
    CustomerProfilePayload,
    PersonalDealScorePayload,
    PersonalDemoResponse,
    PersonalDealsResponse,
    PersonalRecommendationPayload,
    PreferenceDimensionPayload,
)


def to_profile_payload(profile: CustomerProfile) -> CustomerProfilePayload:
    data = profile.to_dict()
    return CustomerProfilePayload(**data)


def to_deal_score_payload(score: PersonalDealScore) -> PersonalDealScorePayload:
    return PersonalDealScorePayload(**score.to_dict())


def to_advice_payload(advice: BuyingAdvice) -> BuyingAdvicePayload:
    return BuyingAdvicePayload(**advice.to_dict())


def to_recommendation_payload(rec: PersonalRecommendation) -> PersonalRecommendationPayload:
    data = rec.to_dict()
    advice = data.get("advice")
    dims = data.get("preference_dimensions") or []
    return PersonalRecommendationPayload(
        product_id=data["product_id"],
        product_name=data["product_name"],
        profile_id=data["profile_id"],
        reason=data["reason"],
        explanation=data["explanation"],
        known_price=data.get("known_price"),
        currency=data.get("currency") or "PHP",
        marketplace=data.get("marketplace"),
        personal_deal_score=data["personal_deal_score"],
        global_deal_score=data.get("global_deal_score"),
        preference_score=data["preference_score"],
        confidence=data["confidence"],
        advice=BuyingAdvicePayload(**advice) if advice else None,
        evidence_ids=list(data.get("evidence_ids") or []),
        preference_dimensions=[PreferenceDimensionPayload(**item) for item in dims],
        rating=data.get("rating"),
        review_count=int(data.get("review_count") or 0),
    )


def to_deals_response(result: PersonalDealsResult) -> PersonalDealsResponse:
    return PersonalDealsResponse(
        profile_id=result.profile_id,
        recommendations=[to_recommendation_payload(item) for item in result.recommendations],
        data_status=result.data_status,
        warnings=list(result.warnings),
        generated_at=result.generated_at.isoformat() if result.generated_at else None,
        processing=dict(result.processing),
    )


def to_demo_response(payload: PersonalDemoPayload) -> PersonalDemoResponse:
    return PersonalDemoResponse(
        active_profile=to_profile_payload(payload.active_profile),
        profiles=[to_profile_payload(item) for item in payload.profiles],
        deals=to_deals_response(payload.deals),
        limitations=list(payload.limitations),
    )
