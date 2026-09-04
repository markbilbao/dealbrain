"""Read-only adapter from CanonicalDecisionSnapshot to DecisionPageView.

Translates captured facts for the existing Product Foundation UI. Does not
recalculate PiqScore, Recommendation, discounts, shipping, taxes, or price state.
"""

from __future__ import annotations

from app.consumer.fixtures import AFFILIATE_DISCLOSURE, FRESHNESS_DISCLAIMER
from app.consumer.location import DeliveryContext
from app.consumer.presentation import (
    STATUS_LABELS,
    _ask_placeholder,
    _tone_for_shipping,
    _tone_for_state,
    _tone_for_tax,
    piqscore_descriptor,
)
from app.consumer.pricing import (
    MoneyComponent,
    format_money,
    price_state_label,
    shipping_display,
    signed_money,
    tax_display,
)
from app.consumer.view_models import (
    CompareFitRow,
    DecisionPageView,
    EvidenceCategoryView,
    OfferEconomicsView,
    PageName,
    PiqScoreView,
    ProductCardView,
    ShopperContextView,
    SourceView,
    WhySectionView,
    WhyVariant,
)
from app.core.countries import is_valid_country_code, normalize_country_code
from app.domain.entities.decision_presentation import CanonicalProductPresentation
from app.domain.entities.decision_snapshot import (
    CanonicalDecisionSnapshot,
    EvaluatedProductSnapshot,
)
from app.domain.entities.offer_economics import (
    PRICE_STATE_LABELS as CANONICAL_PRICE_LABELS,
)
from app.domain.entities.offer_economics import (
    CanonicalOfferEconomics,
    minor_to_major,
)
from app.domain.entities.research_execution import TrustedMarketContext
from app.market.context import compose_market_context
from app.market.invalidation import invalidate_for_destination_change
from app.market.support import production_certified_shopping_markets
from app.services.canonical_offer_economics import money_component_from_canonical


def page_view_from_snapshot(
    snapshot: CanonicalDecisionSnapshot,
    *,
    page: PageName,
    session_location: DeliveryContext,
    location_prompt: bool = False,
    recalculating: bool = False,
    location_error: str | None = None,
    geolocation_needs_city: bool = False,
) -> DecisionPageView:
    """Build the existing consumer view model from one verified snapshot."""

    historical = _delivery_from_snapshot(snapshot)
    session_differs = _session_differs(historical, session_location)
    trusted = _trusted_from_snapshot(snapshot)
    invalidation = invalidate_for_destination_change(
        compose_market_context(trusted_market=trusted, delivery=historical),
        compose_market_context(trusted_market=trusted, delivery=session_location),
    )
    economics_by_id = {item.product_id: item for item in snapshot.offer_economics}
    highest = max(snapshot.evaluated_products, key=lambda item: item.canonical_piqscore.value)
    cards = tuple(
        _card_from_product(
            product,
            snapshot=snapshot,
            economics=economics_by_id.get(product.product_id),
            highest_id=highest.product_id,
            historical=historical,
        )
        for product in snapshot.evaluated_products
    )
    best = next(
        card for card in cards if card.product_id == snapshot.recommendation.best_piq_product_id
    )
    alternatives = tuple(card for card in cards if not card.is_best_piq)
    qualified = snapshot.qualification.is_qualified if snapshot.qualification else False
    qualified_message = _qualified_message(snapshot)
    why_variant: WhyVariant = (
        "qualified"
        if qualified
        else (
            "score_diff"
            if highest.product_id != snapshot.recommendation.best_piq_product_id
            else "standard"
        )
    )
    sources = _sources_from_snapshot(snapshot)
    unknowns = _unknowns_from_snapshot(snapshot, session_differs, session_location)
    categories = _categories_from_snapshot(snapshot)
    return DecisionPageView(
        decision_id=snapshot.decision_id,
        context_version=snapshot.context_version,
        catalog_id="",
        query_label="Your decision",
        evaluated_count=len(snapshot.evaluated_products),
        page=page,
        why_variant=why_variant,
        location=historical,
        location_prompt=False,
        recalculating=False,
        recommendation_changed=False,
        recommendation_changed_message=None,
        best_piq=best,
        alternatives=alternatives,
        compared=cards,
        highest_piqscore_product_id=highest.product_id,
        highest_piqscore_name=highest.display_name,
        recommendation_decision=snapshot.recommendation.decision,
        shopper=_shopper_from_snapshot(snapshot, historical, best),
        affiliate_disclosure=AFFILIATE_DISCLOSURE,
        freshness_disclaimer=FRESHNESS_DISCLAIMER,
        data_classification=snapshot.data_classification,
        unknowns=unknowns,
        evidence_categories=categories,
        sources=sources,
        why_sections=_why_sections_from_snapshot(snapshot, cards, historical, unknowns, sources),
        ask_placeholder=_ask_placeholder(page),
        ask_suggestions=_canonical_ask_suggestions(snapshot),
        compare_pay_rows=_pay_rows_from_cards(cards, historical),
        compare_fit_rows=_fit_rows_from_snapshot(snapshot, cards),
        canonical_piqscore_set_sha256=snapshot.canonical_piqscore_set_sha256,
        recommendation_snapshot_sha256=snapshot.recommendation.snapshot_sha256,
        geocode_available=False,
        location_error=location_error,
        geolocation_needs_city=geolocation_needs_city,
        delivery_costs_verified=_delivery_verified(snapshot),
        data_unavailable=False,
        unavailable_message=None,
        destination_snapshot_known=historical.is_known,
        recommendation_qualified_message=qualified_message,
        session_location_differs=session_differs,
        session_location_label=session_location.display_place or None,
        presentation_mode="canonical",
        qualification_state=(
            snapshot.qualification.state if snapshot.qualification is not None else None
        ),
        shopping_market_certified=production_certified_shopping_markets().is_certified(
            trusted.country_code if trusted is not None else None
        ),
        destination_reevaluation_required=invalidation.reevaluation_required,
    )


