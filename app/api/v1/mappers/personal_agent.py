"""Map Personal Agent domain objects to HTTP schemas."""

from __future__ import annotations

from app.core.public_brand import present_consumer_text
from app.domain.entities.personal_agent import (
    BuyingAdvice,
    CustomerProfile,
    PersonalDealScore,
    PersonalDealsResult,
    PersonalDemoPayload,
    PersonalRecommendation,
)
from app.schemas.personal_agent import (
    BuyingAdvicePayload,
    CustomerProfilePayload,
    PersonalDealScorePayload,
    PersonalDealsResponse,
    PersonalDemoResponse,
    PersonalRecommendationPayload,
    PreferenceDimensionPayload,
)


def to_profile_payload(profile: CustomerProfile) -> CustomerProfilePayload:
    data = profile.to_dict()
    return CustomerProfilePayload(**data)


def to_deal_score_payload(score: PersonalDealScore) -> PersonalDealScorePayload:
    data = score.to_dict()
    return PersonalDealScorePayload(
        product_id=data["product_id"],
        profile_id=data["profile_id"],
        personal_deal_score=data["personal_deal_score"],
        global_deal_score=data.get("global_deal_score"),
        preference_fit=data["preference_fit"],
        budget_fit=data["budget_fit"],
        brand_affinity=data["brand_affinity"],
        ownership_compatibility=data["ownership_compatibility"],
        community_trust=data["community_trust"],
        factors=[present_consumer_text(item) for item in data.get("factors") or []],
        evidence_ids=list(data.get("evidence_ids") or []),
    )


def to_advice_payload(advice: BuyingAdvice) -> BuyingAdvicePayload:
    data = advice.to_dict()
    return BuyingAdvicePayload(
        product_id=data["product_id"],
        profile_id=data["profile_id"],
        verdict=data["verdict"],
        label=data["label"],
        summary=present_consumer_text(data["summary"]),
        explanation=present_consumer_text(data["explanation"]),
        evidence=[present_consumer_text(item) for item in data.get("evidence") or []],
        evidence_ids=list(data.get("evidence_ids") or []),
        personal_deal_score=data.get("personal_deal_score"),
        alternative_product_id=data.get("alternative_product_id"),
        alternative_product_name=data.get("alternative_product_name"),
    )


def to_recommendation_payload(rec: PersonalRecommendation) -> PersonalRecommendationPayload:
    data = rec.to_dict()
    dims = data.get("preference_dimensions") or []
    return PersonalRecommendationPayload(
        product_id=data["product_id"],
        product_name=data["product_name"],
        profile_id=data["profile_id"],
        reason=present_consumer_text(data["reason"]),
        explanation=present_consumer_text(data["explanation"]),
        known_price=data.get("known_price"),
        currency=data.get("currency") or "PHP",
        marketplace=data.get("marketplace"),
        personal_deal_score=data["personal_deal_score"],
        global_deal_score=data.get("global_deal_score"),
        preference_score=data["preference_score"],
        confidence=data["confidence"],
        advice=to_advice_payload(rec.advice) if rec.advice else None,
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
        warnings=[present_consumer_text(item) for item in result.warnings],
        generated_at=result.generated_at.isoformat() if result.generated_at else None,
        processing=dict(result.processing),
    )


def to_demo_response(payload: PersonalDemoPayload) -> PersonalDemoResponse:
    return PersonalDemoResponse(
        active_profile=to_profile_payload(payload.active_profile),
        profiles=[to_profile_payload(item) for item in payload.profiles],
        deals=to_deals_response(payload.deals),
        limitations=[present_consumer_text(item) for item in payload.limitations],
    )
