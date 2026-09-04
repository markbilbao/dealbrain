"""Assemble Product Foundation page views from fixtures and session location.

Does not calculate PiqScore or Recommendation. Destination changes either load an
explicit fixture snapshot or invalidate location-sensitive economics.
"""

from __future__ import annotations

from app.consumer import mode as consumer_mode
from app.consumer.fixtures import (
    AFFILIATE_DISCLOSURE,
    DATA_CLASSIFICATION,
    DEFAULT_CATALOG_ID,
    FRESHNESS_DISCLAIMER,
    FixtureDecision,
    FixtureOffer,
    destination_catalog,
    get_decision,
)
from app.consumer.location import DeliveryContext
from app.consumer.market_coverage import attach_shopping_coverage
from app.consumer.pricing import (
    MoneyComponent,
    evaluate_offer_total,
    format_money,
    price_state_label,
    shipping_display,
    signed_money,
    tax_display,
)
from app.consumer.uuid import is_canonical_uuid
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
)
from app.market.completeness import select_dominant_price_state
from app.market.context import intended_ph_product_defaults
from app.market.selection import SelectedShoppingMarket
from app.market.support import production_certified_shopping_markets

STATUS_LABELS = {
    "verified": "Verified",
    "not_applicable": "Not applicable",
    "unknown": "Unknown",
    "unverified": "Not verified",
    "estimated": "Estimated",
}


def piqscore_descriptor(value: float) -> str:
    if value >= 90:
        return "Excellent"
    if value >= 80:
        return "Very Good"
    if value >= 70:
        return "Good"
    if value >= 60:
        return "Fair"
    return "Limited"