def _delivery_from_snapshot(snapshot: CanonicalDecisionSnapshot) -> DeliveryContext:
    context = snapshot.delivery_context or next(
        (item.delivery for item in snapshot.offer_economics if item.delivery),
        None,
    )
    if context is None or not context.city:
        return DeliveryContext()
    return DeliveryContext(
        city=context.city,
        postal_code=context.postal_code,
        source="manual",
    )


def _trusted_from_snapshot(snapshot: CanonicalDecisionSnapshot) -> TrustedMarketContext | None:
    """Use captured country only. Do not invent PH when the snapshot omitted it."""

    country = None
    if snapshot.delivery_context is not None:
        country = snapshot.delivery_context.country
    if not country:
        country = next(
            (item.delivery.country for item in snapshot.offer_economics if item.delivery),
            None,
        )
    code = normalize_country_code(country)
    if not code or not is_valid_country_code(code):
        return None
    try:
        return TrustedMarketContext(country_code=code)
    except ValueError:
        return None


def _session_differs(historical: DeliveryContext, session: DeliveryContext) -> bool:
    if not historical.is_known or not session.is_known:
        return False
    return historical.destination_key != session.destination_key


def _card_from_product(
    product: EvaluatedProductSnapshot,
    *,
    snapshot: CanonicalDecisionSnapshot,
    economics: CanonicalOfferEconomics | None,
    highest_id: str,
    historical: DeliveryContext,
) -> ProductCardView:
    presentation = _product_presentation(snapshot, product.product_id)
    brand, model = _captured_identity(presentation)
    listing = MoneyComponent(kind="listing", label="Listing price", amount=None, status="unknown")
    shipping = MoneyComponent(kind="shipping", label="Shipping", amount=None, status="unknown")
    taxes = MoneyComponent(kind="tax", label="Taxes / duties", amount=None, status="unknown")
    voucher = None
    imports = None
    dominant_state = "price_before_shipping"
    dominant_amount = None
    international = False
    merchant = "Unknown"
    freshness = None
    if economics is not None:
        listing = money_component_from_canonical(economics.listing)
        shipping = money_component_from_canonical(economics.shipping)
        taxes = money_component_from_canonical(economics.taxes)
        voucher = money_component_from_canonical(economics.voucher) if economics.voucher else None
        imports = (
            money_component_from_canonical(economics.import_charges)
            if economics.import_charges
            else None
        )
        dominant_state = economics.price_state
        dominant_amount = minor_to_major(economics.dominant_amount_minor)
        international = economics.international
        merchant = economics.merchant or "Unknown"
        freshness = economics.freshness
        if historical.is_known:
            shipping = MoneyComponent(
                kind=shipping.kind,
                label=f"Shipping to {historical.display_place}",
                amount=shipping.amount,
                currency=shipping.currency,
                status=shipping.status,
                applies=shipping.applies,
            )
    dest = historical.display_place if historical.is_known else "the decision destination"
    why_won = _why_won_from_snapshot(snapshot, product.product_id)
    alt_reason = _tradeoff_for(snapshot, product.product_id)
    if not alt_reason and product.product_id != snapshot.recommendation.best_piq_product_id:
        alt_reason = "This offer is in the evaluated set and was not selected as Best Piq."
    return ProductCardView(
        product_id=product.product_id,
        brand=brand,
        model=model,
        category=presentation.category if presentation and presentation.category else "",
        merchant=merchant,
        offer_url=presentation.offer_url if presentation and presentation.offer_url else "",
        image_key="",
        tags=(),
        piqscore=PiqScoreView(
            value=product.canonical_piqscore.value,
            descriptor=piqscore_descriptor(product.canonical_piqscore.value),
            percentile_label=None,
            snapshot_sha256=product.canonical_piqscore.snapshot_sha256,
        ),
        economics=OfferEconomicsView(
            listing=listing,
            voucher=voucher,
            shipping=shipping,
            taxes=taxes,
            import_charges=imports,
            other_costs=(),
            dominant_state=dominant_state,  # type: ignore[arg-type]
            dominant_label=(
                CANONICAL_PRICE_LABELS.get(dominant_state, price_state_label(dominant_state))
                if economics is not None
                else "Unavailable"
            ),
            dominant_amount=dominant_amount,
            international=international,
            shipping_material=True,
            breakdown_lines=_breakdown_from_components(
                listing, voucher, shipping, taxes, imports, dominant_state, dominant_amount
            ),
        ),
        is_best_piq=product.product_id == snapshot.recommendation.best_piq_product_id,
        is_highest_piqscore=product.product_id == highest_id,
        is_qualified=bool(
            snapshot.qualification
            and snapshot.qualification.is_qualified
            and product.product_id == snapshot.recommendation.best_piq_product_id
        ),
        alternative_badge=None,
        alternative_reason=alt_reason,
        compact_breakdown=_compact_from_components(listing, voucher, shipping),
        why_it_won=why_won,
        freshness_label=freshness,
        origin_label=dest if historical.is_known else None,
        display_name=product.display_name,
    )


