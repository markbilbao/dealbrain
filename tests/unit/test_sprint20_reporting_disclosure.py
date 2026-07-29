"""Sprint 20 unit tests — reporting & disclosure."""

from __future__ import annotations

from datetime import UTC, datetime

from app.affiliate.memory import InMemoryAffiliateRepository
from app.affiliate.reporting.aggregator import aggregate_revenue_report
from app.domain.entities.affiliate import (
    AffiliateClick,
    ClickSource,
    ConversionStatus,
    MarketplacePlaceholder,
)
from app.services.affiliate_disclosure_service import AffiliateDisclosureService
from app.services.affiliate_reporting_service import AffiliateReportingService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def test_seeded_report_has_clicks_ctr_and_buckets() -> None:
    repo = InMemoryAffiliateRepository(seed=True)
    service = AffiliateReportingService(
        repo, impression_store=repo, clock=lambda: FIXED_NOW, id_factory=lambda: "1"
    )
    report = service.build_report()
    assert report.total_clicks > 0
    assert report.impressions > 0
    assert report.ctr > 0
    assert report.by_merchant
    assert report.by_product
    assert report.by_category
    assert report.top_converting_merchants
    assert report.simulated is True
    assert "Demo" in report.disclaimer or "demo" in report.disclaimer.lower()


def test_aggregator_conversion_rate() -> None:
    clicks = [
        AffiliateClick(
            click_id="c1",
            user_id=None,
            session_id=None,
            merchant_id="m1",
            product_id="p1",
            timestamp=FIXED_NOW,
            device=None,
            country=None,
            campaign_id=None,
            source=ClickSource.DIRECT_LINK,
            referrer=None,
            conversion_status=ConversionStatus.CONVERTED,
            revenue=10.0,
            product_name="A",
            category="phones",
            marketplace=MarketplacePlaceholder.SHOPEE,
            estimated_commission=1.0,
        ),
        AffiliateClick(
            click_id="c2",
            user_id=None,
            session_id=None,
            merchant_id="m1",
            product_id="p1",
            timestamp=FIXED_NOW,
            device=None,
            country=None,
            campaign_id=None,
            source=ClickSource.DIRECT_LINK,
            referrer=None,
            conversion_status=ConversionStatus.CLICKED,
            revenue=0.0,
            product_name="A",
            category="phones",
            marketplace=MarketplacePlaceholder.SHOPEE,
            estimated_commission=1.0,
        ),
    ]
    report = aggregate_revenue_report(
        clicks,
        report_id="r1",
        generated_at=FIXED_NOW,
        impressions=10,
    )
    assert report.total_clicks == 2
    assert report.total_conversions == 1
    assert report.conversion_rate == 0.5
    assert report.ctr == 0.2


def test_disclosure_resolve_includes_ftc_placeholder() -> None:
    repo = InMemoryAffiliateRepository(seed=True)
    service = AffiliateDisclosureService(repo, clock=lambda: FIXED_NOW, id_factory=lambda: "1")
    resolved = service.resolve(region="US", merchant_id="merchant-amazon-us")
    assert resolved["combined_text"]
    assert resolved["ftc_placeholder"] is True
    types = {d.disclosure_type for d in resolved["disclosures"]}
    assert "affiliate_general" in types
    assert "ftc" in types
    assert "merchant" in types


def test_regional_disclosure_hook() -> None:
    repo = InMemoryAffiliateRepository(seed=True)
    service = AffiliateDisclosureService(repo)
    resolved = service.resolve(region="PH", include_ftc=False)
    types = {d.disclosure_type for d in resolved["disclosures"]}
    assert "regional" in types
