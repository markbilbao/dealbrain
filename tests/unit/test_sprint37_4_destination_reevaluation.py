"""Sprint 37.4 — destination re-evaluation readiness and effective-cost honesty."""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.consumer.canonical_presentation import (
    destination_assessment_from_snapshot,
    page_view_from_snapshot,
)
from app.consumer.location import DeliveryContext, context_from_manual, skipped_context
from app.consumer.pages import render_page
from app.consumer.pricing import (
    MoneyComponent,
    evaluate_offer_total,
    select_price_state,
    shipping_display,
)
from app.core.dependencies import get_db, get_shopping_decision_snapshot_repository
from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.main import create_app
from app.market.completeness import select_dominant_price_state
from app.market.context import compose_market_context, intended_ph_product_defaults
from app.market.destination_reevaluation import (
    DESTINATION_INSENSITIVE_DISCLOSURE,
    HISTORICAL_COST_DISCLOSURE,
    REEVALUATION_UNAVAILABLE_DISCLOSURE,
    assess_destination_reevaluation,
    economics_are_destination_insensitive,
    live_destination_reevaluation_available,
)
from app.market.invalidation import (
    assert_destination_reevaluation_not_implemented,
    destination_declaration_changed,
    invalidate_for_destination_change,
)
from app.market.support import production_certified_shopping_markets
from app.services.canonical_offer_economics import attach_offer_economics, capture_offer_economics
from httpx import ASGITransport, AsyncClient

from tests.unit.test_canonical_uuid_consumer_presentation import (
    DECISION_ID,
    START,
    _attrs,
    _bind,
    _econ,
    _economics_snapshot,
    _owner,
)
from tests.unit.test_canonical_uuid_consumer_presentation import (
    _money as _uuid_money,
)

ROOT = Path(__file__).resolve().parents[2]


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


def _market(delivery: DeliveryContext):
    return intended_ph_product_defaults(delivery=delivery)


def _taguig() -> DeliveryContext:
    return context_from_manual("Taguig City", "1630")


def _cebu() -> DeliveryContext:
    return context_from_manual("Cebu City", "6000")


def _ship(status: str, amount: float | None) -> MoneyComponent:
    return MoneyComponent(
        kind="shipping",
        label="Shipping",
        amount=amount,
        currency="PHP",
        status=status,  # type: ignore[arg-type]
    )


def _digital_snapshot(**kwargs):
    base = _economics_snapshot(**kwargs)
    offers = (
        capture_offer_economics(
            offer_id="offer-digital-sony",
            product_id=base.evaluated_products[0].product_id,
            listing=_uuid_money("listing", 19990),
            shipping=_uuid_money("shipping", None, "not_applicable"),
            taxes=_uuid_money("tax", None, "not_applicable"),
            price_state="final_effective_cost",
            dominant_amount=19990,
            merchant="Digital Merchant",
            voucher=None,
            import_charges=None,
            delivery=base.delivery_context,
        ),
        capture_offer_economics(
            offer_id="offer-digital-bose",
            product_id=base.evaluated_products[1].product_id,
            listing=_uuid_money("listing", 18990),
            shipping=_uuid_money("shipping", None, "not_applicable"),
            taxes=_uuid_money("tax", None, "not_applicable"),
            price_state="final_effective_cost",
            dominant_amount=18990,
            merchant="Other Digital",
            voucher=None,
            import_charges=None,
            delivery=base.delivery_context,
        ),
    )
    return attach_offer_economics(base, offers, delivery=base.delivery_context)


def _international_missing_import_snapshot(**kwargs):
    base = _economics_snapshot(**kwargs)
    offers = (
        capture_offer_economics(
            offer_id="offer-intl-sony",
            product_id=base.evaluated_products[0].product_id,
            listing=_uuid_money("listing", 19990),
            shipping=_uuid_money("shipping", None, "not_applicable"),
            taxes=_uuid_money("tax", None, "not_applicable"),
            price_state="final_effective_cost",
            dominant_amount=19990,
            merchant="International Merchant",
            voucher=None,
            import_charges=None,
            international=True,
            delivery=base.delivery_context,
        ),
    )
    snapshot = attach_offer_economics(base, offers, delivery=base.delivery_context)
    assert snapshot.offer_economics[0].international is True
    assert snapshot.offer_economics[0].import_charges is None
    return snapshot


