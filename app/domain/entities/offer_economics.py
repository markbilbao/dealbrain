"""Immutable offer economics captured at canonical decision time.

These values are historical evidence, not a pricing engine and not a live feed.
Amounts are stored in integer minor units to avoid binary floating-point money.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Literal

EvidenceFreshness = Literal["fresh", "stale", "unknown"]

CanonicalPriceState = Literal[
    "final_effective_cost",
    "estimated_landed_cost",
    "price_before_shipping",
    "before_unverified_import_charges",
    "potential_checkout_price",
]
CanonicalComponentKind = Literal[
    "listing",
    "discount",
    "voucher",
    "shipping",
    "tax",
    "import",
]
CanonicalComponentStatus = Literal[
    "verified",
    "estimated",
    "unknown",
    "not_applicable",
    "expired",
    "unsupported",
    "unverified",
]

PRICE_STATE_LABELS: dict[CanonicalPriceState, str] = {
    "final_effective_cost": "Final effective cost",
    "estimated_landed_cost": "Estimated landed cost",
    "price_before_shipping": "Price before shipping",
    "before_unverified_import_charges": "Before unverified import charges",
    "potential_checkout_price": "Potential checkout price",
}

_VALID_STATES = frozenset(PRICE_STATE_LABELS)
_VALID_KINDS = frozenset(
    {"listing", "discount", "voucher", "shipping", "tax", "import"}
)
_VALID_STATUSES = frozenset(
    {
        "verified",
        "estimated",
        "unknown",
        "not_applicable",
        "expired",
        "unsupported",
        "unverified",
    }
)


def major_to_minor(amount: float | int | str | Decimal | None) -> int | None:
    """Convert an already-determined major-unit amount into integer minor units."""

    if amount is None:
        return None
    quantized = (Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    return int(quantized)


def minor_to_major(amount_minor: int | None) -> float | None:
    """Presentation helper. Does not recompute discounts or landed cost."""

    if amount_minor is None:
        return None
    return float(Decimal(amount_minor) / 100)


@dataclass(frozen=True, slots=True)
class CanonicalMoneyLine:
    """One captured price line with semantic status preserved."""

    kind: CanonicalComponentKind
    amount_minor: int | None
    currency: str
    status: CanonicalComponentStatus
    applied: bool = True
    evidence_id: str | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError("canonical money line kind is invalid")
        if self.status not in _VALID_STATUSES:
            raise ValueError("canonical money line status is invalid")
        if not self.currency or len(self.currency) > 8:
            raise ValueError("currency must contain 1 to 8 characters")
        if self.amount_minor is not None and not isinstance(self.amount_minor, int):
            raise ValueError("amount_minor must be an integer or None")
        if isinstance(self.amount_minor, bool):
            raise ValueError("amount_minor must be an integer or None")
        if self.status == "unknown" and self.amount_minor is not None:
            raise ValueError("unknown money lines must not store an amount")
        if self.kind in {"voucher", "discount"} and self.applied and self.status != "verified":
            raise ValueError("unverified, expired, or unknown savings cannot be applied")
        if self.evidence_id is not None and (not self.evidence_id or len(self.evidence_id) > 128):
            raise ValueError("evidence_id must contain 1 to 128 characters")

    @property
    def is_unknown(self) -> bool:
        return self.status in {"unknown", "unverified"} or (
            self.applied and self.amount_minor is None and self.status != "not_applicable"
        )

    @property
    def is_estimate(self) -> bool:
        return self.status == "estimated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "status": self.status,
            "applied": self.applied,
            "evidence_id": self.evidence_id,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class CanonicalDeliveryContext:
    """Minimum destination used when the offer economics were evaluated."""

    city: str | None = None
    postal_code: str | None = None
    country: str | None = None

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("city", self.city, 80),
            ("postal_code", self.postal_code, 12),
            ("country", self.country, 64),
        ):
            if value is not None and (not value.strip() or len(value) > maximum):
                raise ValueError(f"{field_name} must contain 1 to {maximum} characters")

    @property
    def display_place(self) -> str:
        if not self.city:
            return ""
        if self.postal_code:
            return f"{self.city} {self.postal_code}"
        return self.city

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "postal_code": self.postal_code,
            "country": self.country,
        }


@dataclass(frozen=True, slots=True)
class CanonicalOfferEconomics:
    """Decision-time economics for one evaluated offer. Not a live price."""

    offer_id: str
    product_id: str
    currency: str
    listing: CanonicalMoneyLine
    shipping: CanonicalMoneyLine
    taxes: CanonicalMoneyLine
    price_state: CanonicalPriceState
    dominant_amount_minor: int | None
    merchant: str | None = None
    marketplace: str | None = None
    seller_id: str | None = None
    voucher: CanonicalMoneyLine | None = None
    import_charges: CanonicalMoneyLine | None = None
    delivery: CanonicalDeliveryContext | None = None
    international: bool = False
    unknowns: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    provenance_source: str | None = None
    checked_at: datetime | None = None
    freshness: EvidenceFreshness | None = None

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("offer_id", self.offer_id, 128),
            ("product_id", self.product_id, 128),
            ("currency", self.currency, 8),
        ):
            if not value or len(value) > maximum:
                raise ValueError(f"{field_name} must contain 1 to {maximum} characters")
        if self.listing.kind != "listing":
            raise ValueError("listing line kind must be listing")
        if self.shipping.kind != "shipping":
            raise ValueError("shipping line kind must be shipping")
        if self.taxes.kind != "tax":
            raise ValueError("tax line kind must be tax")
        if self.voucher is not None and self.voucher.kind not in {"voucher", "discount"}:
            raise ValueError("voucher line kind must be voucher or discount")
        if self.import_charges is not None and self.import_charges.kind != "import":
            raise ValueError("import line kind must be import")
        if self.price_state not in _VALID_STATES:
            raise ValueError("canonical price state is invalid")
        if self.dominant_amount_minor is not None and (
            isinstance(self.dominant_amount_minor, bool)
            or not isinstance(self.dominant_amount_minor, int)
        ):
            raise ValueError("dominant_amount_minor must be an integer or None")
        if self.listing.currency != self.currency:
            raise ValueError("listing currency must match offer currency")
        if len(self.unknowns) != len(set(self.unknowns)) or any(not item for item in self.unknowns):
            raise ValueError("unknowns must contain unique non-empty values")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must be unique")
        if self.checked_at is not None and self.checked_at.utcoffset() is None:
            raise ValueError("checked_at must be timezone-aware")
        if self.freshness is not None and self.freshness not in {"fresh", "stale", "unknown"}:
            raise ValueError("evidence freshness is invalid")
        if self.merchant is not None and (not self.merchant or len(self.merchant) > 128):
            raise ValueError("merchant must contain 1 to 128 characters")
        if self.provenance_source is not None and len(self.provenance_source) > 256:
            raise ValueError("provenance_source must contain 1 to 256 characters")

    def to_dict(self) -> dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "product_id": self.product_id,
            "currency": self.currency,
            "listing": self.listing.to_dict(),
            "shipping": self.shipping.to_dict(),
            "taxes": self.taxes.to_dict(),
            "price_state": self.price_state,
            "dominant_amount_minor": self.dominant_amount_minor,
            "merchant": self.merchant,
            "marketplace": self.marketplace,
            "seller_id": self.seller_id,
            "voucher": self.voucher.to_dict() if self.voucher else None,
            "import_charges": self.import_charges.to_dict() if self.import_charges else None,
            "delivery": self.delivery.to_dict() if self.delivery else None,
            "international": self.international,
            "unknowns": list(self.unknowns),
            "evidence_ids": list(self.evidence_ids),
            "provenance_source": self.provenance_source,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "freshness": self.freshness,
        }
