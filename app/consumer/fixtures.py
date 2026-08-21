"""Explicit non-live Product Foundation presentation fixtures.

These records are labeled demo data. They do not invent live merchant economics.
PiqScore and Best Piq values are captured constants, not frontend calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from app.consumer.pricing import MoneyComponent
from app.consumer.view_models import WhyVariant

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64
SHA_G = "g" * 64
SHA_H = "h" * 64

AFFILIATE_DISCLOSURE = (
    "PiqSavi may earn a commission if you purchase through an eligible link. "
    "This does not affect PiqScore or recommendation ranking."
)
FRESHNESS_DISCLAIMER = (
    "Prices and availability may change. We show the best options we can access "
    "at the time of your search."
)
DATA_CLASSIFICATION = "non_live_contract_fixture"


@dataclass(frozen=True, slots=True)
class FixtureOffer:
    product_id: str
    brand: str
    model: str
    category: str
    merchant: str
    offer_url: str
    image_key: str
    tags: tuple[str, ...]
    piqscore: float
    percentile_label: str | None
    piqscore_sha256: str
    listing: MoneyComponent
    voucher: MoneyComponent | None
    shipping: MoneyComponent
    taxes: MoneyComponent
    import_charges: MoneyComponent | None
    international: bool
    shipping_material: bool
    alternative_badge: str | None
    alternative_reason: str
    why_it_won: tuple[str, ...]
    freshness_label: str | None
    origin_label: str | None
    fit: dict[str, str]


@dataclass(frozen=True, slots=True)
class FixtureDecision:
    catalog_id: str
    decision_id: str
    query_label: str
    evaluated_count: int
    why_variant: WhyVariant
    best_piq_product_id: str
    recommendation_decision: str
    recommendation_sha256: str
    piqscore_set_sha256: str
    offers: tuple[FixtureOffer, ...]
    shopper_budget: str
    shopper_priority: str
    shopper_use_case: str
    shopper_urgency: str
    evidence_categories: tuple[tuple[str, str], ...]
    sources: tuple[str, ...]
    unknowns: tuple[str, ...]
    why_recommend: str
    why_know: tuple[str, ...]
    why_best_for: tuple[str, ...]
    why_alternatives: tuple[str, ...]
    score_diff_callout: str | None = None
    qualified_callout: str | None = None
    destination_aliases: tuple[str, ...] = ()
    changes_recommendation: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def _php_listing(amount: float, label: str = "Listing price") -> MoneyComponent:
    return MoneyComponent(kind="listing", label=label, amount=amount, status="verified")


def _voucher(amount: float, label: str, status: str = "verified") -> MoneyComponent:
    return MoneyComponent(
        kind="voucher",
        label=label,
        amount=-abs(amount),
        status=status,  # type: ignore[arg-type]
        applies=status == "verified",
    )


def _shipping(
    amount: float | None,
    *,
    status: str = "verified",
    label: str = "Shipping",
) -> MoneyComponent:
    return MoneyComponent(
        kind="shipping",
        label=label,
        amount=amount,
        status=status,  # type: ignore[arg-type]
    )


def _tax(status: str = "not_applicable", amount: float | None = None) -> MoneyComponent:
    return MoneyComponent(
        kind="tax",
        label="Taxes / duties",
        amount=amount,
        status=status,  # type: ignore[arg-type]
    )


def _import(amount: float | None, status: str = "estimated") -> MoneyComponent:
    return MoneyComponent(
        kind="import",
        label="Estimated import charges",
        amount=amount,
        status=status,  # type: ignore[arg-type]
    )


def _sony_local(**overrides: Any) -> FixtureOffer:
    base = FixtureOffer(
        product_id="sony-wh-1000xm5-lazada",
        brand="Sony",
        model="WH-1000XM5",
        category="Wireless Noise Cancelling Headphones",
        merchant="Lazada",
        offer_url="https://www.lazada.com.ph/example-sony-wh-1000xm5",
        image_key="sony-xm5",
        tags=("Excellent sound", "All-day comfort", "Strong ANC"),
        piqscore=92,
        percentile_label="Top 5% of options",
        piqscore_sha256=SHA_A,
        listing=_php_listing(19990),
        voucher=_voucher(1000, "Public voucher (10% off)"),
        shipping=_shipping(0.0),
        taxes=_tax("not_applicable"),
        import_charges=None,
        international=False,
        shipping_material=True,
        alternative_badge=None,
        alternative_reason="",
        why_it_won=(
            "Excellent noise cancellation",
            "Premium sound and comfort",
            "Strong overall value",
        ),
        freshness_label="Checked 2 hours ago",
        origin_label=None,
        fit={
            "Comfort": "4",
            "Sound quality": "5",
            "Noise cancellation": "5",
            "Battery life": "Up to 30 hrs",
            "Warranty": "1 year local warranty",
            "Seller reliability": "High",
        },
    )
    return replace(base, **overrides) if overrides else base


def _bose_local(**overrides: Any) -> FixtureOffer:
    base = FixtureOffer(
        product_id="bose-qc45-lazada",
        brand="Bose",
        model="QuietComfort 45",
        category="Wireless Noise Cancelling Headphones",
        merchant="Lazada",
        offer_url="https://www.lazada.com.ph/example-bose-qc45",
        image_key="bose-qc45",
        tags=("All-day comfort", "Balanced sound"),
        piqscore=88,
        percentile_label=None,
        piqscore_sha256=SHA_B,
        listing=_php_listing(16490),
        voucher=_voucher(800, "Public voucher"),
        shipping=_shipping(300),
        taxes=_tax("not_applicable"),
        import_charges=None,
        international=False,
        shipping_material=True,
        alternative_badge="Best value",
        alternative_reason=("Saves ₱3,000 vs your Best Piq while still offering strong comfort."),
        why_it_won=("All-day comfort", "Strong value", "Reliable ANC"),
        freshness_label="Checked 2 hours ago",
        origin_label=None,
        fit={
            "Comfort": "5",
            "Sound quality": "4",
            "Noise cancellation": "4",
            "Battery life": "Up to 24 hrs",
            "Warranty": "1 year local warranty",
            "Seller reliability": "High",
        },
    )
    return replace(base, **overrides) if overrides else base


def _sennheiser(**overrides: Any) -> FixtureOffer:
    base = FixtureOffer(
        product_id="sennheiser-momentum-4-digital-walker",
        brand="Sennheiser",
        model="Momentum 4 Wireless",
        category="Wireless Noise Cancelling Headphones",
        merchant="Digital Walker",
        offer_url="https://www.digitalwalker.com.ph/example-momentum-4",
        image_key="sennheiser-m4",
        tags=("Great sound", "Great ANC"),
        piqscore=86,
        percentile_label=None,
        piqscore_sha256=SHA_C,
        listing=_php_listing(17990),
        voucher=_voucher(500, "Public voucher"),
        shipping=_shipping(0.0),
        taxes=_tax("not_applicable"),
        import_charges=None,
        international=False,
        shipping_material=True,
        alternative_badge="Best for sound",
        alternative_reason="Richer, more detailed sound signature for music lovers.",
        why_it_won=("Natural sound", "Long battery", "Comfortable fit"),
        freshness_label="Checked 3 hours ago",
        origin_label=None,
        fit={
            "Comfort": "4",
            "Sound quality": "5",
            "Noise cancellation": "4",
            "Battery life": "Up to 60 hrs",
            "Warranty": "1 year local warranty",
            "Seller reliability": "High",
        },
    )
    return replace(base, **overrides) if overrides else base


def _sony_budget(**overrides: Any) -> FixtureOffer:
    base = FixtureOffer(
        product_id="sony-wh-ch720n-lazada",
        brand="Sony",
        model="WH-CH720N",
        category="Wireless Noise Cancelling Headphones",
        merchant="Lazada",
        offer_url="https://www.lazada.com.ph/example-sony-ch720n",
        image_key="sony-ch720n",
        tags=("Reliable ANC", "Long battery"),
        piqscore=82,
        percentile_label=None,
        piqscore_sha256=SHA_D,
        listing=_php_listing(10490),
        voucher=_voucher(500, "Public voucher"),
        shipping=_shipping(0.0),
        taxes=_tax("not_applicable"),
        import_charges=None,
        international=False,
        shipping_material=True,
        alternative_badge="Best budget",
        alternative_reason="Lowest total cost with reliable ANC and long battery life.",
        why_it_won=("Low delivered cost", "Reliable ANC", "Long battery"),
        freshness_label="Checked 2 hours ago",
        origin_label=None,
        fit={
            "Comfort": "3",
            "Sound quality": "4",
            "Noise cancellation": "3",
            "Battery life": "Up to 35 hrs",
            "Warranty": "1 year local warranty",
            "Seller reliability": "High",
        },
    )
    return replace(base, **overrides) if overrides else base


def _amazon_bose(**overrides: Any) -> FixtureOffer:
    base = FixtureOffer(
        product_id="bose-qc45-amazon-us",
        brand="Bose",
        model="QuietComfort 45",
        category="Wireless Noise Cancelling Headphones",
        merchant="Amazon US",
        offer_url="https://www.amazon.com/example-bose-qc45",
        image_key="bose-qc45",
        tags=("All-day comfort", "Strong comfort"),
        piqscore=83,
        percentile_label=None,
        piqscore_sha256=SHA_E,
        listing=MoneyComponent(
            kind="listing",
            label="Item price",
            amount=16500,
            status="verified",
        ),
        voucher=None,
        shipping=_shipping(1800, status="estimated", label="International shipping"),
        taxes=_tax("not_applicable"),
        import_charges=_import(1950, "estimated"),
        international=True,
        shipping_material=True,
        alternative_badge="Amazon US",
        alternative_reason=(
            "Cross-border option. Compare estimated landed cost, not the raw item price."
        ),
        why_it_won=("Comfort-first fit", "Known US listing price", "Estimated import shown"),
        freshness_label="Checked 4 hours ago",
        origin_label="Amazon US",
        fit={
            "Comfort": "5",
            "Sound quality": "4",
            "Noise cancellation": "4",
            "Battery life": "Up to 24 hrs",
            "Warranty": "30-day Amazon US returns",
            "Seller reliability": "High",
        },
    )
    return replace(base, **overrides) if overrides else base


def _amazon_sony(**overrides: Any) -> FixtureOffer:
    return _amazon_bose(
        product_id="sony-wh-1000xm5-amazon-us",
        brand="Sony",
        model="WH-1000XM5",
        image_key="sony-xm5",
        tags=("Excellent sound", "Strong ANC"),
        piqscore=82,
        percentile_label=None,
        piqscore_sha256=SHA_F,
        listing=MoneyComponent(
            kind="listing",
            label="Item price",
            amount=16500,
            status="verified",
        ),
        alternative_badge="Amazon US",
        alternative_reason="Estimated landed cost includes shipping and import charges.",
        **overrides,
    )


def _soundcore(**overrides: Any) -> FixtureOffer:
    base = FixtureOffer(
        product_id="soundcore-space-q45-shopee",
        brand="Soundcore",
        model="Space Q45",
        category="Wireless Noise Cancelling Headphones",
        merchant="Shopee",
        offer_url="https://shopee.ph/example-soundcore-q45",
        image_key="soundcore-q45",
        tags=("Budget ANC", "Light build"),
        piqscore=74,
        percentile_label=None,
        piqscore_sha256=SHA_G,
        listing=_php_listing(7499),
        voucher=None,
        shipping=_shipping(None, status="unknown"),
        taxes=_tax("unknown"),
        import_charges=None,
        international=False,
        shipping_material=True,
        alternative_badge=None,
        alternative_reason="",
        why_it_won=("Fits the budget", "Known listing price", "Comfortable for the price"),
        freshness_label="Checked 5 hours ago",
        origin_label=None,
        fit={
            "Comfort": "3",
            "Sound quality": "3",
            "Noise cancellation": "3",
            "Battery life": "Up to 50 hrs",
            "Warranty": "1 year local warranty",
            "Seller reliability": "Medium",
        },
    )
    return replace(base, **overrides) if overrides else base


_STANDARD_SOURCES = ("Lazada", "Reddit", "YouTube", "Sony Official")
_STANDARD_CATEGORIES = (
    ("Product quality", "verified"),
    ("Price & value", "verified"),
    ("Shipping", "verified"),
    ("Seller reliability", "verified"),
    ("Warranty / returns", "verified"),
    ("Taxes / duties", "not_applicable"),
)
_STANDARD_UNKNOWNS = (
    "Account-specific vouchers were not included",
    "Seller stock levels may change",
    "Future prices cannot be predicted",
    "Shopee offer data was not available for this decision",
)
_STANDARD_KNOW = (
    "1-year local warranty",
    "Ships from the Philippines",
    "2–4 day returns on this offer",
    "Promo price may end soon",
    "Stock levels may change",
)
_STANDARD_BEST_FOR = (
    "Comfort-first users",
    "Long flights and commutes",
    "Strong ANC performance",
    "Balanced sound quality",
    "Shoppers prioritizing total delivered value",
)
_STANDARD_ALTS = (
    "Choose Bose if comfort matters more than maximum ANC.",
    "Choose Sennheiser Momentum 4 for a more natural sound.",
    (
        "Choose Amazon US only if landed cost is significantly lower "
        "and cross-border returns are acceptable."
    ),
)


def _standard_decision() -> FixtureDecision:
    sony = _sony_local()
    bose = _bose_local()
    senn = _sennheiser()
    budget = _sony_budget()
    return FixtureDecision(
        catalog_id="headphones-standard",
        decision_id="headphones-standard",
        query_label="Wireless Noise Cancelling Headphones",
        evaluated_count=26,
        why_variant="standard",
        best_piq_product_id=sony.product_id,
        recommendation_decision="buy",
        recommendation_sha256=SHA_H,
        piqscore_set_sha256=SHA_A,
        offers=(sony, bose, senn, budget),
        shopper_budget="Up to ₱30,000",
        shopper_priority="Comfort",
        shopper_use_case="Travel • Work • Everyday",
        shopper_urgency="Normal",
        evidence_categories=_STANDARD_CATEGORIES,
        sources=_STANDARD_SOURCES,
        unknowns=_STANDARD_UNKNOWNS,
        why_recommend=(
            "This offer is the best match for your {budget} budget, {priority} priority, "
            "and delivery to {delivery}."
        ),
        why_know=_STANDARD_KNOW,
        why_best_for=_STANDARD_BEST_FOR,
        why_alternatives=_STANDARD_ALTS,
        destination_aliases=("taguig", "taguig-city", "taguig-city-1630"),
    )


def _score_diff_decision() -> FixtureDecision:
    bose = _bose_local(
        piqscore=90,
        listing=_php_listing(19990),
        voucher=_voucher(1000, "Public voucher (10% off)"),
        shipping=_shipping(0.0),
        alternative_badge=None,
        alternative_reason="",
    )
    sony = _sony_local(
        piqscore=93,
        percentile_label="Top 3% of options",
        alternative_badge=None,
        alternative_reason="Highest objective PiqScore in this evaluated set.",
        listing=_php_listing(20990),
        voucher=_voucher(1000, "Public voucher"),
        shipping=_shipping(0.0),
    )
    senn = _sennheiser()
    amazon = _amazon_bose()
    return FixtureDecision(
        catalog_id="headphones-score-diff",
        decision_id="headphones-score-diff",
        query_label="Wireless Noise Cancelling Headphones",
        evaluated_count=4,
        why_variant="score_diff",
        best_piq_product_id=bose.product_id,
        recommendation_decision="buy",
        recommendation_sha256=SHA_H,
        piqscore_set_sha256=SHA_B,
        offers=(bose, sony, senn, amazon),
        shopper_budget="Up to ₱20,000",
        shopper_priority="Comfort",
        shopper_use_case="Travel • Work • Everyday",
        shopper_urgency="Normal",
        evidence_categories=_STANDARD_CATEGORIES,
        sources=_STANDARD_SOURCES,
        unknowns=_STANDARD_UNKNOWNS,
        why_recommend=(
            "Bose is the best match for your {budget} budget and {priority} priority "
            "with delivery to {delivery}."
        ),
        why_know=_STANDARD_KNOW,
        why_best_for=_STANDARD_BEST_FOR,
        why_alternatives=_STANDARD_ALTS,
        score_diff_callout=(
            "Sony has the highest objective PiqScore at 93. Bose is your Best Piq for You "
            "because comfort is your highest priority and its delivered cost remains competitive."
        ),
        destination_aliases=("taguig", "taguig-city", "taguig-city-1630"),
    )


def _cross_border_decision() -> FixtureDecision:
    sony_us = _amazon_sony()
    bose = _bose_local()
    senn = _sennheiser()
    budget = _sony_budget()
    return FixtureDecision(
        catalog_id="headphones-cross-border",
        decision_id="headphones-cross-border",
        query_label="Wireless Noise Cancelling Headphones",
        evaluated_count=4,
        why_variant="cross_border",
        best_piq_product_id=sony_us.product_id,
        recommendation_decision="consider",
        recommendation_sha256=SHA_H,
        piqscore_set_sha256=SHA_F,
        offers=(sony_us, bose, senn, budget),
        shopper_budget="Up to ₱20,000",
        shopper_priority="Comfort",
        shopper_use_case="Travel • Work • Everyday",
        shopper_urgency="Normal",
        evidence_categories=(
            ("Product quality", "verified"),
            ("Price & value", "verified"),
            ("Shipping", "verified"),
            ("Seller reliability", "verified"),
            ("Warranty / returns", "verified"),
            ("Taxes / duties", "estimated"),
        ),
        sources=("Amazon US", "Reddit", "YouTube", "Sony Official"),
        unknowns=(
            "Import charges are estimates, not a customs invoice",
            "Account-specific vouchers were not included",
            "Seller stock levels may change",
            "Future prices cannot be predicted",
        ),
        why_recommend=(
            "This cross-border offer is presented using estimated landed cost for delivery "
            "to {delivery}, not the raw international item price."
        ),
        why_know=(
            "Item price is the international listing, not the delivered cost",
            "International shipping is estimated",
            "Import charges are estimated",
            "Cross-border returns take longer than local marketplace returns",
            "Stock levels may change",
        ),
        why_best_for=_STANDARD_BEST_FOR,
        why_alternatives=_STANDARD_ALTS,
        destination_aliases=("taguig", "taguig-city", "taguig-city-1630"),
    )


def _qualified_decision() -> FixtureDecision:
    soundcore = _soundcore()
    bose = _bose_local()
    senn = _sennheiser()
    budget = _sony_budget()
    return FixtureDecision(
        catalog_id="headphones-qualified",
        decision_id="headphones-qualified",
        query_label="Wireless Noise Cancelling Headphones",
        evaluated_count=4,
        why_variant="qualified",
        best_piq_product_id=soundcore.product_id,
        recommendation_decision="consider",
        recommendation_sha256=SHA_H,
        piqscore_set_sha256=SHA_G,
        offers=(soundcore, bose, senn, budget),
        shopper_budget="Up to ₱20,000",
        shopper_priority="Comfort",
        shopper_use_case="Travel • Work • Everyday",
        shopper_urgency="Normal",
        evidence_categories=(
            ("Product quality", "verified"),
            ("Price & value", "verified"),
            ("Shipping", "unknown"),
            ("Seller reliability", "verified"),
            ("Warranty / returns", "verified"),
            ("Taxes / duties", "unknown"),
        ),
        sources=("Shopee",),
        unknowns=(
            "Shipping to the selected area is not verified",
            "Taxes / duties are not verified",
            "Account-specific vouchers were not included",
            "Seller stock levels may change",
        ),
        why_recommend=(
            "This is a qualified Best Piq because shipping to {delivery} is not yet verified "
            "and could change the recommendation."
        ),
        why_know=_STANDARD_KNOW,
        why_best_for=_STANDARD_BEST_FOR,
        why_alternatives=_STANDARD_ALTS,
        qualified_callout=(
            "Shipping to this delivery area is not yet verified and may be significant. "
            "The recommendation may change once shipping is known."
        ),
        destination_aliases=("taguig", "taguig-city", "taguig-city-1630"),
    )


def _cebu_decision() -> FixtureDecision:
    """Explicit destination snapshot. Not a frontend recompute of Best Piq."""
    bose = _bose_local(
        piqscore=90,
        listing=_php_listing(16490),
        voucher=_voucher(800, "Public voucher"),
        shipping=_shipping(0.0),
        alternative_badge=None,
        alternative_reason="",
        why_it_won=(
            "Verified delivered cost for Cebu City",
            "Comfort-first fit",
            "Competitive total value",
        ),
    )
    sony = _sony_local(
        shipping=_shipping(450),
        alternative_badge=None,
        alternative_reason="Still excellent ANC, with paid shipping to Cebu City.",
    )
    senn = _sennheiser(shipping=_shipping(350))
    budget = _sony_budget()
    return FixtureDecision(
        catalog_id="headphones-cebu",
        decision_id="headphones-cebu",
        query_label="Wireless Noise Cancelling Headphones",
        evaluated_count=26,
        why_variant="standard",
        best_piq_product_id=bose.product_id,
        recommendation_decision="buy",
        recommendation_sha256=SHA_C,
        piqscore_set_sha256=SHA_B,
        offers=(bose, sony, senn, budget),
        shopper_budget="Up to ₱30,000",
        shopper_priority="Comfort",
        shopper_use_case="Travel • Work • Everyday",
        shopper_urgency="Normal",
        evidence_categories=_STANDARD_CATEGORIES,
        sources=_STANDARD_SOURCES,
        unknowns=_STANDARD_UNKNOWNS,
        why_recommend=(
            "This offer now has the strongest fit and verified delivered cost for {delivery}."
        ),
        why_know=_STANDARD_KNOW,
        why_best_for=_STANDARD_BEST_FOR,
        why_alternatives=_STANDARD_ALTS,
        destination_aliases=("cebu", "cebu-city", "cebu-city-6000"),
        changes_recommendation=True,
        extra={
            "changed_from_catalog": "headphones-standard",
            "changed_message": (
                "Your recommendation changed. This offer now has the strongest fit "
                "and verified delivered cost for {delivery}."
            ),
        },
    )


def _import_unverified_decision() -> FixtureDecision:
    sony_us = _amazon_sony(
        import_charges=_import(None, "unknown"),
        shipping=_shipping(1800, status="estimated", label="International shipping"),
    )
    bose = _bose_local()
    senn = _sennheiser()
    budget = _sony_budget()
    return FixtureDecision(
        catalog_id="headphones-import-unverified",
        decision_id="headphones-import-unverified",
        query_label="Wireless Noise Cancelling Headphones",
        evaluated_count=4,
        why_variant="cross_border",
        best_piq_product_id=sony_us.product_id,
        recommendation_decision="consider",
        recommendation_sha256=SHA_H,
        piqscore_set_sha256=SHA_F,
        offers=(sony_us, bose, senn, budget),
        shopper_budget="Up to ₱20,000",
        shopper_priority="Comfort",
        shopper_use_case="Travel • Work • Everyday",
        shopper_urgency="Normal",
        evidence_categories=(
            ("Product quality", "verified"),
            ("Price & value", "verified"),
            ("Shipping", "verified"),
            ("Taxes / duties", "unknown"),
        ),
        sources=("Amazon US",),
        unknowns=("Import charges are not verified",),
        why_recommend="International item price is shown before unverified import charges.",
        why_know=("Import charges could change the delivered cost",),
        why_best_for=_STANDARD_BEST_FOR,
        why_alternatives=_STANDARD_ALTS,
        destination_aliases=("taguig", "taguig-city", "taguig-city-1630"),
    )


def _potential_checkout_decision() -> FixtureDecision:
    sony = _sony_local(
        voucher=_voucher(1000, "Unverified checkout voucher", status="unverified"),
    )
    bose = _bose_local()
    senn = _sennheiser()
    budget = _sony_budget()
    return FixtureDecision(
        catalog_id="headphones-potential-checkout",
        decision_id="headphones-potential-checkout",
        query_label="Wireless Noise Cancelling Headphones",
        evaluated_count=4,
        why_variant="standard",
        best_piq_product_id=sony.product_id,
        recommendation_decision="consider",
        recommendation_sha256=SHA_H,
        piqscore_set_sha256=SHA_A,
        offers=(sony, bose, senn, budget),
        shopper_budget="Up to ₱30,000",
        shopper_priority="Comfort",
        shopper_use_case="Travel • Work • Everyday",
        shopper_urgency="Normal",
        evidence_categories=_STANDARD_CATEGORIES,
        sources=("Lazada",),
        unknowns=("Checkout voucher is not verified",),
        why_recommend="A possible checkout saving is shown separately because it is not verified.",
        why_know=("Unverified checkout prices can change at payment",),
        why_best_for=_STANDARD_BEST_FOR,
        why_alternatives=_STANDARD_ALTS,
        destination_aliases=("taguig", "taguig-city", "taguig-city-1630"),
    )


def _negative_voucher_examples() -> dict[str, FixtureOffer]:
    return {
        "expired": _sony_local(
            product_id="sony-expired-voucher",
            voucher=_voucher(1000, "Expired public voucher", status="expired"),
        ),
        "unsupported": _sony_local(
            product_id="sony-unsupported-voucher",
            voucher=_voucher(1000, "Unsupported voucher", status="unsupported"),
        ),
    }


CATALOG: dict[str, FixtureDecision] = {
    decision.catalog_id: decision
    for decision in (
        _standard_decision(),
        _score_diff_decision(),
        _cross_border_decision(),
        _qualified_decision(),
        _cebu_decision(),
        _import_unverified_decision(),
        _potential_checkout_decision(),
    )
}

DEFAULT_CATALOG_ID = "headphones-standard"
FAMILY_TO_DESTINATION = {
    "headphones-standard": {"cebu": "headphones-cebu", "cebu-city": "headphones-cebu"},
}


def get_decision(catalog_id: str) -> FixtureDecision:
    if catalog_id not in CATALOG:
        raise KeyError(catalog_id)
    return CATALOG[catalog_id]


def resolve_catalog_id(decision_id: str) -> str:
    if decision_id in CATALOG:
        return decision_id
    raise KeyError(decision_id)


def destination_catalog(current_id: str, destination_key: str) -> str:
    """Return an explicit fixture id for a known destination family, else current."""
    family = FAMILY_TO_DESTINATION.get(current_id, {})
    slug = destination_key
    for alias, catalog_id in family.items():
        if slug == alias or slug.startswith(f"{alias}-"):
            return catalog_id
    for decision in CATALOG.values():
        if (
            destination_key in decision.destination_aliases
            and current_id == "headphones-standard"
            and decision.catalog_id == "headphones-cebu"
        ):
            return decision.catalog_id
    return current_id
