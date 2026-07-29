"""Sprint 20 unit tests — click tracking & attribution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.affiliate.attribution.engine import AttributionEngine
from app.affiliate.memory import InMemoryAffiliateRepository
from app.domain.entities.affiliate import (
    AffiliateClick,
    AttributionModel,
    ClickSource,
    ConversionStatus,
    MarketplacePlaceholder,
)
from app.services.affiliate_tracking_service import AffiliateTrackingService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _service() -> AffiliateTrackingService:
    repo = InMemoryAffiliateRepository(seed=True)
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"{counter['n']}"

    return AffiliateTrackingService(
        repo,
        link_repository=repo,
        merchant_repository=repo,
        attribution_repository=repo,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )


def test_track_click_and_update_conversion() -> None:
    service = _service()
    click = service.track_click(
        merchant_id="merchant-shopee-ph",
        product_id="prod-1",
        product_name="Phone",
        category="smartphones",
        user_id="u1",
        session_id="s1",
        source="shopping_assistant",
        device="mobile",
        country="ph",
    )
    assert click.conversion_status is ConversionStatus.CLICKED
    assert click.country == "PH"
    updated = service.update_conversion_status(
        click.click_id,
        conversion_status="converted",
        revenue=100.0,
        estimated_commission=5.5,
    )
    assert updated.conversion_status is ConversionStatus.CONVERTED
    assert updated.revenue == 100.0


def test_track_click_from_link() -> None:
    repo = InMemoryAffiliateRepository(seed=True)
    service = AffiliateTrackingService(
        repo,
        link_repository=repo,
        merchant_repository=repo,
        attribution_repository=repo,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "x",
    )
    links = repo.list_links(limit=1)
    assert links
    click = service.track_click(link_id=links[0].link_id, source="affiliate_dashboard")
    assert click.merchant_id == links[0].merchant_id
    assert click.product_id == links[0].product_id


def test_attribution_last_and_first_click() -> None:
    engine = AttributionEngine()
    base = AffiliateClick(
        click_id="c1",
        user_id="u1",
        session_id="s1",
        merchant_id="m1",
        product_id="p1",
        timestamp=FIXED_NOW,
        device="desktop",
        country="US",
        campaign_id=None,
        source=ClickSource.DIRECT_LINK,
        referrer=None,
        conversion_status=ConversionStatus.CLICKED,
        revenue=0.0,
        marketplace=MarketplacePlaceholder.AMAZON,
        estimated_commission=1.0,
    )
    second = AffiliateClick(
        click_id="c2",
        user_id="u1",
        session_id="s1",
        merchant_id="m1",
        product_id="p1",
        timestamp=FIXED_NOW + timedelta(minutes=5),
        device="desktop",
        country="US",
        campaign_id="camp",
        source=ClickSource.SHOPPING_ASSISTANT,
        referrer=None,
        conversion_status=ConversionStatus.CLICKED,
        revenue=0.0,
        marketplace=MarketplacePlaceholder.AMAZON,
        estimated_commission=2.0,
    )
    last = engine.attribute(
        [base, second],
        model=AttributionModel.LAST_CLICK,
        attribution_id="a1",
        attributed_at=FIXED_NOW,
        revenue=50.0,
    )
    assert last.click_id == "c2"
    first = engine.attribute(
        [base, second],
        model=AttributionModel.FIRST_CLICK,
        attribution_id="a2",
        attributed_at=FIXED_NOW,
    )
    assert first.click_id == "c1"
    internal = engine.attribute(
        [base, second],
        model=AttributionModel.INTERNAL_RECOMMENDATION,
        attribution_id="a3",
        attributed_at=FIXED_NOW,
    )
    assert internal.click_id == "c2"
    direct = engine.attribute(
        [base, second],
        model=AttributionModel.DIRECT,
        attribution_id="a4",
        attributed_at=FIXED_NOW,
    )
    assert direct.click_id is None


def test_service_attribute_marks_click() -> None:
    service = _service()
    click = service.track_click(
        merchant_id="merchant-amazon-us",
        product_id="prod-airpods",
        source="shopping_assistant",
        user_id="u1",
        session_id="s1",
    )
    result = service.attribute(
        model="last_click",
        user_id="u1",
        session_id="s1",
        revenue=20.0,
        estimated_commission=0.8,
    )
    assert result.click_id == click.click_id
    updated = service.get_click(click.click_id)
    assert updated.conversion_status is ConversionStatus.ATTRIBUTED