def test_same_normalized_destination_does_not_invalidate() -> None:
    previous = _market(context_from_manual("Cebu City", None))
    current = _market(context_from_manual("cebu city", None))
    result = invalidate_for_destination_change(previous, current)
    assert previous.destination_key == current.destination_key == "cebu-city"
    assert result.destination_changed is False
    assert result.reevaluation_required is False
    assert result.reevaluation_status == "not_required"
    assert result.destination_sensitive_economics_stale is False
    assert result.live_reevaluation_attempted is False


def test_different_city_requires_unavailable_reevaluation() -> None:
    result = assess_destination_reevaluation(_market(_taguig()), _market(_cebu()))
    assert result.destination_changed is True
    assert result.reevaluation_required is True
    assert result.reevaluation_status == "required_unavailable"
    assert result.destination_sensitive_economics_stale is True
    assert result.live_evidence_path_available is False
    assert result.live_reevaluation_attempted is False
    assert result.manufactured_shipping is False
    assert result.previous_destination_shipping_reused is False
    assert result.prior_canonical_decision_preserved is True
    assert result.disclosure == REEVALUATION_UNAVAILABLE_DISCLOSURE
    assert result.historical_cost_disclosure == HISTORICAL_COST_DISCLOSURE


def test_postal_change_that_can_affect_shipping_requires_reevaluation() -> None:
    previous = _market(context_from_manual("Taguig City", "1630"))
    current = _market(context_from_manual("Taguig City", "1634"))
    result = invalidate_for_destination_change(previous, current)
    assert previous.destination_key != current.destination_key
    assert result.reevaluation_required is True
    assert result.reevaluation_status == "required_unavailable"


def test_postal_removed_requires_reevaluation() -> None:
    previous = _market(context_from_manual("Taguig City", "1630"))
    current = _market(context_from_manual("Taguig City", None))
    result = invalidate_for_destination_change(previous, current)
    assert result.destination_changed is True
    assert result.reevaluation_required is True


def test_skipped_to_known_requires_reevaluation() -> None:
    result = assess_destination_reevaluation(_market(skipped_context()), _market(_cebu()))
    assert result.destination_changed is True
    assert result.reevaluation_required is True
    assert result.reevaluation_status == "required_unavailable"


def test_known_to_skipped_requires_reevaluation() -> None:
    result = assess_destination_reevaluation(_market(_taguig()), _market(skipped_context()))
    assert result.destination_changed is True
    assert result.reevaluation_required is True


def test_absent_to_known_requires_reevaluation() -> None:
    result = assess_destination_reevaluation(
        compose_market_context(trusted_market=None),
        _market(_cebu()),
    )
    assert result.destination_changed is True
    assert result.reevaluation_required is True


def test_absent_session_is_not_a_shopper_destination_change() -> None:
    previous = _market(_taguig())
    current = compose_market_context(trusted_market=previous.trusted_market)
    assert current.destination_state == "absent"
    assert destination_declaration_changed(previous, current) is False
    result = invalidate_for_destination_change(previous, current)
    assert result.destination_changed is False
    assert result.reevaluation_required is False


def test_destination_insensitive_economics_remain_usable() -> None:
    snapshot = _digital_snapshot()
    assert economics_are_destination_insensitive(snapshot.offer_economics) is True
    result = assess_destination_reevaluation(
        _market(_taguig()),
        _market(_cebu()),
        offer_economics=snapshot.offer_economics,
    )
    assert result.destination_changed is True
    assert result.destination_insensitive_economics is True
    assert result.reevaluation_required is False
    assert result.reevaluation_status == "not_required"
    assert result.destination_sensitive_economics_stale is False
    assert result.disclosure == DESTINATION_INSENSITIVE_DISCLOSURE
    view = page_view_from_snapshot(snapshot, page="results", session_location=_cebu())
    assert view.destination_reevaluation_required is False
    assert view.destination_reevaluation_status == "not_required"
    assert view.best_piq.economics.dominant_amount == 19990
    assert view.best_piq.economics.shipping.status == "not_applicable"
    assert view.recalculating is False


def test_international_missing_import_is_not_destination_insensitive() -> None:
    snapshot = _international_missing_import_snapshot()
    offer = snapshot.offer_economics[0]
    assert offer.international is True
    assert offer.shipping.status == "not_applicable"
    assert offer.taxes.status == "not_applicable"
    assert offer.import_charges is None
    assert economics_are_destination_insensitive(snapshot.offer_economics) is False
    result = assess_destination_reevaluation(
        _market(_taguig()),
        _market(_cebu()),
        offer_economics=snapshot.offer_economics,
    )
    assert result.destination_changed is True
    assert result.destination_insensitive_economics is False
    assert result.reevaluation_required is True
    assert result.reevaluation_status == "required_unavailable"
    assert result.manufactured_shipping is False
    assert result.live_reevaluation_attempted is False
    assert offer.import_charges is None


