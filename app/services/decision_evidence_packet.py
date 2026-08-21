"""Read-only evidence packet for Phase 29.4A answers.

Assembles already-captured facts from a canonical decision snapshot or, when
explicitly permitted, from Product Foundation presentation fixtures. Never
calculates PiqScore or Recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.consumer.mode import UNAVAILABLE_CLASSIFICATION, fixture_catalogs_permitted
from app.consumer.pricing import format_php, shipping_display, tax_display
from app.consumer.view_models import DecisionPageView, ProductCardView
from app.domain.entities.decision_snapshot import CanonicalDecisionSnapshot


@dataclass(frozen=True, slots=True)
class EvidenceFact:
    evidence_id: str
    topic: str
    fact: str
    product_id: str | None
    source: str | None
    freshness: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluatedOfferFact:
    product_id: str
    display_name: str
    piqscore: float | None
    is_best_piq: bool
    is_highest_piqscore: bool
    is_qualified: bool
    merchant: str | None
    price_state: str | None
    price_label: str | None
    price_amount: float | None
    shipping_status: str | None
    shipping_display: str | None
    voucher_status: str | None
    import_status: str | None
    freshness_label: str | None
    why_it_won: tuple[str, ...]
    alternative_reason: str | None


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacket:
    """Bounded facts the model/composer may use. No live lookup, no mutation."""

    decision_id: str
    context_version: int
    data_classification: str
    available: bool
    best_piq_product_id: str
    best_piq_name: str
    highest_piqscore_product_id: str
    highest_piqscore_name: str
    recommendation_decision: str
    is_qualified: bool
    qualified_reason: str | None
    delivery_label: str | None
    delivery_verified: bool
    sources: tuple[str, ...]
    unknowns: tuple[str, ...]
    facts: tuple[EvidenceFact, ...]
    offers: tuple[EvaluatedOfferFact, ...]
    canonical_piqscore_set_sha256: str
    recommendation_snapshot_sha256: str
    evaluated_product_ids: tuple[str, ...]

    def offer(self, product_id: str) -> EvaluatedOfferFact | None:
        for item in self.offers:
            if item.product_id == product_id:
                return item
        return None

    def names(self) -> tuple[str, ...]:
        return tuple(item.display_name for item in self.offers)

    def facts_for(self, *topics: str) -> tuple[EvidenceFact, ...]:
        wanted = {topic.lower() for topic in topics}
        return tuple(item for item in self.facts if item.topic.lower() in wanted)


def packet_from_snapshot(snapshot: CanonicalDecisionSnapshot) -> DecisionEvidencePacket:
    best_id = snapshot.recommendation.best_piq_product_id
    highest_id = max(
        snapshot.evaluated_products,
        key=lambda item: item.canonical_piqscore.value,
    ).product_id
    offers = [
        EvaluatedOfferFact(
            product_id=product.product_id,
            display_name=product.display_name,
            piqscore=product.canonical_piqscore.value,
            is_best_piq=product.product_id == best_id,
            is_highest_piqscore=product.product_id == highest_id,
            is_qualified=False,
            merchant=None,
            price_state=None,
            price_label=None,
            price_amount=None,
            shipping_status=None,
            shipping_display=None,
            voucher_status=None,
            import_status=None,
            freshness_label=None,
            why_it_won=(),
            alternative_reason=None,
        )
        for product in snapshot.evaluated_products
    ]
    facts = tuple(
        EvidenceFact(
            evidence_id=item.evidence_id,
            topic=item.topic,
            fact=item.fact,
            product_id=item.product_id,
            source=item.source,
            freshness=item.freshness,
        )
        for item in snapshot.evidence
    )
    sources = tuple(dict.fromkeys(item.source for item in snapshot.evidence if item.source))
    best = next(item for item in offers if item.is_best_piq)
    highest = next(item for item in offers if item.is_highest_piqscore)
    return DecisionEvidencePacket(
        decision_id=snapshot.decision_id,
        context_version=snapshot.context_version,
        data_classification="non_live_contract_fixture",
        available=True,
        best_piq_product_id=best.product_id,
        best_piq_name=best.display_name,
        highest_piqscore_product_id=highest.product_id,
        highest_piqscore_name=highest.display_name,
        recommendation_decision=snapshot.recommendation.decision,
        is_qualified=False,
        qualified_reason=None,
        delivery_label=None,
        delivery_verified=False,
        sources=sources,
        unknowns=snapshot.unknowns,
        facts=facts,
        offers=tuple(offers),
        canonical_piqscore_set_sha256=snapshot.canonical_piqscore_set_sha256,
        recommendation_snapshot_sha256=snapshot.recommendation.snapshot_sha256,
        evaluated_product_ids=snapshot.evaluated_product_ids,
    )


def packet_from_page_view(view: DecisionPageView) -> DecisionEvidencePacket:
    if view.data_unavailable:
        return unavailable_packet(view.decision_id, view.context_version)
    cards = (view.best_piq, *view.alternatives)
    offers = tuple(_offer_from_card(card) for card in cards if card.product_id)
    facts = _facts_from_view(view, cards)
    sources = tuple(item.name for item in view.sources)
    return DecisionEvidencePacket(
        decision_id=view.decision_id,
        context_version=view.context_version,
        data_classification=view.data_classification,
        available=True,
        best_piq_product_id=view.best_piq.product_id,
        best_piq_name=f"{view.best_piq.brand} {view.best_piq.model}".strip(),
        highest_piqscore_product_id=view.highest_piqscore_product_id,
        highest_piqscore_name=view.highest_piqscore_name,
        recommendation_decision=view.recommendation_decision,
        is_qualified=view.best_piq.is_qualified,
        qualified_reason=view.recommendation_qualified_message,
        delivery_label=view.location.display_place or None,
        delivery_verified=view.delivery_costs_verified,
        sources=sources,
        unknowns=view.unknowns,
        facts=facts,
        offers=offers,
        canonical_piqscore_set_sha256=view.canonical_piqscore_set_sha256,
        recommendation_snapshot_sha256=view.recommendation_snapshot_sha256,
        evaluated_product_ids=tuple(card.product_id for card in cards if card.product_id),
    )


def unavailable_packet(decision_id: str, context_version: int = 1) -> DecisionEvidencePacket:
    return DecisionEvidencePacket(
        decision_id=decision_id,
        context_version=context_version,
        data_classification=UNAVAILABLE_CLASSIFICATION,
        available=False,
        best_piq_product_id="",
        best_piq_name="",
        highest_piqscore_product_id="",
        highest_piqscore_name="",
        recommendation_decision="",
        is_qualified=False,
        qualified_reason=None,
        delivery_label=None,
        delivery_verified=False,
        sources=(),
        unknowns=("Verified offer economics are not available for this request.",),
        facts=(),
        offers=(),
        canonical_piqscore_set_sha256="",
        recommendation_snapshot_sha256="",
        evaluated_product_ids=(),
    )


def presentation_fixtures_allowed() -> bool:
    return fixture_catalogs_permitted()


def _offer_from_card(card: ProductCardView) -> EvaluatedOfferFact:
    voucher_status = card.economics.voucher.status if card.economics.voucher else None
    import_status = card.economics.import_charges.status if card.economics.import_charges else None
    return EvaluatedOfferFact(
        product_id=card.product_id,
        display_name=f"{card.brand} {card.model}".strip(),
        piqscore=card.piqscore.value,
        is_best_piq=card.is_best_piq,
        is_highest_piqscore=card.is_highest_piqscore,
        is_qualified=card.is_qualified,
        merchant=card.merchant or None,
        price_state=card.economics.dominant_state,
        price_label=card.economics.dominant_label,
        price_amount=card.economics.dominant_amount,
        shipping_status=card.economics.shipping.status,
        shipping_display=shipping_display(card.economics.shipping),
        voucher_status=voucher_status,
        import_status=import_status,
        freshness_label=card.freshness_label,
        why_it_won=card.why_it_won,
        alternative_reason=card.alternative_reason or None,
    )


def _facts_from_view(
    view: DecisionPageView,
    cards: tuple[ProductCardView, ...],
) -> tuple[EvidenceFact, ...]:
    facts: list[EvidenceFact] = []
    prefix = f"pf:{view.catalog_id or view.decision_id}"
    for card in cards:
        if not card.product_id:
            continue
        name = f"{card.brand} {card.model}".strip()
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:{card.product_id}:piqscore",
                topic="piqscore",
                fact=f"{name} PiqScore {card.piqscore.value}",
                product_id=card.product_id,
                source="canonical-piqscore",
            )
        )
        if card.merchant:
            facts.append(
                EvidenceFact(
                    evidence_id=f"{prefix}:{card.product_id}:merchant",
                    topic="merchant",
                    fact=f"{name} merchant {card.merchant}",
                    product_id=card.product_id,
                    source=card.merchant,
                )
            )
        listing = card.economics.listing
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:{card.product_id}:listing",
                topic="price",
                fact=f"{name} listing {format_php(listing.amount)} ({listing.status})",
                product_id=card.product_id,
                source=card.merchant,
                status=listing.status,
            )
        )
        if card.economics.voucher is not None:
            voucher = card.economics.voucher
            amount = format_php(voucher.amount) if voucher.amount is not None else "Unknown"
            facts.append(
                EvidenceFact(
                    evidence_id=f"{prefix}:{card.product_id}:voucher",
                    topic="voucher",
                    fact=(
                        f"{name} voucher {amount} status {voucher.status}; "
                        "unverified, expired, and unsupported savings are not applied"
                    ),
                    product_id=card.product_id,
                    source=card.merchant,
                    status=voucher.status,
                )
            )
        shipping = card.economics.shipping
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:{card.product_id}:shipping",
                topic="shipping",
                fact=(f"{name} shipping {shipping_display(shipping)} (status {shipping.status})"),
                product_id=card.product_id,
                source=card.merchant,
                status=shipping.status,
            )
        )
        taxes = card.economics.taxes
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:{card.product_id}:tax",
                topic="tax",
                fact=f"{name} taxes {tax_display(taxes)} (status {taxes.status})",
                product_id=card.product_id,
                source=card.merchant,
                status=taxes.status,
            )
        )
        if card.economics.import_charges is not None:
            imports = card.economics.import_charges
            facts.append(
                EvidenceFact(
                    evidence_id=f"{prefix}:{card.product_id}:import",
                    topic="import",
                    fact=(
                        f"{name} import charges {tax_display(imports)} (status {imports.status})"
                    ),
                    product_id=card.product_id,
                    source=card.merchant,
                    status=imports.status,
                )
            )
        if card.economics.dominant_amount is not None or card.economics.dominant_state:
            facts.append(
                EvidenceFact(
                    evidence_id=f"{prefix}:{card.product_id}:price-state",
                    topic="price_state",
                    fact=(
                        f"{name} {card.economics.dominant_label} "
                        f"{format_php(card.economics.dominant_amount)}"
                    ),
                    product_id=card.product_id,
                    source=card.merchant,
                    status=card.economics.dominant_state,
                )
            )
        if card.freshness_label:
            facts.append(
                EvidenceFact(
                    evidence_id=f"{prefix}:{card.product_id}:freshness",
                    topic="freshness",
                    fact=f"{name} {card.freshness_label}",
                    product_id=card.product_id,
                    source=card.merchant,
                    freshness=card.freshness_label,
                )
            )
        for index, reason in enumerate(card.why_it_won):
            facts.append(
                EvidenceFact(
                    evidence_id=f"{prefix}:{card.product_id}:reason:{index}",
                    topic="recommendation",
                    fact=reason,
                    product_id=card.product_id,
                    source="recommendation-reasoning",
                )
            )
    if view.shopper.why_this_fits:
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:fit",
                topic="recommendation",
                fact=view.shopper.why_this_fits,
                product_id=view.best_piq.product_id,
                source="recommendation-reasoning",
            )
        )
    if view.location.is_known:
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:location",
                topic="location",
                fact=f"Current delivery area {view.location.display_place}",
                product_id=None,
                source="session-delivery",
            )
        )
    for index, unknown in enumerate(view.unknowns):
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:unknown:{index}",
                topic="unknown",
                fact=unknown,
                product_id=None,
                source=None,
            )
        )
    for source in view.sources:
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:source:{source.name}",
                topic="source",
                fact=f"Source used: {source.name}",
                product_id=None,
                source=source.name,
            )
        )
    if view.recommendation_qualified_message:
        facts.append(
            EvidenceFact(
                evidence_id=f"{prefix}:qualified",
                topic="qualified",
                fact=view.recommendation_qualified_message,
                product_id=view.best_piq.product_id,
                source="recommendation-reasoning",
            )
        )
    for section in view.why_sections:
        for index, (_icon, text) in enumerate(section.bullets):
            topic = "warranty" if "warrant" in text.lower() else "recommendation"
            if topic == "warranty" or section.number in {1, 2}:
                facts.append(
                    EvidenceFact(
                        evidence_id=f"{prefix}:why:{section.number}:{index}",
                        topic=topic,
                        fact=text,
                        product_id=view.best_piq.product_id,
                        source="recommendation-reasoning",
                    )
                )
    return tuple(facts)
