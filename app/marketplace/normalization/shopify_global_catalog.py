"""Shopify Global Catalog normalization adapter.

Accepts an already validated in-memory Shopify product and one variant.
Does not perform HTTP, does not retain the raw catalog payload, and does
not build a product index.

Money reuses ``CanonicalMoneyLine`` / ``CanonicalOfferEconomics`` and keeps
Shopify's integer minor-unit amount exact. Title comparison reuses
``RuleBasedProductParser`` and ``ExactVariantProductMatcher``. Provenance
reuses Sprint 18 ``DataProvenance``, ``DataFreshness``, and
``evaluate_freshness``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.entities.marketplace_data import (
    DataFreshness,
    DataProvenance,
    FreshnessStatus,
    ProductAvailability,
    SourceMode,
)
from app.domain.entities.offer_economics import (
    CanonicalDeliveryContext,
    CanonicalMoneyLine,
    CanonicalOfferEconomics,
)
from app.domain.entities.product_match import MatchType, ProductMatchResult
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.marketplace.freshness.rules import evaluate_freshness
from app.marketplace.normalization.normalizer import parse_availability, parse_datetime
from app.research.shopify_global_catalog_ph_probe import is_placeholder_or_test_result

SHOPIFY_GLOBAL_CATALOG_SOURCE = "shopify_global_catalog"
# Capability-policy map: retained shopper-facing freshness is not established.
RETAINED_SHOPPER_FACING_FRESHNESS_ESTABLISHED = False
_MATCH_TITLE_SEPARATOR = " — "
_GENERIC_VARIANT_TITLES = frozenset({"default title"})
_OBSERVATION_KINDS = frozenset({"fixture", "synthetic", "live"})
ObservationKind = Literal["fixture", "synthetic", "live"]

_UNKNOWN_COMPONENTS: tuple[str, ...] = (
    "shipping unknown",
    "taxes unknown",
    "import charges unknown",
    "voucher not applied",
    "seller discount unknown",
    "platform discount unknown",
    "voucher eligibility unknown",
    "free shipping unknown",
    "checkout costs unknown",
)


class ShopifyNormalizationRefusal(ValueError):
    """Useful normalization failed closed. No partial offer is returned."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class ShopifySourceFacts:
    """Exact source facts. Not the original Shopify response."""

    source_identity: str
    product_id: str
    variant_id: str | None
    product_title: str
    variant_title: str | None
    seller_identity: str
    seller_domain: str | None
    seller_url: str | None
    product_url: str | None
    checkout_url: str | None
    availability: ProductAvailability
    currency: str
    price_amount_minor: int
    checked_at: datetime
    provider_source_timestamp: datetime | None
    provider_timestamp_supplied: bool
    ph_query_context: bool
    source_mode: SourceMode
    observation_kind: ObservationKind
    raw_response_persisted: bool = False

    def __post_init__(self) -> None:
        if self.source_identity != SHOPIFY_GLOBAL_CATALOG_SOURCE:
            raise ValueError("source identity must be shopify_global_catalog")
        if self.raw_response_persisted:
            raise ValueError("raw Shopify responses must not be persisted")
        if self.observation_kind == "live" and self.source_mode != SourceMode.LIVE:
            raise ValueError("live observations must use the live source mode")
        if self.observation_kind != "live" and self.source_mode == SourceMode.LIVE:
            raise ValueError("fixture or synthetic observations must not be labeled live")
        if self.checked_at.utcoffset() is None:
            raise ValueError("checked_at must be timezone-aware")
        if (
            self.provider_source_timestamp is not None
            and self.provider_source_timestamp.utcoffset() is None
        ):
            raise ValueError("provider_source_timestamp must be timezone-aware")
        if self.provider_timestamp_supplied != (self.provider_source_timestamp is not None):
            raise ValueError("provider timestamp flag must match the timestamp value")
        amount = self.price_amount_minor
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError("price_amount_minor must be an integer minor-unit amount")


