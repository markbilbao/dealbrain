"""Canonical offer economics capture, integrity, and 29.4A consumption."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.consumer.pricing import MoneyComponent, evaluate_offer_total, select_price_state
from app.domain.entities.decision_snapshot import (
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V1_1,
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
    _StoredDecisionSnapshot,
)
from app.infrastructure.persistence.codec import decode_entity, encode
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.infrastructure.persistence.stores import SHOPPING_DECISION_SNAPSHOTS
from app.services.answer_from_evidence import compose_evidence_answer
from app.services.canonical_offer_economics import (
    attach_offer_economics,
    capture_offer_economics,
    delivery_from_location,
    money_component_from_canonical,
)
from app.services.decision_evidence_packet import packet_from_snapshot
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000029"
SONY_ID = "sony-wh-1000xm5"
BOSE_ID = "bose-qc-ultra"
ROOT = Path(__file__).resolve().parents[2]


def _owner() -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id="guest-econ",
        session_id="session-guest-econ",
        expires_at=START + timedelta(minutes=30),
    )


def _score(value: float, digest: str) -> CanonicalPiqScoreSnapshot:
    return CanonicalPiqScoreSnapshot(
        value=value,
        authority="canonical-piqscore-dealscore-engine",
        semantics_version="protected-existing-authority-v1",
        snapshot_sha256=digest * 64,
    )


def _base_snapshot() -> CanonicalDecisionSnapshot:
    return CanonicalDecisionSnapshot(
        decision_id=DECISION_ID,
        context_version=1,
        owner=_owner(),
        evaluated_products=(
            EvaluatedProductSnapshot(
                product_id=SONY_ID,
                display_name="Sony WH-1000XM5",
                variant="black",
                canonical_piqscore=_score(90, "a"),
            ),
            EvaluatedProductSnapshot(
                product_id=BOSE_ID,
                display_name="Bose QuietComfort Ultra",
                variant="black",
                canonical_piqscore=_score(88, "b"),
            ),
        ),
        recommendation=CanonicalRecommendationSnapshot(
            authority="canonical-recommendation-engine",
            decision="consider",
            best_piq_product_id=SONY_ID,
            alternative_product_ids=(BOSE_ID,),
            snapshot_sha256="c" * 64,
        ),
        evidence=(
            DecisionEvidenceSnapshot(
                evidence_id="fixture-battery-sony",
                product_id=SONY_ID,
                topic="battery",
                fact="non-live fixture battery evidence A",
                source="contract-fixture://battery/a",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="d" * 64,
            ),
            DecisionEvidenceSnapshot(
                evidence_id="fixture-battery-bose",
                product_id=BOSE_ID,
                topic="battery",
                fact="non-live fixture battery evidence B",
                source="contract-fixture://battery/b",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="e" * 64,
            ),
        ),
        unknowns=("live marketplace facts are intentionally absent",),
        affiliate_neutrality=AffiliateNeutralitySnapshot(),
        created_at=START,
        updated_at=START,
    )


def _listing(amount: float | None, status: str = "verified") -> MoneyComponent:
    return MoneyComponent(
        kind="listing",
        label="Listing price",
        amount=amount,
        status=status,  # type: ignore[arg-type]
    )


def _shipping(amount: float | None, status: str = "verified") -> MoneyComponent:
    return MoneyComponent(
        kind="shipping",
        label="Shipping",
        amount=amount,
        status=status,  # type: ignore[arg-type]
    )


def _tax(amount: float | None, status: str = "verified") -> MoneyComponent:
    return MoneyComponent(
        kind="tax",
        label="Taxes / duties",
        amount=amount,
        status=status,  # type: ignore[arg-type]
        applies=status != "not_applicable",
    )


def _voucher(amount: float | None, status: str = "verified") -> MoneyComponent:
    return MoneyComponent(
        kind="voucher",
        label="Public voucher",
        amount=amount,
        status=status,  # type: ignore[arg-type]
        applies=status == "verified",
    )


def _import_charges(amount: float | None, status: str = "estimated") -> MoneyComponent:
    return MoneyComponent(
        kind="import",
        label="Import charges",
        amount=amount,
        status=status,  # type: ignore[arg-type]
    )


def _taguig():
    return delivery_from_location(city="Taguig City", postal_code="1630", country="PH")


def _capture(
    product_id: str,
    *,
    listing: MoneyComponent,
    shipping: MoneyComponent,
    taxes: MoneyComponent,
    price_state: str,
    dominant_amount: float | None,
    merchant: str | None = "captured-merchant",
    voucher: MoneyComponent | None = None,
    import_charges: MoneyComponent | None = None,
    international: bool = False,
    provenance_source: str | None = "captured-offer://listing",
    checked_at: datetime | None = None,
):
    if dominant_amount is None and listing.amount is not None:
        adjustments = tuple(
            item for item in (voucher, shipping, taxes, import_charges) if item is not None
        )
        dominant_amount = evaluate_offer_total(listing, adjustments)
    return capture_offer_economics(
        offer_id=f"offer-{product_id}",
        product_id=product_id,
        listing=listing,
        shipping=shipping,
        taxes=taxes,
        price_state=price_state,  # type: ignore[arg-type]
        dominant_amount=dominant_amount,
        merchant=merchant,
        marketplace=merchant,
        voucher=voucher,
        import_charges=import_charges,
        delivery=_taguig(),
        international=international,
        evidence_ids=(),
        provenance_source=provenance_source,
        checked_at=checked_at,
        freshness="fresh" if checked_at else None,
    )


def _pair(sony, bose, *, classification: str = "canonical_decision") -> CanonicalDecisionSnapshot:
    return attach_offer_economics(
        _base_snapshot(),
        (sony, bose),
        delivery=_taguig(),
        data_classification=classification,
    )


def _local_final() -> CanonicalDecisionSnapshot:
    sony = _capture(
        SONY_ID,
        listing=_listing(19990),
        voucher=_voucher(-1000),
        shipping=_shipping(0),
        taxes=_tax(None, "not_applicable"),
        price_state="final_effective_cost",
        dominant_amount=18990,
        merchant="Lazada",
        provenance_source="captured-offer://lazada/sony",
        checked_at=START,
    )
    bose = _capture(
        BOSE_ID,
        listing=_listing(18990),
        voucher=None,
        shipping=_shipping(0),
        taxes=_tax(None, "not_applicable"),
        price_state="final_effective_cost",
        dominant_amount=18990,
        merchant="Shopee",
        provenance_source="captured-offer://shopee/bose",
    )
    return _pair(sony, bose)


def _landed() -> CanonicalDecisionSnapshot:
    return _pair(
        _capture(
            SONY_ID,
            listing=_listing(16500),
            shipping=_shipping(1800),
            taxes=_tax(None, "not_applicable"),
            import_charges=_import_charges(1950, "estimated"),
            price_state="estimated_landed_cost",
            dominant_amount=20250,
            international=True,
            merchant="Amazon",
            provenance_source="captured-offer://amazon/sony",
        ),
        _capture(
            BOSE_ID,
            listing=_listing(17000),
            shipping=_shipping(1800),
            taxes=_tax(None, "not_applicable"),
            import_charges=_import_charges(2100, "estimated"),
            price_state="estimated_landed_cost",
            dominant_amount=20900,
            international=True,
            merchant="Amazon",
            provenance_source="captured-offer://amazon/bose",
        ),
    )


@pytest.fixture()
def sqlite_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'offer-econ.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_v1_snapshot_omits_economics_and_keeps_schema() -> None:
    snapshot = _base_snapshot()
    payload = snapshot.to_dict()
    assert payload["schema_version"] == SCHEMA_VERSION_V1
    assert "offer_economics" not in payload
    assert snapshot.offer_economics == ()
    Draft202012Validator(
        json.loads((ROOT / "schemas/sprint29-decision-context.schema.json").read_text()),
        format_checker=FormatChecker(),
    ).validate(payload)


def test_new_economics_serialize_deserialize_and_validate() -> None:
    snapshot = _local_final()
    payload = snapshot.to_dict()
    assert payload["schema_version"] == SCHEMA_VERSION_V1_1
    assert payload["offer_economics"][0]["dominant_amount_minor"] == 1_899_000
    assert payload["offer_economics"][0]["listing"]["amount_minor"] == 1_999_000
    assert payload["offer_economics"][0]["voucher"]["amount_minor"] == -100_000
    assert payload["offer_economics"][0]["shipping"]["amount_minor"] == 0
    assert payload["offer_economics"][0]["taxes"]["status"] == "not_applicable"
    Draft202012Validator(
        json.loads((ROOT / "schemas/sprint29-decision-context-v1.1.schema.json").read_text()),
        format_checker=FormatChecker(),
    ).validate(payload)
    restored = attach_offer_economics(
        _base_snapshot(),
        snapshot.offer_economics,
        delivery=snapshot.delivery_context,
        data_classification=snapshot.data_classification,
    )
    assert restored.to_dict() == payload
    assert restored.content_sha256 == snapshot.content_sha256


def test_economics_persist_in_memory_and_sql(sqlite_factory: sessionmaker[Session]) -> None:
    snapshot = _local_final()
    memory = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    sql = SqlAlchemyDecisionSnapshotRepository(
        session_factory=sqlite_factory,
        clock=lambda: START,
    )
    memory.add(snapshot)
    sql.add(snapshot)
    loaded_memory = memory.get(DECISION_ID, 1)
    loaded_sql = sql.get(DECISION_ID, 1)
    assert loaded_memory is not None
    assert loaded_sql is not None
    assert loaded_memory.offer_economics[0].dominant_amount_minor == 1_899_000
    assert loaded_sql.offer_economics[0].merchant == "Lazada"
    assert loaded_memory.content_sha256 == snapshot.content_sha256
    assert loaded_sql.content_sha256 == snapshot.content_sha256


def test_economics_are_immutable() -> None:
    snapshot = _local_final()
    with pytest.raises(FrozenInstanceError):
        snapshot.offer_economics[0].listing.amount_minor = 1  # type: ignore[misc]


def test_old_payload_without_economics_fields_still_verifies() -> None:
    snapshot = _base_snapshot()
    digest = snapshot.content_sha256
    encoded = encode(_StoredDecisionSnapshot(snapshot=snapshot, content_sha256=digest))
    fields = encoded["fields"]["snapshot"]["fields"]
    fields.pop("offer_economics", None)
    fields.pop("delivery_context", None)
    fields.pop("data_classification", None)
    decoded = decode_entity(_StoredDecisionSnapshot, encoded)
    assert decoded.snapshot.offer_economics == ()
    assert decoded.snapshot.content_sha256 == digest
    assert "offer_economics" not in decoded.snapshot.to_dict()


def test_missing_economics_are_not_backfilled() -> None:
    packet = packet_from_snapshot(_base_snapshot())
    assert packet.offers[0].price_amount is None
    assert packet.offers[0].merchant is None
    assert packet.offers[0].shipping_status is None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda item: replace(item, listing=replace(item.listing, amount_minor=2_000_000)),
        lambda item: replace(
            item,
            voucher=replace(item.voucher, amount_minor=-50_000) if item.voucher else item.voucher,
        ),
        lambda item: replace(item, shipping=replace(item.shipping, amount_minor=15_000)),
        lambda item: replace(item, taxes=replace(item.taxes, status="unknown", amount_minor=None)),
        lambda item: replace(
            item,
            import_charges=replace(
                item.shipping, kind="import", amount_minor=195_000, status="estimated"
            ),
        ),
        lambda item: replace(item, dominant_amount_minor=1_000_000),
        lambda item: replace(item, price_state="price_before_shipping"),
        lambda item: replace(item, merchant="Other Merchant"),
        lambda item: replace(
            item,
            delivery=replace(item.delivery, city="Cebu City") if item.delivery else item.delivery,
        ),
    ],
)
def test_tampering_economics_changes_integrity_digest(mutator) -> None:  # noqa: ANN001
    snapshot = _local_final()
    original = snapshot.content_sha256
    tampered = attach_offer_economics(
        snapshot,
        (mutator(snapshot.offer_economics[0]), snapshot.offer_economics[1]),
        delivery=snapshot.delivery_context,
        data_classification=snapshot.data_classification,
    )
    assert tampered.content_sha256 != original


def test_persisted_tamper_fails_integrity(sqlite_factory: sessionmaker[Session]) -> None:
    snapshot = _local_final()
    repo = SqlAlchemyDecisionSnapshotRepository(
        session_factory=sqlite_factory,
        clock=lambda: START,
    )
    repo.add(snapshot)
    mutated = attach_offer_economics(
        snapshot,
        (
            replace(
                snapshot.offer_economics[0],
                listing=replace(snapshot.offer_economics[0].listing, amount_minor=9),
            ),
            snapshot.offer_economics[1],
        ),
        delivery=snapshot.delivery_context,
        data_classification=snapshot.data_classification,
    )
    with repo._ops() as ops:  # noqa: SLF001
        ops.upsert(
            SHOPPING_DECISION_SNAPSHOTS,
            f"{DECISION_ID}:1",
            _StoredDecisionSnapshot(snapshot=mutated, content_sha256=snapshot.content_sha256),
            owner_id="tamper",
        )
    with pytest.raises(DecisionSnapshotIntegrityError):
        repo.get(DECISION_ID, 1)


def test_price_state_final_effective_cost() -> None:
    snapshot = _local_final()
    assert snapshot.offer_economics[0].price_state == "final_effective_cost"
    assert snapshot.offer_economics[0].dominant_amount_minor == 1_899_000


def test_price_state_shipping_unknown() -> None:
    snapshot = _pair(
        _capture(
            SONY_ID,
            listing=_listing(7499),
            shipping=_shipping(None, "unknown"),
            taxes=_tax(None, "unknown"),
            price_state="price_before_shipping",
            dominant_amount=7499,
        ),
        _capture(
            BOSE_ID,
            listing=_listing(7999),
            shipping=_shipping(None, "unknown"),
            taxes=_tax(None, "unknown"),
            price_state="price_before_shipping",
            dominant_amount=7999,
        ),
    )
    assert snapshot.offer_economics[0].price_state == "price_before_shipping"
    assert snapshot.offer_economics[0].shipping.amount_minor is None
    assert snapshot.offer_economics[0].shipping.status == "unknown"


def test_price_state_estimated_landed_cost() -> None:
    offer = _landed().offer_economics[0]
    assert offer.price_state == "estimated_landed_cost"
    assert offer.shipping.status == "verified"
    assert offer.import_charges is not None
    assert offer.import_charges.status == "estimated"
    assert offer.dominant_amount_minor == 2_025_000


def test_price_state_before_unverified_import_charges() -> None:
    snapshot = _pair(
        _capture(
            SONY_ID,
            listing=_listing(16500),
            shipping=_shipping(1800),
            taxes=_tax(None, "not_applicable"),
            import_charges=_import_charges(None, "unknown"),
            price_state="before_unverified_import_charges",
            dominant_amount=18300,
            international=True,
        ),
        _capture(
            BOSE_ID,
            listing=_listing(17000),
            shipping=_shipping(1800),
            taxes=_tax(None, "not_applicable"),
            import_charges=_import_charges(None, "unverified"),
            price_state="before_unverified_import_charges",
            dominant_amount=18800,
            international=True,
        ),
    )
    assert snapshot.offer_economics[0].price_state == "before_unverified_import_charges"
    assert snapshot.offer_economics[0].import_charges is not None
    assert snapshot.offer_economics[0].import_charges.status == "unknown"


def test_price_state_potential_checkout() -> None:
    snapshot = _pair(
        _capture(
            SONY_ID,
            listing=_listing(19990),
            voucher=_voucher(-1500, "unverified"),
            shipping=_shipping(0),
            taxes=_tax(None, "not_applicable"),
            price_state="potential_checkout_price",
            dominant_amount=19990,
        ),
        _capture(
            BOSE_ID,
            listing=_listing(18990),
            shipping=_shipping(0),
            taxes=_tax(None, "not_applicable"),
            price_state="final_effective_cost",
            dominant_amount=18990,
        ),
    )
    voucher = snapshot.offer_economics[0].voucher
    assert snapshot.offer_economics[0].price_state == "potential_checkout_price"
    assert voucher is not None
    assert voucher.status == "unverified"
    assert voucher.applied is False


def test_free_shipping_is_not_unknown() -> None:
    shipping = _local_final().offer_economics[0].shipping
    assert shipping.status == "verified"
    assert shipping.amount_minor == 0
    assert shipping.is_unknown is False


def test_taxes_not_applicable_is_not_unknown() -> None:
    taxes = _local_final().offer_economics[0].taxes
    assert taxes.status == "not_applicable"
    assert taxes.is_unknown is False


def test_estimated_import_is_not_verified() -> None:
    charges = _landed().offer_economics[0].import_charges
    assert charges is not None
    assert charges.status == "estimated"
    assert charges.status != "verified"


def test_expired_voucher_is_not_applied() -> None:
    captured = capture_offer_economics(
        offer_id="offer-sony",
        product_id=SONY_ID,
        listing=_listing(19990),
        shipping=_shipping(0),
        taxes=_tax(None, "not_applicable"),
        price_state="final_effective_cost",
        dominant_amount=19990,
        voucher=_voucher(-1000, "expired"),
    )
    assert captured.voucher is not None
    assert captured.voucher.applied is False
    assert captured.voucher.status == "expired"


def test_partial_economics_are_accepted() -> None:
    captured = capture_offer_economics(
        offer_id="offer-sony",
        product_id=SONY_ID,
        listing=_listing(7499),
        shipping=_shipping(None, "unknown"),
        taxes=_tax(None, "unknown"),
        price_state="price_before_shipping",
        dominant_amount=7499,
    )
    assert captured.listing.amount_minor == 749_900
    assert captured.shipping.status == "unknown"
    assert "shipping unknown" in captured.unknowns


def test_currency_and_integer_minor_units() -> None:
    captured = _local_final().offer_economics[0]
    assert captured.currency == "PHP"
    assert isinstance(captured.listing.amount_minor, int)
    assert isinstance(captured.dominant_amount_minor, int)
    with pytest.raises(ValueError):
        replace(captured.listing, amount_minor=19990.0)  # type: ignore[arg-type]


def test_provenance_survives_and_is_not_invented() -> None:
    packet = packet_from_snapshot(_local_final())
    sources = " ".join(packet.sources)
    assert "captured-offer://lazada/sony" in sources
    assert "Reddit" not in sources
    assert "YouTube" not in sources
    assert packet_from_snapshot(_base_snapshot()).offers[0].merchant is None


def test_snapshot_with_economics_answers_price() -> None:
    result = compose_evidence_answer(
        "Why is the price ₱18,990?",
        packet_from_snapshot(_local_final()),
    )
    assert result.status in {"answered", "partially_answered"}
    assert "18,990" in result.answer
    assert "Final effective cost" in result.answer


def test_snapshot_without_economics_price_is_insufficient() -> None:
    result = compose_evidence_answer(
        "Why is the price ₱18,990?",
        packet_from_snapshot(_base_snapshot()),
    )
    assert result.status == "insufficient_evidence"
    assert "18,990" not in result.answer


def test_canonical_unknown_shipping_is_not_called_free() -> None:
    snapshot = _pair(
        _capture(
            SONY_ID,
            listing=_listing(7499),
            shipping=_shipping(None, "unknown"),
            taxes=_tax(None, "unknown"),
            price_state="price_before_shipping",
            dominant_amount=7499,
        ),
        _capture(
            BOSE_ID,
            listing=_listing(7999),
            shipping=_shipping(None, "unknown"),
            taxes=_tax(None, "unknown"),
            price_state="price_before_shipping",
            dominant_amount=7999,
        ),
    )
    result = compose_evidence_answer("Does this include shipping?", packet_from_snapshot(snapshot))
    assert "not treated as FREE" in result.answer
    assert "Price before shipping" in result.answer
    assert result.packet.offers[0].shipping_display != "FREE"


def test_canonical_estimated_import_stays_estimated() -> None:
    result = compose_evidence_answer(
        "Are import charges included?",
        packet_from_snapshot(_landed()),
    )
    assert "estimated" in result.answer.lower()
    assert "not a guaranteed checkout amount" in result.answer.lower()


def test_canonical_merchant_can_be_identified() -> None:
    result = compose_evidence_answer(
        "Which merchant is this?",
        packet_from_snapshot(_local_final()),
    )
    assert result.status == "answered"
    assert "Lazada" in result.answer


def test_production_fixtures_do_not_replace_missing_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.canonical_offer_economics.fixture_catalogs_permitted",
        lambda: False,
    )
    with pytest.raises(ValueError, match="fixture offer economics"):
        capture_offer_economics(
            offer_id="fixture-sony",
            product_id=SONY_ID,
            listing=_listing(19990),
            shipping=_shipping(0),
            taxes=_tax(None, "not_applicable"),
            price_state="final_effective_cost",
            dominant_amount=18990,
            source_classification="non_live_contract_fixture",
        )
    result = compose_evidence_answer(
        "Does this include shipping?",
        packet_from_snapshot(_base_snapshot()),
    )
    assert result.status == "insufficient_evidence"
    assert "18,990" not in result.answer


def test_answering_does_not_mutate_economics() -> None:
    snapshot = _local_final()
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.recommendation.best_piq_product_id,
        snapshot.offer_economics[0].dominant_amount_minor,
    )
    compose_evidence_answer("Why is the price ₱18,990?", packet_from_snapshot(snapshot))
    after = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.recommendation.best_piq_product_id,
        snapshot.offer_economics[0].dominant_amount_minor,
    )
    assert before == after


def test_presentation_adapter_does_not_redefine_totals() -> None:
    component = money_component_from_canonical(_local_final().offer_economics[0].listing)
    assert component.amount == 19990
    assert component.currency == "PHP"
    assert component.status == "verified"


def test_capture_does_not_recompute_price_state() -> None:
    shipping = _shipping(None, "unknown")
    taxes = _tax(None, "unknown")
    computed = select_price_state(
        shipping=shipping,
        taxes=taxes,
        import_charges=None,
        savings=(),
        international=False,
        location_known=True,
        shipping_material=True,
    )
    captured = capture_offer_economics(
        offer_id="offer-sony",
        product_id=SONY_ID,
        listing=_listing(7499),
        shipping=shipping,
        taxes=taxes,
        price_state="potential_checkout_price",
        dominant_amount=7499,
    )
    assert captured.price_state == "potential_checkout_price"
    assert captured.price_state != computed


def test_refine_and_propose_are_absent() -> None:
    from app.services import canonical_offer_economics as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "refine_session_recommendation" not in source
    assert "propose_research" not in source