def build_page_view(
    *,
    decision_id: str,
    page: PageName,
    location: DeliveryContext,
    location_prompt: bool | None = None,
    recalculating: bool = False,
    location_error: str | None = None,
    geolocation_needs_city: bool = False,
    allow_fixtures: bool | None = None,
    selected_market: SelectedShoppingMarket | None = None,
) -> DecisionPageView:
    permitted = (
        consumer_mode.fixture_catalogs_permitted() if allow_fixtures is None else allow_fixtures
    )
    prompt_when_absent = location.is_absent if location_prompt is None else bool(location_prompt)
    if is_canonical_uuid(decision_id):
        return _unavailable_page_view(
            decision_id=decision_id,
            page=page,
            location=location,
            location_prompt=prompt_when_absent,
            recalculating=recalculating,
            location_error=location_error,
            geolocation_needs_city=geolocation_needs_city,
            selected_market=selected_market,
        )
    if not permitted:
        return _unavailable_page_view(
            decision_id=decision_id or "unavailable",
            page=page,
            location=location,
            location_prompt=prompt_when_absent,
            recalculating=recalculating,
            location_error=location_error,
            geolocation_needs_city=geolocation_needs_city,
            selected_market=selected_market,
        )
    catalog_id = _resolve_catalog(decision_id, location)
    decision = get_decision(catalog_id)
    prompt = decision.why_variant != "qualified" if location_prompt is None else location_prompt
    if location.is_known or location.is_skipped:
        prompt = False if location_prompt is None else location_prompt

    highest = max(decision.offers, key=lambda item: item.piqscore)
    overlay_unknown_shipping = _should_unknown_shipping(decision, location)
    destination_snapshot_known = location.is_known and not overlay_unknown_shipping
    qualify_recommendation = location.is_known and overlay_unknown_shipping
    cards = tuple(
        _product_card(
            offer,
            decision=decision,
            location=location,
            highest_id=highest.product_id,
            unknown_shipping=overlay_unknown_shipping,
            qualify_recommendation=qualify_recommendation,
        )
        for offer in decision.offers
    )
    best = next(card for card in cards if card.is_best_piq)
    alternatives = tuple(card for card in cards if not card.is_best_piq)
    delivery_label = location.display_place if location.is_known else "your area"
    shopper = ShopperContextView(
        budget_label=decision.shopper_budget,
        top_priority=decision.shopper_priority,
        use_case=decision.shopper_use_case,
        delivery_label=delivery_label if location.is_known else "Not set",
        urgency=decision.shopper_urgency,
        why_this_fits=_why_fits(decision, location, best),
    )
    changed = bool(decision.changes_recommendation and location.is_known)
    changed_message = None
    if changed:
        template = str(decision.extra.get("changed_message") or "")
        changed_message = template.format(delivery=location.display_place)
    qualified_message = None
    if qualify_recommendation:
        qualified_message = (
            f"Shipping to {location.display_place} is not yet verified and may change "
            "this recommendation. This is a qualified Best Piq for You."
        )
    view = DecisionPageView(
        decision_id=decision.catalog_id,
        context_version=1,
        catalog_id=decision.catalog_id,
        query_label=decision.query_label,
        evaluated_count=decision.evaluated_count,
        page=page,
        why_variant=decision.why_variant,
        location=location,
        location_prompt=bool(prompt and location.is_absent),
        recalculating=recalculating,
        recommendation_changed=changed,
        recommendation_changed_message=changed_message,
        best_piq=best,
        alternatives=alternatives,
        compared=cards[:4],
        highest_piqscore_product_id=highest.product_id,
        highest_piqscore_name=f"{highest.brand} {highest.model}",
        recommendation_decision=decision.recommendation_decision,
        shopper=shopper,
        affiliate_disclosure=AFFILIATE_DISCLOSURE,
        freshness_disclaimer=FRESHNESS_DISCLAIMER,
        data_classification=DATA_CLASSIFICATION,
        unknowns=_unknowns_for_location(decision, location, qualify_recommendation),
        evidence_categories=tuple(
            EvidenceCategoryView(
                label=label,
                status=status,  # type: ignore[arg-type]
                status_label=STATUS_LABELS.get(status, status.replace("_", " ").title()),
            )
            for label, status in decision.evidence_categories
        ),
        sources=tuple(SourceView(name=name, proven=True) for name in decision.sources),
        why_sections=_why_sections(
            decision,
            location,
            qualify_recommendation=qualify_recommendation,
            qualified_message=qualified_message,
        ),
        ask_placeholder=_ask_placeholder(page),
        ask_suggestions=_ask_suggestions(page, decision, cards),
        compare_pay_rows=_pay_rows(cards, location),
        compare_fit_rows=_fit_rows(cards),
        canonical_piqscore_set_sha256=decision.piqscore_set_sha256,
        recommendation_snapshot_sha256=decision.recommendation_sha256,
        geocode_available=False,
        location_error=location_error,
        geolocation_needs_city=geolocation_needs_city,
        delivery_costs_verified=destination_snapshot_known,
        destination_snapshot_known=destination_snapshot_known,
        recommendation_qualified_message=qualified_message,
        shopping_market_certified=production_certified_shopping_markets().is_certified("PH"),
        destination_reevaluation_required=bool(overlay_unknown_shipping and location.is_known),
    )
    return attach_shopping_coverage(view, selected_market)


def list_catalog_ids() -> tuple[str, ...]:
    from app.consumer.fixtures import CATALOG

    return tuple(CATALOG)