@dataclass(frozen=True, slots=True)
class ShopifyNormalizedOffer:
    """One variant, normalized. Source ids are not parser output."""

    source: ShopifySourceFacts
    economics: CanonicalOfferEconomics
    provenance: DataProvenance
    freshness: DataFreshness
    match_title: str
    parsed: CanonicalProduct
    retained_shopper_facing_freshness_established: bool
    seller_discount_applied: bool
    platform_discount_applied: bool
    voucher_applied: bool
    free_shipping_claimed: bool
    checkout_cost_amount_minor: int | None
    raw_response_persisted: bool = False

    def __post_init__(self) -> None:
        if self.raw_response_persisted or self.source.raw_response_persisted:
            raise ValueError("raw Shopify responses must not be persisted")
        if self.retained_shopper_facing_freshness_established:
            raise ValueError("retained shopper-facing freshness is not established")
        if self.seller_discount_applied or self.platform_discount_applied:
            raise ValueError("unknown discounts must not be applied")
        if self.voucher_applied or self.free_shipping_claimed:
            raise ValueError("unknown voucher or free shipping must not be applied")
        if self.checkout_cost_amount_minor is not None:
            raise ValueError("unknown checkout costs must not be stored as an amount")
        if self.economics.price_state == "final_effective_cost":
            raise ValueError("unknown shipping and costs are not a final effective cost")
        if self.economics.listing.amount_minor != self.source.price_amount_minor:
            raise ValueError("listing amount_minor must preserve the source minor units")
        if self.economics.currency != self.source.currency:
            raise ValueError("offer currency must preserve the source currency")
        if self.freshness.is_current_live_price:
            raise ValueError("this path must not claim a current live price")
        synthetic = self.source.source_mode != SourceMode.LIVE
        if synthetic and self.provenance.source_mode == SourceMode.LIVE:
            raise ValueError("fixture or synthetic observations must not be labeled live")


@dataclass(frozen=True, slots=True)
class ShopifyIdentityComparison:
    """Source ids and parsed-title comparison. Title similarity cannot merge ids."""

    relation: str
    merged: bool
    source_product_ids_conflict: bool
    source_variant_ids_conflict: bool
    title_similarity_overridden: bool
    parsed_match: ProductMatchResult


def compose_shopify_match_title(product_title: str, variant_title: str | None) -> str:
    """Deterministic display title. Variant title is appended once when distinct."""

    product = " ".join(product_title.split())
    variant = " ".join((variant_title or "").split())
    if not product:
        raise ShopifyNormalizationRefusal("missing_product_title")
    if not variant or variant.casefold() in _GENERIC_VARIANT_TITLES:
        return product
    if variant.casefold() == product.casefold():
        return product
    return f"{product}{_MATCH_TITLE_SEPARATOR}{variant}"