def _breakdown_from_components(
    listing: MoneyComponent,
    voucher: MoneyComponent | None,
    shipping: MoneyComponent,
    taxes: MoneyComponent,
    imports: MoneyComponent | None,
    state: str,
    dominant_amount: float | None,
) -> tuple[tuple[str, str, str], ...]:
    lines: list[tuple[str, str, str]] = [
        (listing.label, format_money(listing.amount, listing.currency), "neutral"),
    ]
    if voucher is not None:
        if voucher.status == "verified" and voucher.applies:
            lines.append(
                (voucher.label, signed_money(voucher.amount, voucher.currency), "positive")
            )
        else:
            lines.append((voucher.label, "Not applied", "warn"))
    lines.append((shipping.label, shipping_display(shipping), _tone_for_shipping(shipping)))
    if imports is not None:
        lines.append((imports.label, tax_display(imports), _tone_for_shipping(imports)))
    else:
        lines.append((taxes.label, tax_display(taxes), _tone_for_tax(taxes)))
    label = CANONICAL_PRICE_LABELS.get(state, price_state_label(state))  # type: ignore[arg-type]
    lines.append((label, format_money(dominant_amount, listing.currency), _tone_for_state(state)))
    return tuple(lines)


def _compact_from_components(
    listing: MoneyComponent,
    voucher: MoneyComponent | None,
    shipping: MoneyComponent,
) -> str:
    parts = [format_money(listing.amount, listing.currency)]
    if voucher is not None and voucher.status == "verified" and voucher.amount:
        parts.append(f"{signed_money(voucher.amount, voucher.currency)} voucher")
    if shipping.is_unknown:
        parts.append("shipping not verified")
    elif shipping.amount == 0 and shipping.status == "verified":
        parts.append("FREE shipping")
    elif shipping.amount is not None:
        parts.append(f"{format_money(shipping.amount, shipping.currency)} shipping")
    return " · ".join(parts)


