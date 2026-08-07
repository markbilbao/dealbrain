"""Map Affiliate Revenue Engine entities to HTTP response schemas — Sprint 20."""

from __future__ import annotations

from typing import Any

from app.core.public_brand import present_consumer_text
from app.domain.entities.affiliate import (
    AffiliateClick,
    AffiliateDisclosure,
    AffiliateLink,
    AffiliateMerchant,
    AffiliateRevenueReport,
    AttributionResult,
    RevenueReportBucket,
)
from app.schemas.affiliate import (
    AffiliateClickPayload,
    AffiliateDisclosurePayload,
    AffiliateLinkPayload,
    AffiliateMerchantPayload,
    AffiliateReportResponse,
    AttributionResultPayload,
    RevenueBucketPayload,
)


def to_merchant_payload(merchant: AffiliateMerchant) -> AffiliateMerchantPayload:
    return AffiliateMerchantPayload(
        merchant_id=merchant.merchant_id,
        merchant_name=merchant.merchant_name,
        marketplace=merchant.marketplace.value,
        country=merchant.country,
        affiliate_network=merchant.affiliate_network.value,
        tracking_template=merchant.tracking_template,
        commission_type=merchant.commission_type.value,
        commission_value=merchant.commission_value,
        cookie_days=merchant.cookie_days,
        status=merchant.status.value,
        priority=merchant.priority,
        created_at=merchant.created_at.isoformat(),
        updated_at=merchant.updated_at.isoformat(),
        health_status=merchant.health_status.value,
        allowed_countries=list(merchant.allowed_countries),
        deep_link_supported=merchant.deep_link_supported,
        notes=merchant.notes,
        simulated=True,
    )


def to_link_payload(link: AffiliateLink) -> AffiliateLinkPayload:
    return AffiliateLinkPayload(
        link_id=link.link_id,
        merchant_id=link.merchant_id,
        product_id=link.product_id,
        product_name=link.product_name,
        original_url=link.original_url,
        affiliate_url=link.affiliate_url,
        marketplace=link.marketplace.value,
        campaign_id=link.campaign_id,
        sub_id=link.sub_id,
        click_id=link.click_id,
        deep_link=link.deep_link,
        created_at=link.created_at.isoformat(),
        category=link.category,
        estimated_commission=link.estimated_commission,
        currency=link.currency,
        disclosure_required=link.disclosure_required,
        simulated=link.simulated,
    )


def to_click_payload(click: AffiliateClick) -> AffiliateClickPayload:
    return AffiliateClickPayload(
        click_id=click.click_id,
        user_id=click.user_id,
        session_id=click.session_id,
        merchant_id=click.merchant_id,
        product_id=click.product_id,
        timestamp=click.timestamp.isoformat(),
        device=click.device,
        country=click.country,
        campaign_id=click.campaign_id,
        source=click.source.value,
        referrer=click.referrer,
        conversion_status=click.conversion_status.value,
        revenue=click.revenue,
        link_id=click.link_id,
        product_name=click.product_name,
        category=click.category,
        marketplace=click.marketplace.value if click.marketplace else None,
        attribution_model=click.attribution_model.value,
        estimated_commission=click.estimated_commission,
        currency=click.currency,
        metadata=dict(click.metadata),
        simulated=click.simulated,
    )


def to_attribution_payload(result: AttributionResult) -> AttributionResultPayload:
    return AttributionResultPayload(
        attribution_id=result.attribution_id,
        model=result.model.value,
        click_id=result.click_id,
        merchant_id=result.merchant_id,
        product_id=result.product_id,
        attributed_at=result.attributed_at.isoformat(),
        revenue=result.revenue,
        estimated_commission=result.estimated_commission,
        reason=result.reason,
        candidates_considered=result.candidates_considered,
        currency=result.currency,
        simulated=result.simulated,
    )


def to_bucket_payload(bucket: RevenueReportBucket) -> RevenueBucketPayload:
    return RevenueBucketPayload(
        key=bucket.key,
        label=bucket.label,
        clicks=bucket.clicks,
        conversions=bucket.conversions,
        revenue=bucket.revenue,
        estimated_commission=bucket.estimated_commission,
        conversion_rate=bucket.conversion_rate,
        currency=bucket.currency,
    )


def to_report_payload(report: AffiliateRevenueReport) -> AffiliateReportResponse:
    return AffiliateReportResponse(
        report_id=report.report_id,
        generated_at=report.generated_at.isoformat(),
        total_clicks=report.total_clicks,
        total_conversions=report.total_conversions,
        conversion_rate=report.conversion_rate,
        ctr=report.ctr,
        estimated_commission=report.estimated_commission,
        total_revenue=report.total_revenue,
        impressions=report.impressions,
        by_merchant=[to_bucket_payload(b) for b in report.by_merchant],
        by_product=[to_bucket_payload(b) for b in report.by_product],
        by_category=[to_bucket_payload(b) for b in report.by_category],
        top_converting_merchants=[to_bucket_payload(b) for b in report.top_converting_merchants],
        top_converting_products=[to_bucket_payload(b) for b in report.top_converting_products],
        currency=report.currency,
        disclaimer=present_consumer_text(report.disclaimer)
        if report.disclaimer
        else report.disclaimer,
        simulated=report.simulated,
    )


def to_disclosure_payload(disclosure: AffiliateDisclosure) -> AffiliateDisclosurePayload:
    return AffiliateDisclosurePayload(
        disclosure_id=disclosure.disclosure_id,
        disclosure_type=disclosure.disclosure_type,
        text=present_consumer_text(disclosure.text),
        region=disclosure.region,
        merchant_id=disclosure.merchant_id,
        locale=disclosure.locale,
        created_at=disclosure.created_at.isoformat(),
        updated_at=disclosure.updated_at.isoformat(),
        ftc_placeholder=disclosure.ftc_placeholder,
        active=disclosure.active,
    )


def to_resolve_payload(resolved: dict[str, Any]) -> dict[str, Any]:
    combined = resolved["combined_text"]
    disclaimer = resolved.get("disclaimer")
    return {
        "disclosures": [to_disclosure_payload(d) for d in resolved["disclosures"]],
        "combined_text": present_consumer_text(combined) if combined else combined,
        "region": resolved.get("region"),
        "merchant_id": resolved.get("merchant_id"),
        "ftc_placeholder": resolved.get("ftc_placeholder", True),
        "disclaimer": present_consumer_text(disclaimer) if disclaimer else disclaimer,
    }