def shopify_listing_price(
    product: Mapping[str, Any], variant: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    """Price object the adapter will read. Variant price wins over the range."""

    return _listing_price(product, variant)


def integer_source_minor_amount(price: Mapping[str, Any] | None) -> int | None:
    """Preserve an integer source minor-unit amount. Floats are not accepted."""

    if not isinstance(price, Mapping):
        return None
    amount = price.get("amount")
    if isinstance(amount, bool) or amount is None:
        return None
    if isinstance(amount, int):
        return amount
    if isinstance(amount, str):
        stripped = amount.strip()
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            return int(stripped)
    return None


def normalize_shopify_global_catalog_offer(
    product: Mapping[str, Any],
    variant: Mapping[str, Any] | None = None,
    *,
    checked_at: datetime,
    observation_kind: ObservationKind = "synthetic",
    ph_query_context: bool = True,
) -> ShopifyNormalizedOffer:
    """Normalize one validated variant. Refuses incomplete or test records."""

    if observation_kind not in _OBSERVATION_KINDS:
        raise ShopifyNormalizationRefusal("unknown_observation_class")
    if checked_at.utcoffset() is None:
        raise ShopifyNormalizationRefusal("checked_at_must_be_timezone_aware")
    product_map = _as_mapping(product, reason="missing_product_identity")
    variant_map = _selected_variant(product_map, variant)
    if is_placeholder_or_test_result(dict(product_map), dict(variant_map)):
        raise ShopifyNormalizationRefusal("placeholder_or_test")
    _refuse_conflicting_variant_ids(variant_map)

    product_id = _text(product_map.get("id"))
    if not product_id:
        raise ShopifyNormalizationRefusal("missing_product_identity")
    variant_id = _text(variant_map.get("id"))
    product_title = _text(product_map.get("title"))
    if not product_title:
        raise ShopifyNormalizationRefusal("missing_product_title")
    variant_title = _text(variant_map.get("title"))
    seller = _as_optional_mapping(variant_map.get("seller"))
    seller_identity = _text(seller.get("name")) or _text(seller.get("id"))
    if not seller_identity:
        raise ShopifyNormalizationRefusal("missing_seller_identity")

    price = _listing_price(product_map, variant_map)
    amount_minor = integer_source_minor_amount(price)
    if amount_minor is None or amount_minor < 0:
        raise ShopifyNormalizationRefusal("missing_price")
    currency = _currency(price.get("currency") if price else None)
    if currency is None:
        raise ShopifyNormalizationRefusal("missing_currency")

    provider_timestamp = _provider_timestamp(product_map, variant_map, price)
    mode = SourceMode.LIVE if observation_kind == "live" else SourceMode.FIXTURE
    match_title = compose_shopify_match_title(product_title, variant_title)
    parsed = RuleBasedProductParser().parse(match_title)
    availability = _availability(variant_map)
    source = ShopifySourceFacts(
        source_identity=SHOPIFY_GLOBAL_CATALOG_SOURCE,
        product_id=product_id,
        variant_id=variant_id,
        product_title=product_title,
        variant_title=variant_title,
        seller_identity=seller_identity,
        seller_domain=_text(seller.get("domain")),
        seller_url=_absolute_http_url(seller.get("url")),
        product_url=_absolute_http_url(product_map.get("url")),
        checkout_url=_absolute_http_url(variant_map.get("checkout_url")),
        availability=availability,
        currency=currency,
        price_amount_minor=amount_minor,
        checked_at=checked_at,
        provider_source_timestamp=provider_timestamp,
        provider_timestamp_supplied=provider_timestamp is not None,
        ph_query_context=ph_query_context,
        source_mode=mode,
        observation_kind=observation_kind,
        raw_response_persisted=False,
    )
    provenance = _provenance(source, observation_kind)
    freshness = _freshness(source, observation_kind)
    economics = _economics(source)
    return ShopifyNormalizedOffer(
        source=source,
        economics=economics,
        provenance=provenance,
        freshness=freshness,
        match_title=match_title,
        parsed=parsed,
        retained_shopper_facing_freshness_established=(
            RETAINED_SHOPPER_FACING_FRESHNESS_ESTABLISHED
        ),
        seller_discount_applied=False,
        platform_discount_applied=False,
        voucher_applied=False,
        free_shipping_claimed=False,
        checkout_cost_amount_minor=None,
        raw_response_persisted=False,
    )


def compare_shopify_variant_identity(
    left: ShopifyNormalizedOffer,
    right: ShopifyNormalizedOffer,
) -> ShopifyIdentityComparison:
    """Hold distinct source variants apart. Parser output does not merge them."""

    parsed_match = ExactVariantProductMatcher().match_products(left.parsed, right.parsed)
    product_conflict = left.source.product_id != right.source.product_id
    left_variant = left.source.variant_id
    right_variant = right.source.variant_id
    variant_conflict = bool(left_variant and right_variant and left_variant != right_variant)
    same_variant = bool(left_variant and right_variant and left_variant == right_variant)
    title_match = parsed_match.is_match and parsed_match.match_type in {
        MatchType.EXACT_VARIANT,
        MatchType.PROBABLE_VARIANT,
    }
    overridden = variant_conflict and title_match
    merged = False
    if product_conflict:
        relation = (
            "different_product"
            if parsed_match.match_type == MatchType.DIFFERENT_PRODUCT
            else "different_source_product"
        )
    elif variant_conflict:
        relation = "different_source_variant"
    elif parsed_match.match_type == MatchType.DIFFERENT_PRODUCT:
        relation = "different_product"
    elif parsed_match.match_type == MatchType.SAME_PRODUCT_DIFFERENT_VARIANT:
        relation = "same_product_different_variant"
    elif parsed_match.match_type == MatchType.INSUFFICIENT_INFORMATION:
        relation = "insufficient_information"
    elif title_match and same_variant and not parsed_match.conflicts:
        relation = "same_source_variant"
        merged = True
    else:
        relation = "ambiguous"
    if variant_conflict or product_conflict:
        merged = False
    return ShopifyIdentityComparison(
        relation=relation,
        merged=merged,
        source_product_ids_conflict=product_conflict,
        source_variant_ids_conflict=variant_conflict,
        title_similarity_overridden=overridden,
        parsed_match=parsed_match,
    )


def _economics(source: ShopifySourceFacts) -> CanonicalOfferEconomics:
    currency = source.currency
    listing = CanonicalMoneyLine(
        kind="listing",
        amount_minor=source.price_amount_minor,
        currency=currency,
        status="verified",
        applied=True,
        label="observed listing price",
    )
    shipping = _unknown_line("shipping", currency)
    taxes = _unknown_line("tax", currency)
    voucher = _unknown_line("voucher", currency)
    imports = _unknown_line("import", currency)
    delivery = None
    if source.ph_query_context:
        delivery = CanonicalDeliveryContext(country="PH")
    return CanonicalOfferEconomics(
        offer_id=_bounded_identifier(f"{source.product_id}:{source.variant_id or '-'}"),
        product_id=_bounded_identifier(source.product_id),
        currency=currency,
        listing=listing,
        shipping=shipping,
        taxes=taxes,
        price_state="price_before_shipping",
        dominant_amount_minor=source.price_amount_minor,
        merchant=_bounded_text(source.seller_identity),
        marketplace=SHOPIFY_GLOBAL_CATALOG_SOURCE,
        seller_id=_bounded_text(source.seller_identity),
        voucher=voucher,
        import_charges=imports,
        delivery=delivery,
        international=False,
        unknowns=_UNKNOWN_COMPONENTS,
        evidence_ids=(),
        provenance_source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
        checked_at=source.checked_at,
        freshness="unknown",
    )


def _unknown_line(kind: str, currency: str) -> CanonicalMoneyLine:
    return CanonicalMoneyLine(
        kind=kind,  # type: ignore[arg-type]
        amount_minor=None,
        currency=currency,
        status="unknown",
        applied=False,
    )


def _provenance(source: ShopifySourceFacts, observation_kind: ObservationKind) -> DataProvenance:
    if source.provider_timestamp_supplied:
        timestamp_note = "Shopify supplied a source timestamp. It is not the PiqSavi query time."
    else:
        timestamp_note = (
            "Shopify did not supply a freshness timestamp. "
            "checked_at is the PiqSavi query time only."
        )
    mode_note = (
        "Live observation."
        if observation_kind == "live"
        else "Fixture or synthetic observation is not live."
    )
    return DataProvenance(
        source_mode=source.source_mode,
        source_id=SHOPIFY_GLOBAL_CATALOG_SOURCE,
        connector_id=None,
        observed_at=source.checked_at,
        source_timestamp=source.provider_source_timestamp,
        ingested_at=source.checked_at,
        confidence=1.0,
        notes=(
            f"{mode_note} {timestamp_note} Retained shopper-facing freshness is not established."
        ),
        simulated=observation_kind != "live",
    )


def _freshness(source: ShopifySourceFacts, observation_kind: ObservationKind) -> DataFreshness:
    """Reuse Sprint 18 freshness, then refuse a stronger claim than the evidence."""

    technical = evaluate_freshness(
        source_mode=source.source_mode,
        observed_at=source.checked_at,
        source_timestamp=source.provider_source_timestamp,
        ingested_at=source.checked_at,
        now=source.checked_at,
        connector_healthy=None,
        simulated=observation_kind != "live",
    )
    warning = technical.warning or ""
    if not source.provider_timestamp_supplied:
        extra = (
            "Shopify did not supply a freshness timestamp. "
            "checked_at is not a provider freshness timestamp."
        )
        warning = f"{warning}; {extra}" if warning else extra
    if not RETAINED_SHOPPER_FACING_FRESHNESS_ESTABLISHED:
        extra = "Retained shopper-facing freshness is not established."
        warning = f"{warning}; {extra}" if warning else extra
    if source.source_mode != SourceMode.LIVE:
        extra = "Fixture or synthetic observation is not live marketplace pricing."
        warning = f"{warning}; {extra}" if warning else extra
    return DataFreshness(
        status=FreshnessStatus.UNKNOWN,
        source_mode=source.source_mode,
        last_successful_observation=source.checked_at,
        source_timestamp=source.provider_source_timestamp,
        ingestion_timestamp=source.checked_at,
        age_hours=None,
        connector_healthy=technical.connector_healthy,
        warning=warning,
        is_current_live_price=False,
    )


def _listing_price(
    product: Mapping[str, Any], variant: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    variant_price = _as_optional_mapping(variant.get("price"))
    if variant_price and integer_source_minor_amount(variant_price) is not None:
        return variant_price
    if variant.get("price") not in (None, {}, []):
        return variant_price or {}
    price_range = _as_optional_mapping(product.get("price_range"))
    minimum = _as_optional_mapping(price_range.get("min"))
    if minimum:
        return minimum
    return None


def _provider_timestamp(
    product: Mapping[str, Any],
    variant: Mapping[str, Any],
    price: Mapping[str, Any] | None,
) -> datetime | None:
    for source in (price or {}, variant, product):
        if not isinstance(source, Mapping):
            continue
        parsed = parse_datetime(source.get("source_timestamp"))
        if parsed is not None:
            return parsed
    return None


def _availability(variant: Mapping[str, Any]) -> ProductAvailability:
    availability = _as_optional_mapping(variant.get("availability"))
    if not availability:
        return ProductAvailability.UNKNOWN
    if availability.get("available") is False:
        return ProductAvailability.OUT_OF_STOCK
    status = _text(availability.get("status"))
    if status:
        return parse_availability(status)
    if availability.get("available") is True:
        return ProductAvailability.IN_STOCK
    return ProductAvailability.UNKNOWN


def _selected_variant(
    product: Mapping[str, Any], variant: Mapping[str, Any] | None
) -> Mapping[str, Any]:
    if variant is not None:
        return _as_mapping(variant, reason="missing_variant_identity")
    raw_variants = product.get("variants")
    if isinstance(raw_variants, list):
        found = [item for item in raw_variants if isinstance(item, Mapping)]
        if len(found) > 1:
            raise ShopifyNormalizationRefusal("conflicting_variant_identity")
        if len(found) == 1:
            return found[0]
    return {}


def _refuse_conflicting_variant_ids(variant: Mapping[str, Any]) -> None:
    primary = _text(variant.get("id"))
    alias = _text(variant.get("variant_id"))
    if primary and alias and primary != alias:
        raise ShopifyNormalizationRefusal("conflicting_variant_identity")


def _currency(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    code = text.upper()
    if not code or len(code) > 8:
        return None
    return code


def _bounded_identifier(value: str) -> str:
    if 1 <= len(value) <= 128:
        return value
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_text(value: str) -> str:
    if len(value) <= 128:
        return value
    return value[:128]


def _as_mapping(value: Mapping[str, Any], *, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ShopifyNormalizationRefusal(reason)
    return value


def _as_optional_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _absolute_http_url(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    lowered = text.casefold()
    if lowered.startswith("https://") or lowered.startswith("http://"):
        return text
    return None