def _unavailable_page_view(
    *,
    decision_id: str,
    page: PageName,
    location: DeliveryContext,
    location_prompt: bool,
    recalculating: bool,
    location_error: str | None,
    geolocation_needs_city: bool,
    selected_market: SelectedShoppingMarket | None = None,
) -> DecisionPageView:
    """Honest production state when canonical offer economics are missing."""
    empty = _unavailable_product()
    view = DecisionPageView(
        decision_id=decision_id,
        context_version=1,
        catalog_id="",
        query_label="Decision",
        evaluated_count=0,
        page=page,
        why_variant="standard",
        location=location,
        location_prompt=location_prompt and location.is_absent,
        recalculating=recalculating,
        recommendation_changed=False,
        recommendation_changed_message=None,
        best_piq=empty,
        alternatives=(),
        compared=(),
        highest_piqscore_product_id="",
        highest_piqscore_name="",
        recommendation_decision="",
        shopper=ShopperContextView(
            budget_label="",
            top_priority="",
            use_case="",
            delivery_label=location.display_place if location.is_known else "Not set",
            urgency="",
            why_this_fits="",
        ),
        affiliate_disclosure="",
        freshness_disclaimer="",
        data_classification=consumer_mode.UNAVAILABLE_CLASSIFICATION,
        unknowns=("Verified offer economics are not available for this request.",),
        evidence_categories=(),
        sources=(),
        why_sections=(),
        ask_placeholder="Ask PiqSavi...",
        ask_suggestions=(),
        compare_pay_rows=(),
        compare_fit_rows=(),
        canonical_piqscore_set_sha256="",
        recommendation_snapshot_sha256="",
        geocode_available=False,
        location_error=location_error,
        geolocation_needs_city=geolocation_needs_city,
        delivery_costs_verified=False,
        data_unavailable=True,
        unavailable_message=(
            "PiqSavi does not have a complete canonical decision with verified "
            "offer economics for this request. Prices, merchants, shipping, "
            "discounts, PiqScore, and Recommendation evidence are unavailable. "
            "Demo catalogs are not used as production shopping evidence."
        ),
        destination_snapshot_known=False,
        recommendation_qualified_message=None,
        presentation_mode="unavailable",
        shopping_market_certified=False,
        destination_reevaluation_required=False,
    )
    return attach_shopping_coverage(view, selected_market)


def _unavailable_product() -> ProductCardView:
    listing = MoneyComponent(kind="listing", label="Listing price", amount=None, status="unknown")
    shipping = MoneyComponent(kind="shipping", label="Shipping", amount=None, status="unknown")
    taxes = MoneyComponent(kind="tax", label="Taxes / duties", amount=None, status="unknown")
    economics = OfferEconomicsView(
        listing=listing,
        voucher=None,
        shipping=shipping,
        taxes=taxes,
        import_charges=None,
        other_costs=(),
        dominant_state="price_before_shipping",
        dominant_label="Unavailable",
        dominant_amount=None,
        international=False,
        shipping_material=True,
        breakdown_lines=(),
    )
    return ProductCardView(
        product_id="",
        brand="",
        model="",
        category="",
        merchant="",
        offer_url="/",
        image_key="",
        tags=(),
        piqscore=PiqScoreView(value=0.0, descriptor="", percentile_label=None, snapshot_sha256=""),
        economics=economics,
        is_best_piq=True,
        is_highest_piqscore=False,
        is_qualified=False,
        alternative_badge=None,
        alternative_reason="",
        compact_breakdown="",
        why_it_won=(),
        freshness_label=None,
        origin_label=None,
    )


def _unknowns_for_location(
    decision: FixtureDecision,
    location: DeliveryContext,
    qualify_recommendation: bool,
) -> tuple[str, ...]:
    items = list(decision.unknowns)
    if qualify_recommendation:
        note = (
            f"Shipping, availability, and total cost for {location.display_place} "
            "are not in a destination-specific snapshot and may change this recommendation."
        )
        if note not in items:
            items.insert(0, note)
    return tuple(items)


def _resolve_catalog(decision_id: str, location: DeliveryContext) -> str:
    current = decision_id if decision_id else DEFAULT_CATALOG_ID
    try:
        get_decision(current)
    except KeyError:
        current = DEFAULT_CATALOG_ID
    if location.is_known:
        return destination_catalog(current, location.destination_key)
    return current


def _should_unknown_shipping(decision: FixtureDecision, location: DeliveryContext) -> bool:
    if location.is_skipped or location.is_absent:
        return True
    key = location.destination_key
    if any(key == alias or key.startswith(f"{alias}") for alias in decision.destination_aliases):
        return False
    city_slug = key.split("-")[0]
    aliases = decision.destination_aliases
    if any(alias == city_slug or alias.startswith(f"{city_slug}-") for alias in aliases):
        return False
    return not any(city_slug == alias.split("-")[0] for alias in aliases)