def _product_presentation(
    snapshot: CanonicalDecisionSnapshot,
    product_id: str,
) -> CanonicalProductPresentation | None:
    return next(
        (item for item in snapshot.product_presentation if item.product_id == product_id),
        None,
    )


def _captured_identity(
    presentation: CanonicalProductPresentation | None,
) -> tuple[str, str]:
    if presentation is None:
        return "", ""
    return presentation.brand or "", presentation.model or ""


def _why_won_from_snapshot(
    snapshot: CanonicalDecisionSnapshot,
    product_id: str,
) -> tuple[str, ...]:
    reasons = tuple(
        item.reason
        for item in snapshot.recommendation_reasons
        if item.product_id in {None, product_id}
    )
    if reasons:
        return reasons[:3]
    return tuple(item.fact for item in snapshot.evidence if item.product_id == product_id)[:3]


def _tradeoff_for(snapshot: CanonicalDecisionSnapshot, product_id: str) -> str:
    return next(
        (item.reason for item in snapshot.alternative_tradeoffs if item.product_id == product_id),
        "",
    )


def _shopper_from_snapshot(
    snapshot: CanonicalDecisionSnapshot,
    historical: DeliveryContext,
    best: ProductCardView,
) -> ShopperContextView:
    context = snapshot.shopper_context
    why_fits = f"{best.identity_name} is the canonical Best Piq for You in this decision."
    if snapshot.recommendation_reasons:
        why_fits = snapshot.recommendation_reasons[0].reason
    if context is None:
        return ShopperContextView(
            budget_label="Not captured",
            top_priority="Not captured",
            use_case="Not captured",
            delivery_label=historical.display_place or "Not set",
            urgency="Not captured",
            why_this_fits=why_fits,
        )
    return ShopperContextView(
        budget_label=context.budget_label or "Not captured",
        top_priority=context.top_priority or "Not captured",
        use_case=context.use_case or "Not captured",
        delivery_label=historical.display_place or "Not set",
        urgency=context.urgency or "Not captured",
        why_this_fits=why_fits,
    )


def _qualified_message(snapshot: CanonicalDecisionSnapshot) -> str | None:
    qualification = snapshot.qualification
    if qualification is None or not qualification.is_qualified:
        return None
    parts = list(qualification.reasons)
    if qualification.material_unknowns:
        parts.append("Material unknown: " + "; ".join(qualification.material_unknowns))
    if qualification.could_change_recommendation:
        parts.append("This unknown could materially change the Recommendation.")
    return " ".join(parts) if parts else "This is a qualified Best Piq for You."


def _sources_from_snapshot(snapshot: CanonicalDecisionSnapshot) -> tuple[SourceView, ...]:
    names: list[str] = []
    for item in snapshot.evidence:
        if item.source:
            names.append(item.source)
    for item in snapshot.offer_economics:
        if item.provenance_source:
            names.append(item.provenance_source)
    return tuple(SourceView(name=name, proven=True) for name in dict.fromkeys(names))


def _categories_from_snapshot(
    snapshot: CanonicalDecisionSnapshot,
) -> tuple[EvidenceCategoryView, ...]:
    topics = tuple(dict.fromkeys(item.topic for item in snapshot.evidence if item.topic))
    return tuple(
        EvidenceCategoryView(
            label=topic,
            status="verified",
            status_label=STATUS_LABELS["verified"],
        )
        for topic in topics
    )