def test_destination_specific_shipping_is_not_reused_for_new_destination() -> None:
    snapshot = _economics_snapshot()
    assessment = destination_assessment_from_snapshot(snapshot, _cebu())
    assert assessment.previous_destination_shipping_reused is False
    assert assessment.manufactured_shipping is False
    view = page_view_from_snapshot(snapshot, page="results", session_location=_cebu())
    html = render_page(view)
    assert "Shipping to Taguig City" in html
    assert "Shipping to Cebu City 6000" not in html
    assert view.best_piq.economics.shipping.amount == 0
    assert view.best_piq.economics.shipping.status == "verified"
    assert REEVALUATION_UNAVAILABLE_DISCLOSURE in html
    assert "not this location's current effective cost" in html


def test_unknown_shipping_remains_unknown_and_never_free() -> None:
    unknown = _ship("unknown", None)
    zero_unknown = _ship("unknown", 0.0)
    estimated_zero = _ship("estimated", 0.0)
    verified_zero = _ship("verified", 0.0)
    assert shipping_display(unknown) == "Not verified"
    assert shipping_display(zero_unknown) == "Not verified"
    assert "FREE" not in shipping_display(unknown)
    assert "₱0" not in shipping_display(unknown)
    assert "FREE" not in shipping_display(zero_unknown)
    assert shipping_display(estimated_zero) != "FREE"
    assert shipping_display(verified_zero) == "FREE"
    listing = MoneyComponent(kind="listing", label="Listing", amount=10000, status="verified")
    total = evaluate_offer_total(listing, (unknown,))
    assert total == 10000
    state = select_price_state(
        shipping=unknown,
        taxes=MoneyComponent(kind="tax", label="Tax", amount=None, status="not_applicable"),
        import_charges=None,
        savings=(),
        international=False,
        location_known=True,
        shipping_material=True,
    )
    assert state == "price_before_shipping"
    stale = select_dominant_price_state(
        market=_market(_cebu()),
        shipping=verified_zero,
        taxes=MoneyComponent(kind="tax", label="Tax", amount=None, status="not_applicable"),
        import_charges=None,
        savings=(),
        international=False,
        shipping_material=True,
        destination_sensitive_stale=True,
    )
    assert stale == "price_before_shipping"
    assert stale != "final_effective_cost"


def test_unverified_voucher_stays_excluded_after_destination_change() -> None:
    snapshot = attach_offer_economics(
        _economics_snapshot(),
        (
            _econ(
                _economics_snapshot().evaluated_products[0].product_id,
                listing=19990,
                voucher=-1500,
                voucher_status="unverified",
                shipping=0,
                price_state="potential_checkout_price",
                dominant=19990,
                merchant="Captured Merchant",
                provenance="captured-offer://merchant/sony",
            ),
        ),
        delivery=_economics_snapshot().delivery_context,
    )
    voucher = snapshot.offer_economics[0].voucher
    assert voucher is not None
    assert voucher.status == "unverified"
    assert voucher.applied is False
    view = page_view_from_snapshot(snapshot, page="results", session_location=_cebu())
    assert view.best_piq.economics.voucher is not None
    assert view.best_piq.economics.voucher.status == "unverified"
    assert view.best_piq.economics.voucher.applies is False
    assert view.best_piq.economics.dominant_amount == 19990
    html = render_page(view)
    assert "Not applied" in html


def test_canonical_decision_and_piqscores_remain_immutable() -> None:
    snapshot = _economics_snapshot()
    digest = snapshot.content_sha256
    scores = tuple(item.canonical_piqscore.value for item in snapshot.evaluated_products)
    reco = snapshot.recommendation.best_piq_product_id
    view = page_view_from_snapshot(snapshot, page="results", session_location=_cebu())
    assessment = assess_destination_reevaluation(
        _market(_taguig()),
        _market(_cebu()),
        offer_economics=snapshot.offer_economics,
    )
    assert snapshot.content_sha256 == digest
    assert tuple(item.canonical_piqscore.value for item in snapshot.evaluated_products) == scores
    assert snapshot.recommendation.best_piq_product_id == reco
    assert view.best_piq.piqscore.value == scores[0]
    assert view.canonical_piqscore_set_sha256 == snapshot.canonical_piqscore_set_sha256
    assert view.recommendation_snapshot_sha256 == snapshot.recommendation.snapshot_sha256
    assert view.recalculating is False
    assert assessment.prior_canonical_decision_preserved is True
    assert assessment.invalidation.piqscore_rewritten is False
    assert assessment.invalidation.recommendation_rewritten is False
    assert assessment.invalidation.canonical_snapshot_rewritten is False


