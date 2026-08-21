"""Capture already-evaluated offer economics into the canonical snapshot.

This adapter copies decision-time values. It does not search marketplaces,
recompute PiqScore, or invent missing components.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from app.consumer.mode import fixture_catalogs_permitted
from app.consumer.pricing import MoneyComponent
from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot
from app.domain.entities.offer_economics import (
    CanonicalComponentStatus,
    CanonicalDeliveryContext,
    CanonicalMoneyLine,
    CanonicalOfferEconomics,
    CanonicalPriceState,
    major_to_minor,
    minor_to_major,
)


def money_component_from_canonical(line: CanonicalMoneyLine) -> MoneyComponent:
    """Presentation adapter. Does not redefine the captured economic amount."""

    return MoneyComponent(
        kind=line.kind,  # type: ignore[arg-type]
        label=line.label or line.kind,
        amount=minor_to_major(line.amount_minor) if line.amount_minor is not None else None,
        currency=line.currency,
        status=line.status,  # type: ignore[arg-type]
        applies=line.applied,
    )


def capture_money_line(
    component: MoneyComponent,
    *,
    evidence_id: str | None = None,
) -> CanonicalMoneyLine:
    """Copy one already-determined money line. Does not apply savings logic."""

    applied = True
    if component.kind in {"voucher", "discount"}:
        applied = bool(component.may_reduce_price)
    amount_minor = major_to_minor(component.amount)
    status: CanonicalComponentStatus = component.status  # type: ignore[assignment]
    if status == "unknown":
        amount_minor = None
    return CanonicalMoneyLine(
        kind=component.kind,  # type: ignore[arg-type]
        amount_minor=amount_minor,
        currency=component.currency,
        status=status,
        applied=applied,
        evidence_id=evidence_id,
        label=component.label,
    )


def capture_offer_economics(
    *,
    offer_id: str,
    product_id: str,
    listing: MoneyComponent,
    shipping: MoneyComponent,
    taxes: MoneyComponent,
    price_state: CanonicalPriceState,
    dominant_amount: float | None,
    merchant: str | None = None,
    marketplace: str | None = None,
    seller_id: str | None = None,
    voucher: MoneyComponent | None = None,
    import_charges: MoneyComponent | None = None,
    delivery: CanonicalDeliveryContext | None = None,
    international: bool = False,
    unknowns: tuple[str, ...] = (),
    evidence_ids: tuple[str, ...] = (),
    provenance_source: str | None = None,
    checked_at: datetime | None = None,
    freshness: str | None = None,
    allow_fixture_source: bool = False,
    source_classification: str | None = None,
) -> CanonicalOfferEconomics:
    """Capture economics supplied by upstream evaluation.

    Production callers must not pass Product Foundation fixture components unless
    ``allow_fixture_source`` is explicitly true and fixture catalogs are permitted.
    """

    if source_classification == "non_live_contract_fixture" and not (
        allow_fixture_source and fixture_catalogs_permitted()
    ):
        raise ValueError("fixture offer economics cannot be captured as production evidence")

    unknowns_list = list(unknowns)
    if shipping.is_unknown:
        unknowns_list.append("shipping unknown")
    if taxes.is_unknown:
        unknowns_list.append("taxes unknown")
    if voucher is not None and voucher.status in {
        "unverified",
        "expired",
        "unsupported",
        "unknown",
    }:
        unknowns_list.append("voucher not applied")
    if import_charges is not None and import_charges.is_unknown:
        unknowns_list.append("import charges unknown")
    unique_unknowns = tuple(dict.fromkeys(item for item in unknowns_list if item))

    return CanonicalOfferEconomics(
        offer_id=offer_id,
        product_id=product_id,
        currency=listing.currency,
        listing=capture_money_line(listing),
        shipping=capture_money_line(shipping),
        taxes=capture_money_line(taxes),
        price_state=price_state,
        dominant_amount_minor=major_to_minor(dominant_amount),
        merchant=merchant,
        marketplace=marketplace,
        seller_id=seller_id,
        voucher=capture_money_line(voucher) if voucher is not None else None,
        import_charges=(capture_money_line(import_charges) if import_charges is not None else None),
        delivery=delivery,
        international=international,
        unknowns=unique_unknowns,
        evidence_ids=evidence_ids,
        provenance_source=provenance_source,
        checked_at=checked_at,
        freshness=freshness,  # type: ignore[arg-type]
    )


def delivery_from_location(
    *,
    city: str | None,
    postal_code: str | None,
    country: str | None = None,
) -> CanonicalDeliveryContext | None:
    if not city and not postal_code and not country:
        return None
    return CanonicalDeliveryContext(city=city, postal_code=postal_code, country=country)


def attach_offer_economics(
    snapshot: CanonicalDecisionSnapshot,
    economics: tuple[CanonicalOfferEconomics, ...],
    *,
    delivery: CanonicalDeliveryContext | None = None,
    data_classification: str | None = None,
) -> CanonicalDecisionSnapshot:
    """Return a new snapshot that includes captured economics. Never mutates."""

    return replace(
        snapshot,
        offer_economics=economics,
        delivery_context=delivery if delivery is not None else snapshot.delivery_context,
        data_classification=data_classification or snapshot.data_classification,
    )