def _unknowns_from_snapshot(
    snapshot: CanonicalDecisionSnapshot,
    session_differs: bool,
    session_location: DeliveryContext,
) -> tuple[str, ...]:
    items = list(snapshot.unknowns)
    for offer in snapshot.offer_economics:
        for unknown in offer.unknowns:
            if unknown not in items:
                items.append(unknown)
    if snapshot.qualification is not None:
        for unknown in snapshot.qualification.material_unknowns:
            if unknown not in items:
                items.append(unknown)
    if not snapshot.offer_economics:
        items.append("Offer economics were not captured in this decision snapshot.")
    if session_differs and session_location.display_place:
        items.append(
            f"Your current session location is {session_location.display_place}. "
            "This historical decision was not re-evaluated for that destination."
        )
    return tuple(items)


def _delivery_verified(snapshot: CanonicalDecisionSnapshot) -> bool:
    return any(item.shipping.status == "verified" for item in snapshot.offer_economics)


def _why_sections_from_snapshot(
    snapshot: CanonicalDecisionSnapshot,
    cards: tuple[ProductCardView, ...],
    historical: DeliveryContext,
    unknowns: tuple[str, ...],
    sources: tuple[SourceView, ...],
) -> tuple[WhySectionView, ...]:
    best = next(card for card in cards if card.is_best_piq)
    delivery = historical.display_place or "the captured destination"
    rec = snapshot.recommendation.decision
    if snapshot.recommendation_reasons:
        narrative = " ".join(item.reason for item in snapshot.recommendation_reasons)
    else:
        narrative = (
            f"{best.identity_name} is Best Piq for You from the evaluated offers. "
            f"The canonical Recommendation is {rec}."
        )
    if best.product_id != snapshot.evaluated_products[0].product_id or any(
        card.is_highest_piqscore and not card.is_best_piq for card in cards
    ):
        highest = next(card for card in cards if card.is_highest_piqscore)
        narrative += (
            f" {highest.identity_name} has the higher objective PiqScore. "
            "PiqScore evaluates the offer; Best Piq for You reflects what best fits the shopper."
        )
    know_bullets: list[tuple[str, str]] = []
    if best.economics.dominant_amount is not None:
        know_bullets.append(
            (
                "check",
                f"Price PiqSavi evaluated: {best.economics.dominant_label} "
                f"{format_money(best.economics.dominant_amount, best.economics.listing.currency)}",
            )
        )
    else:
        know_bullets.append(("warn", "Price PiqSavi evaluated is unavailable for this snapshot."))
    know_bullets.append(("check", f"Shipping: {shipping_display(best.economics.shipping)}"))
    if best.economics.voucher is not None:
        applied = "applied" if best.economics.voucher.applies else "not applied"
        know_bullets.append(("check", f"Voucher {best.economics.voucher.status}; {applied}"))
    if best.economics.import_charges is not None:
        know_bullets.append(
            (
                "check",
                f"Import charges: {tax_display(best.economics.import_charges)} "
                f"({best.economics.import_charges.status})",
            )
        )
    for item in snapshot.evidence[:4]:
        know_bullets.append(("check", item.fact))
    if snapshot.alternative_tradeoffs:
        alts = [item.reason for item in snapshot.alternative_tradeoffs]
    else:
        alts = [
            f"{card.identity_name} remains an evaluated alternative."
            for card in cards
            if not card.is_best_piq
        ]
    if not alts:
        alts = ["No alternative products were captured in this decision."]
    if snapshot.best_for:
        best_for = tuple(("check", item.label) for item in snapshot.best_for)
    else:
        best_for = (
            (
                "check",
                "Shopper priorities were not captured as structured fields on this snapshot.",
            ),
        )
    why_bullets: list[tuple[str, str]] = [
        ("priority", f"Recommendation: {rec}"),
        ("delivery", f"Delivery to: {delivery}"),
        ("check", f"Best Piq: {best.identity_name}"),
    ]
    if snapshot.shopper_context and snapshot.shopper_context.top_priority:
        why_bullets.append(("priority", f"Top priority: {snapshot.shopper_context.top_priority}"))
    if snapshot.shopper_context and snapshot.shopper_context.budget_label:
        why_bullets.append(("budget", f"Budget: {snapshot.shopper_context.budget_label}"))
    return (
        WhySectionView(
            number=1,
            title="Why PiqSavi recommends this",
            narrative=narrative,
            bullets=tuple(why_bullets),
            callout=_qualified_message(snapshot),
            callout_tone="warn"
            if snapshot.qualification and snapshot.qualification.is_qualified
            else "info",
        ),
        WhySectionView(
            number=2,
            title="What to know before you buy",
            narrative="",
            bullets=tuple(know_bullets),
        ),
        WhySectionView(
            number=3,
            title="Best for",
            narrative="",
            bullets=best_for,
        ),
        WhySectionView(
            number=4,
            title="When an alternative may be better",
            narrative="",
            bullets=tuple(("alt", item) for item in alts),
        ),
        WhySectionView(
            number=5,
            title="What PiqSavi considered",
            narrative="",
            bullets=(),
            extra={
                "categories": tuple(
                    (item.label, item.status) for item in _categories_from_snapshot(snapshot)
                ),
                "sources": tuple(item.name for item in sources),
            },
        ),
        WhySectionView(
            number=6,
            title="What we don’t know",
            narrative="",
            bullets=tuple(("warn", item) for item in unknowns),
        ),
    )


