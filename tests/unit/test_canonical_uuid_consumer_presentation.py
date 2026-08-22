"""Canonical UUID Results / Compare / Why presentation adapter tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.consumer.location import DeliveryContext
from app.consumer.pricing import MoneyComponent, select_price_state
from app.core.dependencies import get_db, get_shopping_decision_snapshot_repository
from app.domain.entities.decision_snapshot import (
    AffiliateNeutralitySnapshot,
    CanonicalDecisionSnapshot,
    CanonicalPiqScoreSnapshot,
    CanonicalRecommendationSnapshot,
    DecisionEvidenceSnapshot,
    EvaluatedProductSnapshot,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import DecisionSnapshotIntegrityError
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.shopping_decision_snapshot_repository import (
    SqlAlchemyDecisionSnapshotRepository,
)
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.main import create_app
from app.services.answer_from_evidence import compose_evidence_answer
from app.services.canonical_offer_economics import (
    attach_offer_economics,
    capture_offer_economics,
    delivery_from_location,
)
from app.services.decision_evidence_packet import packet_from_snapshot
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000041"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000099"
SONY_ID = "sony-wh-1000xm5-canonical"
BOSE_ID = "bose-qc-ultra-canonical"
ROOT = Path(__file__).resolve().parents[2]


def _owner(principal_id: str = "guest-uuid-adapter") -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id=principal_id,
        session_id=f"session-{principal_id}",
        expires_at=START + timedelta(minutes=30),
    )


def _score(value: float, digest: str) -> CanonicalPiqScoreSnapshot:
    return CanonicalPiqScoreSnapshot(
        value=value,
        authority="canonical-piqscore-dealscore-engine",
        semantics_version="protected-existing-authority-v1",
        snapshot_sha256=digest * 64,
    )


def _base_snapshot(
    *,
    owner: ConversationOwner | None = None,
    best_id: str = SONY_ID,
    sony_score: float = 90,
    bose_score: float = 88,
) -> CanonicalDecisionSnapshot:
    alt = BOSE_ID if best_id == SONY_ID else SONY_ID
    return CanonicalDecisionSnapshot(
        decision_id=DECISION_ID,
        context_version=1,
        owner=owner or _owner(),
        evaluated_products=(
            EvaluatedProductSnapshot(
                product_id=SONY_ID,
                display_name="Sony WH-1000XM5",
                variant="black",
                canonical_piqscore=_score(sony_score, "a"),
            ),
            EvaluatedProductSnapshot(
                product_id=BOSE_ID,
                display_name="Bose QuietComfort Ultra",
                variant="black",
                canonical_piqscore=_score(bose_score, "b"),
            ),
        ),
        recommendation=CanonicalRecommendationSnapshot(
            authority="canonical-recommendation-engine",
            decision="consider",
            best_piq_product_id=best_id,
            alternative_product_ids=(alt,),
            snapshot_sha256="c" * 64,
        ),
        evidence=(
            DecisionEvidenceSnapshot(
                evidence_id="canonical-battery-sony",
                product_id=SONY_ID,
                topic="battery",
                fact="canonical battery evidence A",
                source="captured-offer://battery/sony",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="d" * 64,
            ),
            DecisionEvidenceSnapshot(
                evidence_id="canonical-battery-bose",
                product_id=BOSE_ID,
                topic="battery",
                fact="canonical battery evidence B",
                source="captured-offer://battery/bose",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="e" * 64,
            ),
        ),
        unknowns=("warranty coverage is unknown",),
        affiliate_neutrality=AffiliateNeutralitySnapshot(),
        created_at=START,
        updated_at=START,
        data_classification="canonical_decision",
    )


def _money(kind: str, amount: float | None, status: str = "verified") -> MoneyComponent:
    return MoneyComponent(
        kind=kind,  # type: ignore[arg-type]
        label=kind,
        amount=amount,
        status=status,  # type: ignore[arg-type]
        applies=status == "verified"
        if kind in {"voucher", "discount"}
        else status != "not_applicable",
    )


def _econ(
    product_id: str,
    *,
    listing: float,
    shipping: float | None,
    shipping_status: str = "verified",
    taxes: float | None = None,
    tax_status: str = "not_applicable",
    voucher: float | None = None,
    voucher_status: str = "verified",
    imports: float | None = None,
    import_status: str = "estimated",
    price_state: str,
    dominant: float | None,
    merchant: str | None,
    international: bool = False,
    provenance: str | None,
):
    return capture_offer_economics(
        offer_id=f"offer-{product_id}",
        product_id=product_id,
        listing=_money("listing", listing),
        shipping=_money("shipping", shipping, shipping_status),
        taxes=_money("tax", taxes, tax_status),
        price_state=price_state,  # type: ignore[arg-type]
        dominant_amount=dominant,
        merchant=merchant,
        voucher=_money("voucher", voucher, voucher_status) if voucher is not None else None,
        import_charges=(
            _money("import", imports, import_status)
            if imports is not None or import_status != "estimated"
            else None
        ),
        delivery=delivery_from_location(city="Taguig City", postal_code="1630", country="PH"),
        international=international,
        provenance_source=provenance,
    )


def _economics_snapshot(**kwargs) -> CanonicalDecisionSnapshot:
    return attach_offer_economics(
        _base_snapshot(**kwargs),
        (
            _econ(
                SONY_ID,
                listing=19990,
                voucher=-1000,
                shipping=0,
                price_state="final_effective_cost",
                dominant=18990,
                merchant="Captured Merchant",
                provenance="captured-offer://merchant/sony",
            ),
            _econ(
                BOSE_ID,
                listing=18990,
                shipping=0,
                price_state="final_effective_cost",
                dominant=18990,
                merchant="Other Merchant",
                provenance="captured-offer://merchant/bose",
            ),
        ),
        delivery=delivery_from_location(city="Taguig City", postal_code="1630", country="PH"),
        data_classification="canonical_decision",
    )


def _attrs(html: str, name: str) -> str:
    needle = f'data-{name}="'
    start = html.index(needle) + len(needle)
    end = html.index('"', start)
    return html[start:end]


@pytest.fixture()
def snapshots() -> InMemoryDecisionSnapshotRepository:
    return InMemoryDecisionSnapshotRepository(clock=lambda: START)


@pytest.fixture()
async def adapter_client(
    mock_db_session: AsyncMock,
    snapshots: InMemoryDecisionSnapshotRepository,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shopping_decision_snapshot_repository] = lambda: snapshots
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _bind(client: AsyncClient, owner: ConversationOwner) -> None:
    client.cookies.set(OWNER_COOKIE, owner_cookie_payload(owner))


@pytest.mark.asyncio
async def test_owned_uuid_results_compare_why_are_200(
    adapter_client: AsyncClient,
    snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshot = _economics_snapshot()
    snapshots.add(snapshot)
    _bind(adapter_client, snapshot.owner)
    for path in (
        f"/results/{DECISION_ID}",
        f"/compare/{DECISION_ID}",
        f"/why-best-piq/{DECISION_ID}",
    ):
        response = await adapter_client.get(path)
        assert response.status_code == 200
        assert _attrs(response.text, "unavailable") == "false"
        assert _attrs(response.text, "decision-id") == DECISION_ID
        assert _attrs(response.text, "presentation-mode") == "canonical"
        assert "Sony" in response.text
        assert "18,990" in response.text
        assert "Final effective cost" in response.text
        assert "Captured Merchant" in response.text
        assert "headphones-standard" not in response.text


@pytest.mark.asyncio
async def test_unauthorized_and_unknown_uuid_are_safe_unavailable(
    adapter_client: AsyncClient,
    snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshots.add(_economics_snapshot())
    _bind(adapter_client, _owner("other-guest"))
    forbidden = await adapter_client.get(f"/results/{DECISION_ID}")
    missing = await adapter_client.get(f"/results/{UNKNOWN_ID}")
    assert forbidden.status_code == 200
    assert missing.status_code == 200
    assert _attrs(forbidden.text, "unavailable") == "true"
    assert _attrs(missing.text, "unavailable") == "true"
    assert "18,990" not in forbidden.text
    assert "18,990" not in missing.text
    assert "Captured Merchant" not in forbidden.text
    assert "does not exist" not in forbidden.text.lower()
    assert "not authorized" not in forbidden.text.lower()


@pytest.mark.asyncio
async def test_tampered_snapshot_is_not_rendered(
    adapter_client: AsyncClient,
    snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshot = _economics_snapshot()
    snapshots.add(snapshot)
    mutated = replace(snapshot, unknowns=("tampered",))
    snapshots._records[(DECISION_ID, 1)] = (mutated, snapshot.content_sha256)  # noqa: SLF001
    _bind(adapter_client, snapshot.owner)
    with pytest.raises(DecisionSnapshotIntegrityError):
        snapshots.get(DECISION_ID, 1)
    page = await adapter_client.get(f"/results/{DECISION_ID}")
    assert page.status_code == 200
    assert _attrs(page.text, "unavailable") == "true"
    assert "18,990" not in page.text


@pytest.mark.asyncio
async def test_fixture_catalog_still_works_when_permitted(adapter_client: AsyncClient) -> None:
    page = await adapter_client.get("/results/headphones-standard")
    assert page.status_code == 200
    assert "WH-1000XM5" in page.text
    assert _attrs(page.text, "presentation-mode") == "fixture"


@pytest.mark.asyncio
async def test_production_fixture_id_does_not_become_canonical(
    adapter_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.consumer.mode.fixture_catalogs_permitted", lambda: False)
    page = await adapter_client.get("/results/headphones-standard")
    assert _attrs(page.text, "unavailable") == "true"
    assert "WH-1000XM5" not in page.text
    assert "18,990" not in page.text
    assert "Lazada" not in page.text


@pytest.mark.asyncio
async def test_cross_surface_consistency_and_ask(
    adapter_client: AsyncClient,
    snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshot = _economics_snapshot()
    snapshots.add(snapshot)
    _bind(adapter_client, snapshot.owner)
    pages = {}
    for name, path in (
        ("results", f"/results/{DECISION_ID}"),
        ("compare", f"/compare/{DECISION_ID}"),
        ("why", f"/why-best-piq/{DECISION_ID}"),
    ):
        pages[name] = await adapter_client.get(path)
        assert pages[name].status_code == 200
    ask = await adapter_client.post(
        "/api/v1/shopping-assistant/query",
        json={
            "query": "What price did you evaluate?",
            "decision_id": DECISION_ID,
            "surface": "results",
        },
    )
    assert ask.status_code == 200
    body = ask.json()
    for html in pages.values():
        assert _attrs(html.text, "best-piq") == SONY_ID
        assert _attrs(html.text, "price-state") == "final_effective_cost"
        assert _attrs(html.text, "decision-id") == DECISION_ID
        assert "18,990" in html.text
        assert "Taguig City 1630" in html.text
        assert html.text.count("sony-wh-1000xm5-lazada") == 0
    assert "warranty coverage is unknown" in pages["why"].text
    assert "canonical battery evidence A" in pages["why"].text
    assert "18,990" in body["answer"]
    assert "Final effective cost" in body["answer"]
    assert "/why-best-piq/" + DECISION_ID in pages["results"].text
    assert (
        f'href="/results/{DECISION_ID}"' in pages["why"].text
        or f"/results/{DECISION_ID}" in pages["why"].text
    )


@pytest.mark.parametrize(
    (
        "price_state",
        "listing",
        "shipping",
        "shipping_status",
        "imports",
        "import_status",
        "dominant",
    ),
    [
        ("final_effective_cost", 19990, 0, "verified", None, "estimated", 18990),
        ("price_before_shipping", 7499, None, "unknown", None, "estimated", 7499),
        ("estimated_landed_cost", 16500, 1800, "verified", 1950, "estimated", 20250),
        ("before_unverified_import_charges", 16500, 1800, "verified", None, "unknown", 18300),
        ("potential_checkout_price", 19990, 0, "verified", None, "estimated", 19990),
    ],
)
def test_canonical_price_states_are_not_recomputed(
    price_state: str,
    listing: float,
    shipping: float | None,
    shipping_status: str,
    imports: float | None,
    import_status: str,
    dominant: float,
) -> None:
    voucher = (
        -1000
        if price_state == "final_effective_cost"
        else (-1500 if price_state == "potential_checkout_price" else None)
    )
    voucher_status = "unverified" if price_state == "potential_checkout_price" else "verified"
    snapshot = attach_offer_economics(
        _base_snapshot(),
        (
            _econ(
                SONY_ID,
                listing=listing,
                shipping=shipping,
                shipping_status=shipping_status,
                voucher=voucher,
                voucher_status=voucher_status,
                imports=imports,
                import_status=import_status,
                price_state=price_state,
                dominant=dominant,
                merchant="Captured Merchant",
                international=price_state
                in {"estimated_landed_cost", "before_unverified_import_charges"},
                provenance="captured-offer://state",
            ),
            _econ(
                BOSE_ID,
                listing=17000,
                shipping=shipping,
                shipping_status=shipping_status,
                imports=imports,
                import_status=import_status,
                price_state=price_state,
                dominant=dominant,
                merchant="Other Merchant",
                international=price_state
                in {"estimated_landed_cost", "before_unverified_import_charges"},
                provenance="captured-offer://state-b",
            ),
        ),
        delivery=delivery_from_location(city="Taguig City", postal_code="1630"),
        data_classification="canonical_decision",
    )
    view = page_view_from_snapshot(
        snapshot,
        page="results",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.economics.dominant_state == price_state
    assert view.best_piq.economics.dominant_amount == dominant
    computed = select_price_state(
        shipping=view.best_piq.economics.shipping,
        taxes=view.best_piq.economics.taxes,
        import_charges=view.best_piq.economics.import_charges,
        savings=tuple(item for item in (view.best_piq.economics.voucher,) if item is not None),
        international=view.best_piq.economics.international,
        location_known=True,
        shipping_material=True,
    )
    if price_state == "potential_checkout_price":
        assert view.best_piq.economics.voucher is not None
        assert view.best_piq.economics.voucher.applies is False
    assert view.best_piq.economics.dominant_state == price_state
    assert view.recommendation_decision == snapshot.recommendation.decision
    _ = computed


def test_free_unknown_tax_and_estimated_import_semantics() -> None:
    view = page_view_from_snapshot(
        _economics_snapshot(),
        page="results",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.economics.shipping.amount == 0
    assert view.best_piq.economics.shipping.status == "verified"
    assert (
        "FREE" in view.best_piq.economics.breakdown_lines[2][1] or view.best_piq.compact_breakdown
    )
    unknown = attach_offer_economics(
        _base_snapshot(),
        (
            _econ(
                SONY_ID,
                listing=7499,
                shipping=None,
                shipping_status="unknown",
                taxes=None,
                tax_status="unknown",
                price_state="price_before_shipping",
                dominant=7499,
                merchant="Captured Merchant",
                provenance="captured-offer://partial",
            ),
            _econ(
                BOSE_ID,
                listing=7999,
                shipping=None,
                shipping_status="unknown",
                taxes=None,
                tax_status="unknown",
                price_state="price_before_shipping",
                dominant=7999,
                merchant="Other Merchant",
                provenance="captured-offer://partial-b",
            ),
        ),
        data_classification="canonical_decision",
    )
    unknown_view = page_view_from_snapshot(
        unknown,
        page="results",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert unknown_view.best_piq.economics.shipping.status == "unknown"
    assert unknown_view.best_piq.economics.shipping.amount is None
    assert "FREE" not in unknown_view.best_piq.compact_breakdown
    assert unknown_view.best_piq.economics.taxes.status == "unknown"
    landed = page_view_from_snapshot(
        attach_offer_economics(
            _base_snapshot(),
            (
                _econ(
                    SONY_ID,
                    listing=16500,
                    shipping=1800,
                    imports=1950,
                    import_status="estimated",
                    price_state="estimated_landed_cost",
                    dominant=20250,
                    merchant="Captured Merchant",
                    international=True,
                    provenance="captured-offer://landed",
                ),
                _econ(
                    BOSE_ID,
                    listing=17000,
                    shipping=1800,
                    imports=2100,
                    import_status="estimated",
                    price_state="estimated_landed_cost",
                    dominant=20900,
                    merchant="Other Merchant",
                    international=True,
                    provenance="captured-offer://landed-b",
                ),
            ),
            data_classification="canonical_decision",
        ),
        page="why",
        session_location=DeliveryContext(),
    )
    assert landed.best_piq.economics.import_charges is not None
    assert landed.best_piq.economics.import_charges.status == "estimated"
    assert "estimated" in " ".join(
        line[1] for line in landed.best_piq.economics.breakdown_lines
    ).lower() or any(
        "estimated" in section.narrative.lower() + str(section.bullets).lower()
        for section in landed.why_sections
    )


def test_legacy_schema_does_not_backfill_economics() -> None:
    snapshot = _base_snapshot()
    view = page_view_from_snapshot(
        snapshot,
        page="results",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.economics.dominant_amount is None
    assert view.best_piq.economics.dominant_label == "Unavailable"
    assert view.best_piq.merchant == "Unknown"
    assert view.best_piq.image_key == ""
    assert "Lazada" not in view.best_piq.merchant
    result = compose_evidence_answer("What price did you evaluate?", packet_from_snapshot(snapshot))
    assert result.status == "insufficient_evidence"
    assert "18,990" not in result.answer


def test_missing_metadata_does_not_use_fixtures() -> None:
    view = page_view_from_snapshot(
        _economics_snapshot(),
        page="compare",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.image_key == ""
    assert view.best_piq.offer_url == ""
    assert all(value == "—" for row in view.compare_fit_rows for value in row.values)
    assert view.best_piq.piqscore.percentile_label is None
    assert "Lazada" not in view.best_piq.merchant
    sources = " ".join(item.name for item in view.sources)
    assert "Reddit" not in sources
    assert "YouTube" not in sources


def test_best_piq_can_differ_from_highest_piqscore() -> None:
    snapshot = _economics_snapshot(best_id=BOSE_ID, sony_score=93, bose_score=90)
    view = page_view_from_snapshot(
        snapshot,
        page="results",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.product_id == BOSE_ID
    assert view.highest_piqscore_product_id == SONY_ID
    assert view.why_variant == "score_diff"


def test_session_location_change_does_not_reprice() -> None:
    snapshot = _economics_snapshot()
    view = page_view_from_snapshot(
        snapshot,
        page="results",
        session_location=DeliveryContext(city="Cebu City", postal_code="6000", source="manual"),
    )
    assert view.location.city == "Taguig City"
    assert view.best_piq.economics.dominant_amount == 18990
    assert view.session_location_differs is True
    assert snapshot.content_sha256 == _economics_snapshot().content_sha256


@pytest.mark.asyncio
async def test_rendering_does_not_mutate_snapshot(
    adapter_client: AsyncClient,
    snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshot = _economics_snapshot()
    snapshots.add(snapshot)
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.offer_economics[0].dominant_amount_minor,
    )
    _bind(adapter_client, snapshot.owner)
    await adapter_client.get(f"/results/{DECISION_ID}")
    await adapter_client.get(f"/compare/{DECISION_ID}")
    await adapter_client.get(f"/why-best-piq/{DECISION_ID}")
    await adapter_client.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "Does this include shipping?", "decision_id": DECISION_ID},
    )
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    after = (
        loaded.content_sha256,
        loaded.canonical_piqscore_set_sha256,
        loaded.recommendation.snapshot_sha256,
        loaded.evaluated_product_ids,
        loaded.offer_economics[0].dominant_amount_minor,
    )
    assert before == after


@pytest.mark.asyncio
async def test_client_cannot_override_canonical_fields(
    adapter_client: AsyncClient,
    snapshots: InMemoryDecisionSnapshotRepository,
) -> None:
    snapshots.add(_economics_snapshot())
    _bind(adapter_client, _owner())
    ask = await adapter_client.post(
        "/api/v1/shopping-assistant/query",
        json={
            "query": "What price did you evaluate?",
            "decision_id": DECISION_ID,
            "price": 1,
            "piqscore": 1,
            "recommendation": "buy",
        },
    )
    assert ask.status_code == 200
    assert "18,990" in ask.json()["answer"]
    assert " ₱1 " not in f" {ask.json()['answer']} "
    assert ask.json()["answer"].count("18,990") >= 1


def test_sql_latest_for_owner_is_owner_bound(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'uuid-adapter.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    repo = SqlAlchemyDecisionSnapshotRepository(session_factory=factory, clock=lambda: START)
    first = _economics_snapshot()
    repo.add(first)
    assert repo.get_latest_for_owner(DECISION_ID, first.owner) is not None
    assert repo.get_latest_for_owner(DECISION_ID, _owner("other")) is None
    engine.dispose()


def test_refine_and_propose_remain_absent() -> None:
    source = (ROOT / "app/consumer/canonical_presentation.py").read_text(encoding="utf-8")
    routes = (ROOT / "app/api/consumer.py").read_text(encoding="utf-8")
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "refine_session_recommendation" not in source
    assert "propose_research" not in source
    assert "def refine_session_recommendation" not in routes
    assert "def propose_research" not in routes
    assert "refine_session_recommendation" not in js
    assert "propose_research" not in js