def test_unavailable_reevaluation_preserves_prior_decision() -> None:
    snapshot = _economics_snapshot()
    assessment = destination_assessment_from_snapshot(snapshot, skipped_context())
    assert assessment.reevaluation_status == "required_unavailable"
    assert assessment.prior_canonical_decision_preserved is True
    view = page_view_from_snapshot(snapshot, page="results", session_location=skipped_context())
    assert view.best_piq.product_id == snapshot.recommendation.best_piq_product_id
    assert view.best_piq.economics.dominant_amount == 18990
    assert view.location.city == "Taguig City"
    assert view.recalculating is False
    html = render_page(view)
    assert REEVALUATION_UNAVAILABLE_DISCLOSURE in html
    assert "Updating costs" not in html


def test_live_flag_and_handoff_remain_unimplemented() -> None:
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert live_destination_reevaluation_available() is False
    assert_destination_reevaluation_not_implemented()
    assert production_certified_shopping_markets().to_tuple() == ()
    source = inspect.getsource(__import__("app.market.destination_reevaluation", fromlist=["*"]))
    assert "attempt_certified_destination_reevaluation" not in source


def test_assessment_works_independently_of_live_execution_guard() -> None:
    snapshot = _economics_snapshot()
    digest = snapshot.content_sha256
    with (
        patch("app.market.destination_reevaluation.DESTINATION_REEVALUATION_IMPLEMENTED", True),
        patch("app.market.invalidation.DESTINATION_REEVALUATION_IMPLEMENTED", True),
    ):
        result = assess_destination_reevaluation(
            _market(_taguig()),
            _market(_cebu()),
            offer_economics=snapshot.offer_economics,
        )
        invalidation = invalidate_for_destination_change(
            _market(_taguig()),
            _market(_cebu()),
            offer_economics=snapshot.offer_economics,
        )
        with pytest.raises(RuntimeError, match="must remain False"):
            assert_destination_reevaluation_not_implemented()
    assert result.reevaluation_required is True
    assert result.reevaluation_status == "required_unavailable"
    assert result.live_reevaluation_attempted is False
    assert result.manufactured_shipping is False
    assert result.prior_canonical_decision_preserved is True
    assert invalidation.live_reevaluation_attempted is False
    assert invalidation.canonical_snapshot_rewritten is False
    assert snapshot.content_sha256 == digest
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert live_destination_reevaluation_available() is False
    assert_destination_reevaluation_not_implemented()


def test_affiliate_neutrality_in_destination_logic() -> None:
    for module_name in (
        "app.market.destination_reevaluation",
        "app.market.invalidation",
    ):
        source = inspect.getsource(__import__(module_name, fromlist=["*"]))
        assert "affiliate" not in source.lower()
        assert "commission" not in source.lower()
    first = assess_destination_reevaluation(_market(_taguig()), _market(_cebu()))
    second = assess_destination_reevaluation(_market(_taguig()), _market(_cebu()))
    assert first.to_dict() == second.to_dict()
    assert "affiliate" not in first.to_dict()


def test_no_client_side_repricing_or_fixture_as_live() -> None:
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "shipping" not in js.lower()
    assert "effective" not in js.lower()
    assert "piqscore" not in js.lower()
    assert "dominant_amount" not in js
    presentation = inspect.getsource(
        __import__("app.consumer.canonical_presentation", fromlist=["*"])
    )
    assert "recalculating=False" in presentation
    assert "fx_quote_for_tests" not in presentation
    api = inspect.getsource(__import__("app.api.consumer", fromlist=["*"]))
    assert "attempt_certified_destination_reevaluation" not in api
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False


def test_incomplete_offer_does_not_gain_zero_shipping_advantage() -> None:
    unknown = _ship("unknown", None)
    listing_a = MoneyComponent(kind="listing", label="Listing", amount=10000, status="verified")
    listing_b = MoneyComponent(kind="listing", label="Listing", amount=10000, status="verified")
    verified = _ship("verified", 250)
    total_unknown = evaluate_offer_total(listing_a, (unknown,))
    total_known = evaluate_offer_total(listing_b, (verified,))
    assert total_unknown == 10000
    assert total_known == 10250
    unknown_state = select_price_state(
        shipping=unknown,
        taxes=MoneyComponent(kind="tax", label="Tax", amount=None, status="not_applicable"),
        import_charges=None,
        savings=(),
        international=False,
        location_known=True,
        shipping_material=True,
    )
    known_state = select_price_state(
        shipping=verified,
        taxes=MoneyComponent(kind="tax", label="Tax", amount=None, status="not_applicable"),
        import_charges=None,
        savings=(),
        international=False,
        location_known=True,
        shipping_material=True,
    )
    assert unknown_state == "price_before_shipping"
    assert known_state == "final_effective_cost"
    assert shipping_display(unknown) != "FREE"
    assert shipping_display(unknown) != "₱0"


