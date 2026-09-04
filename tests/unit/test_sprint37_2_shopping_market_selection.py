"""Sprint 37.2 — shopping market selection + coverage disclosure."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.location import DeliveryContext, context_from_manual
from app.consumer.pages import render_page
from app.consumer.presentation import build_page_view
from app.consumer.pricing import format_money
from app.consumer.shopping_market import (
    SHOPPING_MARKET_COOKIE,
    parse_shopping_market_cookie,
    set_shopping_market_cookie,
    shopping_market_from_cookie,
)
from app.core.dependencies import get_db, get_shopping_decision_snapshot_repository
from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.main import create_app
from app.market.completeness import mixed_currency_blocks_compare
from app.market.context import INTENDED_FIRST_MARKET_COUNTRY, intended_ph_product_defaults
from app.market.coverage import (
    PH_PREPARING_COVERAGE_DISCLOSURE,
    assess_shopping_coverage,
    connector_invocation_eligible,
    plan_authorized_research_if_coverage_allows,
)
from app.market.invalidation import invalidate_for_destination_change
from app.market.selection import (
    PRODUCT_FACING_SHOPPING_MARKETS,
    ShoppingMarketValidationError,
    intended_default_shopping_market,
    selected_shopping_market_from_code,
    trusted_market_from_selected,
)
from app.market.support import (
    production_certified_shopping_markets,
    shopping_markets_for_tests,
)
from app.research.registry import production_research_provider_registry
from httpx import ASGITransport, AsyncClient

from tests.unit.test_canonical_uuid_consumer_presentation import (
    DECISION_ID,
    START,
    _attrs,
    _bind,
    _economics_snapshot,
)
from tests.unit.test_phase_29_4c_propose_research import _owner, _service
from tests.unit.test_sprint31_research_execution_router import CONVERSATION_ID


@pytest.fixture()
def uuid_snapshots() -> InMemoryDecisionSnapshotRepository:
    return InMemoryDecisionSnapshotRepository(clock=lambda: START)


@pytest.fixture()
async def uuid_client(
    mock_db_session: AsyncMock,
    uuid_snapshots: InMemoryDecisionSnapshotRepository,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shopping_decision_snapshot_repository] = lambda: uuid_snapshots
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def test_selected_ph_persists_and_default_is_not_certification() -> None:
    missing = shopping_market_from_cookie(None)
    assert missing.country_code == INTENDED_FIRST_MARKET_COUNTRY == "PH"
    assert missing.origin == "intended_default"
    assert missing.to_dict()["shopping_market_certified"] is False
    explicit = selected_shopping_market_from_code("ph")
    assert explicit.country_code == "PH"
    assert explicit.origin == "explicit"
    payload = explicit.to_cookie_payload()
    assert payload == {"country_code": "PH"}
    restored = parse_shopping_market_cookie('{"country_code":"PH"}')
    assert restored is not None
    assert restored.country_code == "PH"
    assert restored.origin == "explicit"


def test_invalid_country_code_is_rejected() -> None:
    with pytest.raises(ShoppingMarketValidationError):
        selected_shopping_market_from_code("XX")
    with pytest.raises(ShoppingMarketValidationError):
        selected_shopping_market_from_code("UK")
    with pytest.raises(ShoppingMarketValidationError):
        selected_shopping_market_from_code("Philippines")
    assert parse_shopping_market_cookie('{"country_code":"XX"}') is None
    assert parse_shopping_market_cookie("not-json") is None
    assert shopping_market_from_cookie('{"country_code":"XX"}').origin == "intended_default"


def test_shopping_market_is_not_delivery_destination() -> None:
    selected = intended_default_shopping_market()
    delivery = context_from_manual("Cebu City", "6000")
    assert selected.country_code == "PH"
    assert delivery.city == "Cebu City"
    assert "country" not in delivery.to_cookie_payload()
    assert "city" not in selected.to_cookie_payload()


def test_selected_ph_with_empty_catalog_is_unsupported() -> None:
    coverage = assess_shopping_coverage(intended_default_shopping_market())
    assert production_certified_shopping_markets().to_tuple() == ()
    assert coverage.certified is False
    assert coverage.coverage_available is False
    assert coverage.connector_invocation_eligible is False
    assert coverage.reason == "no_certified_shopping_market"
    assert coverage.disclosure == PH_PREPARING_COVERAGE_DISCLOSURE
    assert "live PH" not in coverage.disclosure.lower()
    assert "Shopee" not in coverage.disclosure


def test_account_currency_and_affiliate_cannot_certify_ph() -> None:
    coverage = assess_shopping_coverage(
        selected_shopping_market_from_code("PH"),
        account_country="PH",
        display_currency="PHP",
        affiliate_available=True,
        delivery_country="PH",
    )
    assert coverage.certified is False
    assert coverage.connector_invocation_eligible is False
    assert (
        connector_invocation_eligible(
            intended_default_shopping_market(),
            account_country="PH",
            display_currency="PHP",
            affiliate_available=True,
        )
        is False
    )


def test_test_catalog_certification_does_not_change_production() -> None:
    tests = shopping_markets_for_tests({"PH"})
    covered = assess_shopping_coverage(intended_default_shopping_market(), catalog=tests)
    assert covered.certified is True
    assert production_certified_shopping_markets().is_certified("PH") is False
    assert frozenset({"PH"}) == PRODUCT_FACING_SHOPPING_MARKETS


def test_unsupported_market_cannot_plan_connector_invocation() -> None:
    result = plan_authorized_research_if_coverage_allows(
        None,
        owner=_owner(),
        conversation_id=CONVERSATION_ID,
        decision_id=DECISION_ID,
        canonical_context_version=1,
        registry=production_research_provider_registry(),
        selected=intended_default_shopping_market(),
    )
    assert result.planned is False
    assert result.reason == "unsupported_shopping_market"
    assert result.plan is None


def test_us_selection_is_not_switched_to_ph() -> None:
    selected = selected_shopping_market_from_code("US")
    coverage = assess_shopping_coverage(selected)
    assert selected.country_code == "US"
    assert coverage.selected.country_code == "US"
    assert coverage.certified is False
    assert coverage.disclosure != PH_PREPARING_COVERAGE_DISCLOSURE
    assert "not yet available" in coverage.disclosure


def test_trusted_market_from_selection_is_not_certification() -> None:
    trusted = trusted_market_from_selected(intended_default_shopping_market())
    assert trusted.country_code == "PH"
    assert trusted.source == "server_trusted"
    assert production_certified_shopping_markets().is_certified(trusted.country_code) is False


def test_no_fx_when_ph_is_selected() -> None:
    assert intended_ph_product_defaults().display_currency == "PHP"
    assert format_money(1299, "USD") == "1,299 USD"
    assert "₱" not in format_money(1299, "USD")
    assert mixed_currency_blocks_compare("USD", "PHP") is True


def test_destination_semantics_remain_from_37_1() -> None:
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    previous = intended_ph_product_defaults(delivery=context_from_manual("Taguig City", "1630"))
    current = intended_ph_product_defaults(delivery=context_from_manual("Cebu City", "6000"))
    result = invalidate_for_destination_change(previous, current)
    assert result.live_reevaluation_attempted is False
    assert result.piqscore_rewritten is False
    assert result.recommendation_rewritten is False
    assert previous.trusted_market is not None
    assert previous.trusted_market.country_code == "PH"


def test_cookie_rejects_location_fields() -> None:
    leaked = parse_shopping_market_cookie(
        '{"country_code":"PH","city":"Taguig City","latitude":14.5,"street":"1 Main"}'
    )
    assert leaked is None
    assert (
        shopping_market_from_cookie('{"country_code":"PH","history":["x"]}').origin
        == "intended_default"
    )


def test_fixture_page_discloses_uncertified_coverage() -> None:
    view = build_page_view(
        decision_id="headphones-standard",
        page="results",
        location=DeliveryContext(),
        selected_market=intended_default_shopping_market(),
    )
    html = render_page(view)
    assert view.presentation_mode == "fixture"
    assert view.shopping_market_certified is False
    assert view.shopping_coverage_available is False
    assert view.connector_invocation_eligible is False
    assert view.selected_shopping_market == "PH"
    assert view.shopping_market_origin == "intended_default"
    assert "not certified shopping coverage" in (view.shopping_coverage_disclosure or "").lower()
    assert 'data-shopping-coverage-available="false"' in html
    assert 'data-selected-shopping-market="PH"' in html
    assert "live PH coverage" not in html.lower()
    assert "We search Philippine marketplaces" not in html
    assert "Shopee is supported" not in html


def test_canonical_session_market_does_not_rewrite_delivery() -> None:
    snapshot = _economics_snapshot()
    view = page_view_from_snapshot(
        snapshot,
        page="results",
        session_location=DeliveryContext(city="Cebu City", postal_code="6000", source="manual"),
        session_shopping_market=selected_shopping_market_from_code("PH"),
    )
    assert view.location.city == "Taguig City"
    assert view.selected_shopping_market == "PH"
    assert view.shopping_market_certified is False
    assert view.connector_invocation_eligible is False
    assert view.destination_reevaluation_required is True
    assert view.best_piq.economics.dominant_amount == 18990


def test_propose_research_discloses_unsupported_market() -> None:
    service, _, _, snapshot = _service()
    response = service.handle(
        {"query": "What about AirPods Max?", "decision_id": snapshot.decision_id},
        owner=snapshot.owner,
        snapshot=snapshot,
        selected_market=intended_default_shopping_market(),
    )
    assert response is not None
    assert response.processing["action"] == "propose_research"
    assert response.processing["execution_started"] is False
    assert response.processing["research_executed"] is False
    assert response.processing["connector_invocation_eligible"] is False
    assert response.processing["shopping_market_certified"] is False
    assert response.processing["selected_shopping_market"] == "PH"
    assert response.processing["shopping_coverage_reason"] == "no_certified_shopping_market"


@pytest.mark.asyncio
async def test_shopping_market_cookie_persists_without_rewriting_delivery(
    client: AsyncClient,
) -> None:
    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Taguig City",
            "postal_code": "1630",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=False,
    )
    saved = await client.get(
        "/consumer/shopping-market",
        params={
            "country_code": "PH",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert SHOPPING_MARKET_COOKIE in saved.cookies
    page = await client.get("/results/headphones-standard")
    assert _attrs(page.text, "selected-shopping-market") == "PH"
    assert _attrs(page.text, "shopping-market-origin") == "explicit"
    assert _attrs(page.text, "shopping-coverage-available") == "false"
    assert _attrs(page.text, "shopping-market-certified") == "false"
    assert _attrs(page.text, "connector-invocation-eligible") == "false"
    assert "Delivering to Taguig City 1630" in page.text
    assert "preparing shopping-source coverage for the Philippines" in page.text


@pytest.mark.asyncio
async def test_invalid_market_post_does_not_persist(client: AsyncClient) -> None:
    response = await client.get(
        "/consumer/shopping-market",
        params={
            "country_code": "XX",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert SHOPPING_MARKET_COOKIE not in response.cookies
    page = await client.get("/results/headphones-standard")
    assert _attrs(page.text, "shopping-market-origin") == "intended_default"
    assert _attrs(page.text, "selected-shopping-market") == "PH"


@pytest.mark.asyncio
async def test_delivery_change_does_not_change_shopping_market(client: AsyncClient) -> None:
    await client.get(
        "/consumer/shopping-market",
        params={
            "country_code": "PH",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=False,
    )
    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Davao City",
            "postal_code": "8000",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=True,
    )
    page = await client.get("/results/headphones-standard")
    assert "Delivering to Davao City 8000" in page.text
    assert _attrs(page.text, "selected-shopping-market") == "PH"
    assert _attrs(page.text, "shopping-market-origin") == "explicit"


@pytest.mark.asyncio
async def test_market_change_does_not_rewrite_delivery(client: AsyncClient) -> None:
    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Cebu City",
            "postal_code": "6000",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=True,
    )
    await client.get(
        "/consumer/shopping-market",
        params={
            "country_code": "PH",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=False,
    )
    page = await client.get("/results/headphones-standard")
    assert "Delivering to Cebu City 6000" in page.text
    assert _attrs(page.text, "selected-shopping-market") == "PH"


@pytest.mark.asyncio
async def test_canonical_uuid_page_discloses_uncertified_selected_market(
    uuid_client: AsyncClient,
    uuid_snapshots,
) -> None:
    snapshot = _economics_snapshot()
    uuid_snapshots.add(snapshot)
    _bind(uuid_client, snapshot.owner)
    page = await uuid_client.get(f"/results/{DECISION_ID}")
    assert page.status_code == 200
    assert _attrs(page.text, "presentation-mode") == "canonical"
    assert _attrs(page.text, "selected-shopping-market") == "PH"
    assert _attrs(page.text, "shopping-coverage-available") == "false"
    assert _attrs(page.text, "shopping-market-certified") == "false"
    assert "18,990" in page.text
    assert "live PH coverage" not in page.text.lower()


class _CookieSink:
    def __init__(self) -> None:
        self.cookies: dict[str, str] = {}

    def set_cookie(self, name: str, value: str, **_kwargs: object) -> None:
        self.cookies[name] = value


def test_set_cookie_stores_iso_code_only() -> None:
    sink = _CookieSink()
    set_shopping_market_cookie(sink, selected_shopping_market_from_code("PH"))  # type: ignore[arg-type]
    raw = sink.cookies[SHOPPING_MARKET_COOKIE]
    assert raw == '{"country_code":"PH"}'
    assert "street" not in raw
    assert "latitude" not in raw
