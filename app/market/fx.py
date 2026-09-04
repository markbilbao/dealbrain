"""FX quote authority — Sprint 37.3.

Production has no FX provider. Browser input, selected market, locale, delivery,
account country, and affiliate availability cannot become a trusted quote.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Literal

PRODUCTION_FX_CONVERSION_ENABLED = False
FxFreshness = Literal["fresh", "stale", "unknown", "test_only"]


class CurrencyAuthorityError(ValueError):
    """Raised when currency identity or a quote cannot be trusted."""


@dataclass(frozen=True, slots=True)
class FxQuote:
    """Authoritative conversion quote. Test fixtures are never production evidence."""

    base_currency: str
    quote_currency: str
    rate: float
    as_of: datetime
    provider: str
    quote_id: str
    freshness: FxFreshness = "unknown"
    live: bool = False
    production_eligible: bool = False

    def __post_init__(self) -> None:
        base = _require_currency(self.base_currency, "base currency")
        quote = _require_currency(self.quote_currency, "quote currency")
        if base != self.base_currency:
            object.__setattr__(self, "base_currency", base)
        if quote != self.quote_currency:
            object.__setattr__(self, "quote_currency", quote)
        if self.rate <= 0:
            raise CurrencyAuthorityError("FX rate must be greater than zero")
        if self.as_of.tzinfo is None:
            raise CurrencyAuthorityError("FX quote as_of must be timezone-aware")
        if not (self.provider or "").strip() or not (self.quote_id or "").strip():
            raise CurrencyAuthorityError("FX quote must identify provider and quote_id")
        if self.live and not self.production_eligible:
            raise CurrencyAuthorityError("test-only FX quotes cannot be marked live")
        if self.production_eligible and self.provider == TEST_FX_PROVIDER:
            raise CurrencyAuthorityError("test-only FX quotes cannot be production eligible")

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "rate": self.rate,
            "as_of": self.as_of.isoformat(),
            "provider": self.provider,
            "quote_id": self.quote_id,
            "freshness": self.freshness,
            "live": self.live,
            "production_eligible": self.production_eligible,
        }


TEST_FX_PROVIDER = "test_only_fx_fixture"


def normalize_currency_code(value: str | None) -> str | None:
    cleaned = (value or "").strip().upper()
    if not cleaned:
        return None
    if not cleaned.isalpha() or len(cleaned) < 3 or len(cleaned) > 8:
        return None
    return cleaned


def require_source_currency(value: str | None) -> str:
    """Fail closed when an offer amount is missing its source currency."""

    return _require_currency(value, "source currency")


def _require_currency(value: str | None, label: str) -> str:
    code = normalize_currency_code(value)
    if code is None:
        raise CurrencyAuthorityError(f"{label} is required and must not be assumed")
    return code


def production_fx_quotes() -> tuple[FxQuote, ...]:
    """Fail-closed production catalog. Zero authoritative quotes."""

    return ()


def production_fx_conversion_enabled() -> bool:
    return PRODUCTION_FX_CONVERSION_ENABLED


def resolve_production_fx_quote(base_currency: str, quote_currency: str) -> FxQuote | None:
    """Production never invents a quote from market, locale, or display preference."""

    _ = base_currency, quote_currency
    if not production_fx_conversion_enabled():
        return None
    return None


def fx_quote_for_tests(
    *,
    base_currency: str,
    quote_currency: str,
    rate: float,
    as_of: datetime | None = None,
    quote_id: str = "test-fx-quote-1",
) -> FxQuote:
    """Deterministic in-process quote. Not live and not production evidence."""

    return FxQuote(
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=rate,
        as_of=as_of or datetime(2030, 1, 1, tzinfo=UTC),
        provider=TEST_FX_PROVIDER,
        quote_id=quote_id,
        freshness="test_only",
        live=False,
        production_eligible=False,
    )


def apply_fx_quote(amount: float, quote: FxQuote) -> float:
    converted = (Decimal(str(amount)) * Decimal(str(quote.rate))).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_EVEN,
    )
    return float(converted)
