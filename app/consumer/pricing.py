"""Presentation-only price-state selection from already-captured offer economics.

Does not calculate PiqScore, Recommendation, or landed-cost estimates. Unknown
components stay unknown. Expired and unsupported savings are not applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PriceState = Literal[
    "final_effective_cost",
    "estimated_landed_cost",
    "price_before_shipping",
    "before_unverified_import_charges",
    "potential_checkout_price",
]

ComponentKind = Literal[
    "listing",
    "discount",
    "voucher",
    "shipping",
    "tax",
    "import",
    "other",
]
ComponentStatus = Literal[
    "verified",
    "estimated",
    "unknown",
    "not_applicable",
    "expired",
    "unsupported",
    "unverified",
]

PRICE_STATE_LABELS: dict[PriceState, str] = {
    "final_effective_cost": "Final effective cost",
    "estimated_landed_cost": "Estimated landed cost",
    "price_before_shipping": "Price before shipping",
    "before_unverified_import_charges": "Before unverified import charges",
    "potential_checkout_price": "Potential checkout price",
}


@dataclass(frozen=True, slots=True)
class MoneyComponent:
    """One captured price line. amount is None when the value is unknown."""

    kind: ComponentKind
    label: str
    amount: float | None
    currency: str = "PHP"
    status: ComponentStatus = "verified"
    applies: bool = True

    @property
    def is_unknown(self) -> bool:
        return self.status == "unknown" or (self.applies and self.amount is None)

    @property
    def is_estimate(self) -> bool:
        return self.status == "estimated"

    @property
    def may_reduce_price(self) -> bool:
        return self.kind in {"discount", "voucher"} and self.status == "verified" and self.applies


def format_money(amount: float | None, currency: str | None = None) -> str:
    """Format an already-known amount in its source currency.

    Does not convert currencies. Missing amounts stay Unknown. PHP keeps the
    existing peso glyph; other codes render as ``1,299 USD``.
    """

    if amount is None:
        return "Unknown"
    code = (currency or "").strip().upper()
    rounded = round(amount)
    formatted = f"{rounded:,.0f}" if abs(amount - rounded) < 0.005 else f"{amount:,.2f}"
    if code == "PHP":
        return f"₱{formatted}"
    if code:
        return f"{formatted} {code}"
    return formatted


def format_php(amount: float | None) -> str:
    """PHP display helper. Prefer ``format_money`` when the source currency is known."""

    return format_money(amount, "PHP")


def signed_money(
    amount: float | None,
    currency: str | None = None,
    *,
    unknown_label: str = "Unknown",
) -> str:
    if amount is None:
        return unknown_label
    if amount < 0:
        return f"-{format_money(abs(amount), currency)}"
    return format_money(amount, currency)


def signed_php(amount: float | None, *, unknown_label: str = "Unknown") -> str:
    return signed_money(amount, "PHP", unknown_label=unknown_label)


def shipping_display(component: MoneyComponent) -> str:
    if component.status == "not_applicable":
        return "Not applicable"
    if component.is_unknown or component.status in {"unverified", "unknown"}:
        return "Not verified"
    if component.amount is None:
        return "Not verified"
    if component.amount == 0 and component.status == "verified":
        return "FREE"
    prefix = "+" if component.kind in {"shipping", "tax", "import", "other"} else ""
    estimate = " est." if component.is_estimate else ""
    return f"{prefix}{format_money(component.amount, component.currency)}{estimate}"


def tax_display(component: MoneyComponent) -> str:
    if component.status == "not_applicable":
        return "Not applicable"
    if component.is_unknown or component.status in {"unverified", "unknown"}:
        return "Not verified"
    if component.amount is None:
        return "Not verified"
    if component.amount == 0 and component.status == "verified":
        return format_money(0, component.currency)
    prefix = "+" if component.amount > 0 else ""
    estimate = " est." if component.is_estimate else ""
    return f"{prefix}{format_money(component.amount, component.currency)}{estimate}"


def applicable_adjustment(component: MoneyComponent) -> float:
    """Return the signed amount that may enter the evaluated total, else 0.

    Unknown, expired, unsupported, and unverified savings do not change the total.
    Unknown additive costs also do not enter the total as zero.
    """
    if not component.applies:
        return 0.0
    if component.status in {"expired", "unsupported", "unverified", "unknown"}:
        return 0.0
    if component.amount is None:
        return 0.0
    if component.status == "not_applicable":
        return 0.0
    return float(component.amount)


def evaluate_offer_total(
    listing: MoneyComponent,
    adjustments: tuple[MoneyComponent, ...],
) -> float | None:
    if listing.amount is None:
        return None
    total = float(listing.amount)
    for item in adjustments:
        if item.is_unknown and item.kind in {"shipping", "tax", "import", "other"}:
            continue
        total += applicable_adjustment(item)
    return round(total, 2)


def select_price_state(
    *,
    shipping: MoneyComponent,
    taxes: MoneyComponent,
    import_charges: MoneyComponent | None,
    savings: tuple[MoneyComponent, ...],
    international: bool,
    location_known: bool,
    shipping_material: bool,
) -> PriceState:
    """Choose the dominant consumer price label from captured completeness."""
    unverified_savings = any(
        item.kind in {"discount", "voucher"} and item.status == "unverified" for item in savings
    )
    if unverified_savings:
        return "potential_checkout_price"

    shipping_unknown = shipping.is_unknown or shipping.status == "unverified"
    if (not location_known or shipping_unknown) and shipping_material:
        return "price_before_shipping"

    import_unknown = import_charges is not None and (
        import_charges.is_unknown or import_charges.status == "unverified"
    )
    if international and import_unknown:
        return "before_unverified_import_charges"

    estimated = shipping.is_estimate or taxes.is_estimate
    if import_charges is not None:
        estimated = estimated or import_charges.is_estimate
    if international and estimated:
        return "estimated_landed_cost"
    return "final_effective_cost"


def price_state_label(state: PriceState) -> str:
    return PRICE_STATE_LABELS[state]
