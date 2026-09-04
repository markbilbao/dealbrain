"""Currency conversion state — Sprint 37.3.

Source offer currency is monetary truth. Preferred/display currency is
presentation context. Only an authoritative FX quote may convert between them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.market.context import DEFAULT_DISPLAY_CURRENCY
from app.market.fx import (
    FxQuote,
    apply_fx_quote,
    normalize_currency_code,
    require_source_currency,
    resolve_production_fx_quote,
)

ConversionState = Literal["same_currency", "conversion_available", "conversion_unavailable"]

CONVERSION_UNAVAILABLE_DISCLOSURE = (
    "PHP conversion is not currently available. Amounts are shown in their source currency."
)
MIXED_SOURCE_CURRENCY_DISCLOSURE = (
    "Prices are shown in their source currencies because currency conversion "
    "is not currently available."
)


@dataclass(frozen=True, slots=True)
class CurrencyConversion:
    """Resolved conversion state for one source amount."""

    source_currency: str
    preferred_currency: str
    state: ConversionState
    source_amount: float | None
    converted_amount: float | None
    quote: FxQuote | None
    disclosure: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_currency": self.source_currency,
            "preferred_currency": self.preferred_currency,
            "state": self.state,
            "source_amount": self.source_amount,
            "converted_amount": self.converted_amount,
            "quote": None if self.quote is None else self.quote.to_dict(),
            "disclosure": self.disclosure,
        }


@dataclass(frozen=True, slots=True)
class OfferCurrencyAssessment:
    """Page-level currency honesty for Results / Compare / Why."""

    preferred_currency: str
    source_currencies: tuple[str, ...]
    state: ConversionState
    mixed_source_currencies: bool
    conversion_available: bool
    disclosure: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferred_currency": self.preferred_currency,
            "source_currencies": list(self.source_currencies),
            "state": self.state,
            "mixed_source_currencies": self.mixed_source_currencies,
            "conversion_available": self.conversion_available,
            "disclosure": self.disclosure,
        }


def resolve_currency_presentation(
    *,
    source_currency: str | None,
    source_amount: float | None,
    preferred_currency: str | None = DEFAULT_DISPLAY_CURRENCY,
    quote: FxQuote | None = None,
) -> CurrencyConversion:
    """Resolve source vs preferred currency. Missing source currency fails closed."""

    source = require_source_currency(source_currency)
    preferred = normalize_currency_code(preferred_currency) or DEFAULT_DISPLAY_CURRENCY
    if source == preferred:
        return CurrencyConversion(
            source_currency=source,
            preferred_currency=preferred,
            state="same_currency",
            source_amount=source_amount,
            converted_amount=source_amount,
            quote=None,
            disclosure=None,
        )
    trusted = quote if _quote_applies(quote, source, preferred) else None
    if trusted is not None:
        converted = apply_fx_quote(source_amount, trusted) if source_amount is not None else None
        return CurrencyConversion(
            source_currency=source,
            preferred_currency=preferred,
            state="conversion_available",
            source_amount=source_amount,
            converted_amount=converted,
            quote=trusted,
            disclosure=None,
        )
    return CurrencyConversion(
        source_currency=source,
        preferred_currency=preferred,
        state="conversion_unavailable",
        source_amount=source_amount,
        converted_amount=None,
        quote=None,
        disclosure=CONVERSION_UNAVAILABLE_DISCLOSURE,
    )


def resolve_production_currency_presentation(
    *,
    source_currency: str | None,
    source_amount: float | None,
    preferred_currency: str | None = DEFAULT_DISPLAY_CURRENCY,
) -> CurrencyConversion:
    """Production path. Never consults a live or browser-supplied FX rate."""

    quote = resolve_production_fx_quote(
        require_source_currency(source_currency),
        normalize_currency_code(preferred_currency) or DEFAULT_DISPLAY_CURRENCY,
    )
    return resolve_currency_presentation(
        source_currency=source_currency,
        source_amount=source_amount,
        preferred_currency=preferred_currency,
        quote=quote,
    )


def assess_offer_currencies(
    source_currencies: tuple[str, ...] | list[str],
    *,
    preferred_currency: str | None = DEFAULT_DISPLAY_CURRENCY,
    quote: FxQuote | None = None,
) -> OfferCurrencyAssessment:
    preferred = normalize_currency_code(preferred_currency) or DEFAULT_DISPLAY_CURRENCY
    codes = tuple(
        sorted({code for item in source_currencies if (code := normalize_currency_code(item))})
    )
    if not codes or codes == (preferred,):
        return OfferCurrencyAssessment(
            preferred_currency=preferred,
            source_currencies=codes,
            state="same_currency",
            mixed_source_currencies=False,
            conversion_available=False,
            disclosure=None,
        )
    mixed = len(codes) > 1
    conversions = tuple(
        resolve_currency_presentation(
            source_currency=code,
            source_amount=None,
            preferred_currency=preferred,
            quote=quote,
        )
        for code in codes
        if code != preferred
    )
    available = bool(conversions) and all(
        item.state == "conversion_available" for item in conversions
    )
    if mixed:
        state: ConversionState = "conversion_available" if available else "conversion_unavailable"
        disclosure = None if available else MIXED_SOURCE_CURRENCY_DISCLOSURE
        return OfferCurrencyAssessment(
            preferred_currency=preferred,
            source_currencies=codes,
            state=state,
            mixed_source_currencies=True,
            conversion_available=available,
            disclosure=disclosure,
        )
    foreign = conversions[0] if conversions else None
    if foreign is None:
        return OfferCurrencyAssessment(
            preferred_currency=preferred,
            source_currencies=codes,
            state="same_currency",
            mixed_source_currencies=False,
            conversion_available=False,
            disclosure=None,
        )
    return OfferCurrencyAssessment(
        preferred_currency=preferred,
        source_currencies=codes,
        state=foreign.state,
        mixed_source_currencies=False,
        conversion_available=foreign.state == "conversion_available",
        disclosure=foreign.disclosure,
    )


def _quote_applies(quote: FxQuote | None, source: str, preferred: str) -> bool:
    if quote is None:
        return False
    return quote.base_currency == source and quote.quote_currency == preferred