def _canonical_ask_suggestions(snapshot: CanonicalDecisionSnapshot) -> tuple[str, ...]:
    suggestions = [
        "What price did you evaluate?",
        "Does this include shipping?",
        "Which merchant is this?",
        "What don’t you know?",
    ]
    if snapshot.shopper_context is not None:
        suggestions.insert(0, "What was my top priority?")
    if snapshot.qualification is not None:
        suggestions.insert(1, "Why is this qualified?")
    if snapshot.best_for:
        suggestions.append("What is this best for?")
    if any(item.offer_url for item in snapshot.product_presentation):
        suggestions.append("Where can I buy this?")
    return tuple(suggestions[:6])


def _pay_rows_from_cards(
    cards: tuple[ProductCardView, ...],
    historical: DeliveryContext,
) -> tuple[CompareFitRow, ...]:
    dest = historical.display_place if historical.is_known else "your area"
    return (
        CompareFitRow(
            "Final cost",
            tuple(
                format_money(card.economics.dominant_amount, card.economics.listing.currency)
                for card in cards
            ),
        ),
        CompareFitRow(
            "Price status",
            tuple(card.economics.dominant_label for card in cards),
        ),
        CompareFitRow(
            "Listing price",
            tuple(
                format_money(card.economics.listing.amount, card.economics.listing.currency)
                if card.economics.listing.amount is not None
                else "Unknown"
                for card in cards
            ),
        ),
        CompareFitRow(
            f"Shipping to {dest}" if historical.is_known else "Shipping",
            tuple(shipping_display(card.economics.shipping) for card in cards),
        ),
        CompareFitRow(
            "Taxes / import charges",
            tuple(
                tax_display(card.economics.import_charges)
                if card.economics.import_charges is not None
                else tax_display(card.economics.taxes)
                for card in cards
            ),
        ),
    )


def _fit_rows_from_snapshot(
    snapshot: CanonicalDecisionSnapshot,
    cards: tuple[ProductCardView, ...],
) -> tuple[CompareFitRow, ...]:
    attributes = {
        item.key: item.label
        for product in snapshot.product_presentation
        for item in product.fit_attributes
    }
    if not attributes:
        return ()
    by_product = {item.product_id: item for item in snapshot.product_presentation}
    rows: list[CompareFitRow] = []
    for key, label in attributes.items():
        values: list[str] = []
        for card in cards:
            presentation = by_product.get(card.product_id)
            match = next(
                (
                    item
                    for item in (presentation.fit_attributes if presentation else ())
                    if item.key == key
                ),
                None,
            )
            values.append(match.display_value() if match else "—")
        rows.append(CompareFitRow(label, tuple(values), kind="text"))
    return tuple(rows)