def _product_card(
    offer: FixtureOffer,
    *,
    decision: FixtureDecision,
    location: DeliveryContext,
    highest_id: str,
    unknown_shipping: bool,
    qualify_recommendation: bool = False,
) -> ProductCardView:
    shipping = offer.shipping
    taxes = offer.taxes
    imports = offer.import_charges
    if unknown_shipping and offer.shipping_material:
        dest = location.display_place if location.is_known else "your area"
        shipping = MoneyComponent(
            kind="shipping",
            label=f"Shipping to {dest}",
            amount=None,
            status="unknown",
        )
        if offer.international and imports is not None:
            imports = MoneyComponent(
                kind="import",
                label="Estimated import charges",
                amount=None,
                status="unknown",
            )
        if taxes.status not in {"not_applicable"}:
            taxes = MoneyComponent(
                kind="tax",
                label="Taxes / duties",
                amount=None,
                status="unknown",
            )
    dest = location.display_place if location.is_known else "your area"
    if location.is_known:
        shipping = MoneyComponent(
            kind=shipping.kind,
            label=f"Shipping to {dest}",
            amount=shipping.amount,
            currency=shipping.currency,
            status=shipping.status,
            applies=shipping.applies,
        )
    savings = tuple(item for item in (offer.voucher,) if item is not None)
    market = intended_ph_product_defaults(delivery=location)
    state = select_dominant_price_state(
        market=market,
        shipping=shipping,
        taxes=taxes,
        import_charges=imports,
        savings=savings,
        international=offer.international,
        shipping_material=offer.shipping_material,
        destination_sensitive_stale=unknown_shipping,
    )
    adjustments: list[MoneyComponent] = []
    if offer.voucher is not None:
        adjustments.append(offer.voucher)
    adjustments.append(shipping)
    adjustments.append(taxes)
    if imports is not None:
        adjustments.append(imports)
    dominant_amount = evaluate_offer_total(offer.listing, tuple(adjustments))
    economics = OfferEconomicsView(
        listing=offer.listing,
        voucher=offer.voucher,
        shipping=shipping,
        taxes=taxes,
        import_charges=imports,
        other_costs=(),
        dominant_state=state,
        dominant_label=price_state_label(state),
        dominant_amount=dominant_amount,
        international=offer.international,
        shipping_material=offer.shipping_material,
        breakdown_lines=_breakdown_lines(offer, shipping, taxes, imports, state, dominant_amount),
    )
    return ProductCardView(
        product_id=offer.product_id,
        brand=offer.brand,
        model=offer.model,
        category=offer.category,
        merchant=offer.merchant,
        offer_url=offer.offer_url,
        image_key=offer.image_key,
        tags=offer.tags,
        piqscore=PiqScoreView(
            value=offer.piqscore,
            descriptor=piqscore_descriptor(offer.piqscore),
            percentile_label=offer.percentile_label,
            snapshot_sha256=offer.piqscore_sha256,
        ),
        economics=economics,
        is_best_piq=offer.product_id == decision.best_piq_product_id,
        is_highest_piqscore=offer.product_id == highest_id,
        is_qualified=(decision.why_variant == "qualified" or qualify_recommendation)
        and offer.product_id == decision.best_piq_product_id,
        alternative_badge=offer.alternative_badge,
        alternative_reason=offer.alternative_reason,
        compact_breakdown=_compact_breakdown(offer, shipping),
        why_it_won=offer.why_it_won,
        freshness_label=offer.freshness_label,
        origin_label=offer.origin_label,
    )