@pytest.mark.asyncio
async def test_results_compare_why_show_unavailable_disclosure(
    uuid_client: AsyncClient,
    uuid_snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshot = _economics_snapshot()
    uuid_snapshots.add(snapshot)
    _bind(uuid_client, snapshot.owner)
    await uuid_client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Cebu City",
            "postal_code": "6000",
            "decision_id": DECISION_ID,
            "next": f"/results/{DECISION_ID}",
        },
        follow_redirects=False,
    )
    for path in (
        f"/results/{DECISION_ID}",
        f"/compare/{DECISION_ID}",
        f"/why-best-piq/{DECISION_ID}",
    ):
        page = await uuid_client.get(path)
        assert page.status_code == 200
        assert REEVALUATION_UNAVAILABLE_DISCLOSURE in page.text
        assert HISTORICAL_COST_DISCLOSURE in page.text
        assert _attrs(page.text, "destination-reevaluation-required") == "true"
        assert _attrs(page.text, "destination-reevaluation-status") == "required_unavailable"
        assert _attrs(page.text, "updated-delivery-cost-available") == "false"
        assert _attrs(page.text, "presentation-mode") == "canonical"
        assert "Updating costs" not in page.text
        assert "18,990" in page.text
        assert "Shipping to Taguig City" in page.text


@pytest.mark.asyncio
async def test_destination_reevaluation_endpoint_owner_authorization(
    uuid_client: AsyncClient,
    uuid_snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshot = _economics_snapshot()
    uuid_snapshots.add(snapshot)
    path = f"/consumer/decisions/{DECISION_ID}/destination-reevaluation"
    missing = await uuid_client.get(path)
    assert missing.status_code == 404
    _bind(uuid_client, _owner("other-guest"))
    forbidden = await uuid_client.get(path)
    assert forbidden.status_code == 404
    _bind(uuid_client, snapshot.owner)
    await uuid_client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Cebu City",
            "postal_code": "6000",
            "decision_id": DECISION_ID,
            "next": f"/results/{DECISION_ID}",
        },
        follow_redirects=False,
    )
    ok = await uuid_client.get(path)
    assert ok.status_code == 200
    body = ok.json()
    assert body["decision_id"] == DECISION_ID
    assert body["reevaluation_status"] == "required_unavailable"
    assert body["reevaluation_required"] is True
    assert body["live_reevaluation_attempted"] is False
    assert body["manufactured_shipping"] is False
    assert body["previous_destination_shipping_reused"] is False
    assert body["prior_canonical_decision_preserved"] is True
    assert body["canonical_snapshot_rewritten"] is False
    assert body["piqscore_rewritten"] is False
    assert body["recommendation_rewritten"] is False
    assert body["destination_reevaluation_implemented"] is False
    assert body["canonical_content_sha256"] == snapshot.content_sha256
    assert body["disclosure"] == REEVALUATION_UNAVAILABLE_DISCLOSURE
    assert "affiliate" not in body
    assert (
        snapshot.content_sha256
        == uuid_snapshots.get_latest_for_owner(DECISION_ID, snapshot.owner).content_sha256
    )


@pytest.mark.asyncio
async def test_same_destination_endpoint_does_not_require_reevaluation(
    uuid_client: AsyncClient,
    uuid_snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshot = _economics_snapshot()
    uuid_snapshots.add(snapshot)
    _bind(uuid_client, snapshot.owner)
    await uuid_client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Taguig City",
            "postal_code": "1630",
            "decision_id": DECISION_ID,
            "next": f"/results/{DECISION_ID}",
        },
        follow_redirects=False,
    )
    ok = await uuid_client.get(f"/consumer/decisions/{DECISION_ID}/destination-reevaluation")
    assert ok.status_code == 200
    body = ok.json()
    assert body["destination_changed"] is False
    assert body["reevaluation_required"] is False
    assert body["reevaluation_status"] == "not_required"
    page = await uuid_client.get(f"/results/{DECISION_ID}")
    assert REEVALUATION_UNAVAILABLE_DISCLOSURE not in page.text
    assert _attrs(page.text, "destination-reevaluation-required") == "false"
