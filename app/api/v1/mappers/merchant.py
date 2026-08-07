"""Merchant Platform API mappers — Sprint 21."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.public_brand import present_consumer_text
from app.domain.entities.merchant import (
    MerchantAnalyticsSummary,
    MerchantCampaign,
    MerchantInvitation,
    MerchantMembership,
    MerchantOfferSubmission,
    MerchantOrganization,
    MerchantProductSubmission,
    MerchantPromotion,
    RankingExplanation,
)
from app.schemas.merchant import (
    MerchantAnalyticsResponse,
    MerchantCampaignPayload,
    MerchantInvitationPayload,
    MerchantMatchResultPayload,
    MerchantMembershipPayload,
    MerchantOfferPayload,
    MerchantOrganizationPayload,
    MerchantProductPayload,
    MerchantProfilePayload,
    MerchantPromotionPayload,
    MerchantRankingExplanationResponse,
)


def _parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def to_organization_payload(org: MerchantOrganization) -> MerchantOrganizationPayload:
    data = org.to_dict()
    profile = data["profile"]
    return MerchantOrganizationPayload(
        organization_id=data["organization_id"],
        profile=MerchantProfilePayload(**profile),
        status=data["status"],
        owner_account_id=data["owner_account_id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        affiliate_merchant_id=data.get("affiliate_merchant_id"),
        archived_at=data.get("archived_at"),
        notes=data.get("notes", ""),
    )


def to_membership_payload(membership: MerchantMembership) -> MerchantMembershipPayload:
    data = membership.to_dict()
    return MerchantMembershipPayload(**data)


def to_invitation_payload(invitation: MerchantInvitation) -> MerchantInvitationPayload:
    return MerchantInvitationPayload(**invitation.to_dict())


def to_product_payload(submission: MerchantProductSubmission) -> MerchantProductPayload:
    data = submission.to_dict()
    match = data.get("match_result")
    return MerchantProductPayload(
        submission_id=data["submission_id"],
        organization_id=data["organization_id"],
        submitted_by_account_id=data["submitted_by_account_id"],
        status=data["status"],
        title=data["title"],
        brand=data.get("brand"),
        model=data.get("model"),
        category=data.get("category"),
        description=data.get("description", ""),
        sku=data.get("sku"),
        upc=data.get("upc"),
        ean=data.get("ean"),
        gtin=data.get("gtin"),
        merchant_product_id=data.get("merchant_product_id"),
        image_urls=data.get("image_urls", []),
        identifiers=data.get("identifiers", {}),
        warranty=data.get("warranty"),
        seller_info=data.get("seller_info"),
        validation_errors=data.get("validation_errors", []),
        match_result=MerchantMatchResultPayload(**match) if match else None,
        source_mode=data["source_mode"],
        source_label=data["source_label"],
        matched_product_id=data.get("matched_product_id"),
        review_notes=data.get("review_notes", ""),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def to_offer_payload(offer: MerchantOfferSubmission) -> MerchantOfferPayload:
    data = offer.to_dict()
    return MerchantOfferPayload(
        offer_id=data["offer_id"],
        organization_id=data["organization_id"],
        submitted_by_account_id=data["submitted_by_account_id"],
        status=data["status"],
        title=data["title"],
        currency=data["currency"],
        price=data["price"],
        sale_price=data.get("sale_price"),
        shipping_cost=data["shipping_cost"],
        total_price=data["total_price"],
        inventory_quantity=data.get("inventory_quantity"),
        availability=data["availability"],
        marketplace_url=data.get("marketplace_url"),
        warranty=data.get("warranty"),
        seller_details=data.get("seller_details"),
        product_submission_id=data.get("product_submission_id"),
        matched_product_id=data.get("matched_product_id"),
        validation_errors=data.get("validation_errors", []),
        source_mode=data["source_mode"],
        source_label=data["source_label"],
        is_active=data["is_active"],
        review_notes=data.get("review_notes", ""),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def to_promotion_payload(promotion: MerchantPromotion) -> MerchantPromotionPayload:
    data = promotion.to_dict()
    note = data.get("note")
    if isinstance(note, str):
        data["note"] = present_consumer_text(note)
    return MerchantPromotionPayload(**data)


def to_campaign_payload(campaign: MerchantCampaign) -> MerchantCampaignPayload:
    data = campaign.to_dict()
    return MerchantCampaignPayload(**data)


def to_analytics_response(summary: MerchantAnalyticsSummary) -> MerchantAnalyticsResponse:
    data = summary.to_dict()
    return MerchantAnalyticsResponse(**data)


def to_ranking_explanation_response(
    explanation: RankingExplanation,
) -> MerchantRankingExplanationResponse:
    data = explanation.to_dict()
    factors = []
    for factor in data.get("factors") or []:
        detail = factor.get("detail")
        if isinstance(detail, str):
            factor = {**factor, "detail": present_consumer_text(detail)}
        factors.append(factor)
    data["factors"] = factors
    return MerchantRankingExplanationResponse(**data)


def parse_optional_datetime(value: str | None) -> datetime | None:
    return _parse_dt(value)


def drop_none(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}