def _breakdown_lines(
    offer: FixtureOffer,
    shipping: MoneyComponent,
    taxes: MoneyComponent,
    imports: MoneyComponent | None,
    state: str,
    dominant_amount: float | None,
) -> tuple[tuple[str, str, str], ...]:
    lines: list[tuple[str, str, str]] = []
    listing_label = offer.listing.label
    lines.append(
        (listing_label, format_money(offer.listing.amount, offer.listing.currency), "neutral")
    )
    if offer.voucher is not None:
        tone = "positive" if offer.voucher.status == "verified" else "muted"
        if offer.voucher.status == "verified":
            display = signed_money(offer.voucher.amount, offer.voucher.currency)
        else:
            display = offer.voucher.status.replace("_", " ")
        if offer.voucher.status == "unverified":
            display = "Not applied"
            tone = "warn"
        elif offer.voucher.status in {"expired", "unsupported"}:
            display = offer.voucher.status.title()
            tone = "muted"
            display = "Not applied"
        lines.append((offer.voucher.label, display, tone))
    lines.append((shipping.label, shipping_display(shipping), _tone_for_shipping(shipping)))
    if offer.international and imports is not None:
        lines.append((imports.label, tax_display(imports), _tone_for_shipping(imports)))
    else:
        lines.append((taxes.label, tax_display(taxes), _tone_for_tax(taxes)))
    lines.append(
        (
            price_state_label(state),
            format_money(dominant_amount, offer.listing.currency),
            _tone_for_state(state),
        )
    )
    return tuple(lines)


def _tone_for_state(state: str) -> str:
    if state in {
        "price_before_shipping",
        "before_unverified_import_charges",
        "potential_checkout_price",
    }:
        return "warn"
    return "positive"


def _tone_for_shipping(component: MoneyComponent) -> str:
    if component.is_unknown or component.status in {"unverified", "unknown"}:
        return "warn"
    if component.amount == 0:
        return "positive"
    if component.is_estimate:
        return "warn"
    return "neutral"


def _tone_for_tax(component: MoneyComponent) -> str:
    if component.status == "not_applicable":
        return "muted"
    if component.is_unknown or component.status in {"unverified", "unknown"}:
        return "warn"
    return "neutral"


def _compact_breakdown(offer: FixtureOffer, shipping: MoneyComponent) -> str:
    parts = [format_money(offer.listing.amount, offer.listing.currency)]
    if offer.voucher is not None and offer.voucher.status == "verified" and offer.voucher.amount:
        parts.append(f"{signed_money(offer.voucher.amount, offer.voucher.currency)} voucher")
    if shipping.is_unknown:
        parts.append("shipping not verified")
    elif shipping.amount == 0 and shipping.status == "verified":
        parts.append("FREE shipping")
    elif shipping.amount is not None:
        parts.append(f"{format_money(shipping.amount, shipping.currency)} shipping")
    return " · ".join(parts) if len(parts) == 1 else f"{parts[0]} − " + " + ".join(parts[1:])


def _why_fits(decision: FixtureDecision, location: DeliveryContext, best: ProductCardView) -> str:
    delivery = location.display_place if location.is_known else "your area"
    return (
        f"Best match for your {decision.shopper_budget} budget, "
        f"{decision.shopper_priority.casefold()} priority, and delivery to {delivery}."
    )


def _why_sections(
    decision: FixtureDecision,
    location: DeliveryContext,
    *,
    qualify_recommendation: bool = False,
    qualified_message: str | None = None,
) -> tuple[WhySectionView, ...]:
    delivery = location.display_place if location.is_known else "your area"
    narrative = decision.why_recommend.format(
        budget=decision.shopper_budget,
        priority=decision.shopper_priority,
        delivery=delivery,
    )
    context_bullets = (
        ("budget", f"Budget: {decision.shopper_budget}"),
        ("priority", f"Top priority: {decision.shopper_priority}"),
        ("use", f"Use case: {decision.shopper_use_case}"),
        ("delivery", f"Delivery to: {delivery if location.is_known else 'Not set'}"),
        ("urgency", f"Urgency: {decision.shopper_urgency}"),
    )
    callout = decision.score_diff_callout
    callout_tone = "info"
    if decision.qualified_callout:
        callout = decision.qualified_callout
        callout_tone = "warn"
    if qualify_recommendation and qualified_message:
        callout = qualified_message
        callout_tone = "warn"
    unknowns = _unknowns_for_location(decision, location, qualify_recommendation)
    return (
        WhySectionView(
            number=1,
            title="Why PiqSavi recommends this",
            narrative=narrative,
            bullets=context_bullets,
            callout=callout,
            callout_tone=callout_tone,
        ),
        WhySectionView(
            number=2,
            title="What to know before you buy",
            narrative="",
            bullets=tuple(("check", item) for item in decision.why_know),
        ),
        WhySectionView(
            number=3,
            title="Best for",
            narrative="",
            bullets=tuple(("check", item) for item in decision.why_best_for),
        ),
        WhySectionView(
            number=4,
            title="When an alternative may be better",
            narrative="",
            bullets=tuple(("alt", item) for item in decision.why_alternatives),
        ),
        WhySectionView(
            number=5,
            title="What PiqSavi considered",
            narrative="",
            bullets=(),
            extra={
                "categories": decision.evidence_categories,
                "sources": decision.sources,
            },
        ),
        WhySectionView(
            number=6,
            title="What we don’t know",
            narrative="",
            bullets=tuple(("warn", item) for item in unknowns),
        ),
    )


def _ask_placeholder(page: PageName) -> str:
    if page == "compare":
        return "Ask about this comparison..."
    if page == "why":
        return "Ask about this recommendation..."
    return "Ask about the results..."


def _ask_suggestions(
    page: PageName,
    decision: FixtureDecision,
    cards: tuple[ProductCardView, ...],
) -> tuple[str, ...]:
    alts = [card for card in cards if not card.is_best_piq]
    beat = alts[0].brand if alts else "the alternative"
    suggestions = [
        f"Why did this beat {beat}?",
        "Does this price include shipping?",
        "What if comfort matters more?",
        "What if I deliver this to Cebu?",
    ]
    merchants = {card.merchant for card in cards}
    if "Lazada" in merchants:
        suggestions.insert(2, "Why is the Lazada price lower?")
    if any(card.economics.international for card in cards) or "Amazon US" in merchants:
        suggestions.append("Why is Amazon more expensive?")
        suggestions.append("Does this include import charges?")
    if page == "compare":
        suggestions = [
            "Why is Amazon more expensive?" if "Amazon US" in merchants else suggestions[0],
            "Lowest final cost?",
            "What if comfort matters more?",
            "What if I deliver this to Cebu?",
        ]
    return tuple(suggestions[:6])


def _pay_rows(
    cards: tuple[ProductCardView, ...],
    location: DeliveryContext,
) -> tuple[CompareFitRow, ...]:
    dest = location.display_place if location.is_known else "your area"
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
            tuple(_listing_compare_cell(card) for card in cards),
        ),
        CompareFitRow(
            f"Shipping to {dest}" if location.is_known else "Shipping",
            tuple(shipping_display(card.economics.shipping) for card in cards),
        ),
        CompareFitRow(
            "Taxes / import charges",
            tuple(_tax_compare_cell(card) for card in cards),
        ),
    )


def _listing_compare_cell(card: ProductCardView) -> str:
    listing = card.economics.listing
    base = format_money(listing.amount, listing.currency)
    voucher = card.economics.voucher
    if voucher is not None and voucher.status == "verified" and voucher.amount:
        return f"{base} · {signed_money(voucher.amount, voucher.currency)} voucher"
    return base


def _tax_compare_cell(card: ProductCardView) -> str:
    if card.economics.import_charges is not None:
        return tax_display(card.economics.import_charges)
    return tax_display(card.economics.taxes)


def _fit_rows(cards: tuple[ProductCardView, ...]) -> tuple[CompareFitRow, ...]:
    from app.consumer.fixtures import CATALOG

    # Fit values live on fixture offers; look up by product_id.
    offers = {offer.product_id: offer for decision in CATALOG.values() for offer in decision.offers}
    keys = (
        ("Comfort", "stars"),
        ("Sound quality", "stars"),
        ("Noise cancellation", "stars"),
        ("Battery life", "text"),
        ("Warranty", "text"),
        ("Seller reliability", "text"),
    )
    rows: list[CompareFitRow] = []
    for label, kind in keys:
        values = []
        for card in cards:
            offer = offers.get(card.product_id)
            values.append(offer.fit.get(label, "—") if offer else "—")
        rows.append(CompareFitRow(label, tuple(values), kind=kind))  # type: ignore[arg-type]
    return tuple(rows)
