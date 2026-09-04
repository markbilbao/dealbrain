"""Sprint 37.1 MarketContext — composed PH product context.

Composes existing ``TrustedMarketContext`` (server-trusted country) and
``DeliveryContext`` (session city / optional postal). This is not a second
destination model and is not proof that PH is a certified shopping market.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.consumer.location import DeliveryContext
from app.core.countries import is_valid_country_code, normalize_country_code
from app.domain.entities.research_execution import TrustedMarketContext

INTENDED_FIRST_MARKET_COUNTRY = "PH"
DEFAULT_DISPLAY_CURRENCY = "PHP"
DEFAULT_DISPLAY_LOCALE = "en-PH"

DestinationState = Literal["known", "skipped", "absent"]

_PRIVACY_FORBIDDEN_FIELDS = frozenset(
    {
        "street",
        "address",
        "building",
        "unit",
        "house",
        "latitude",
        "longitude",
        "gps",
        "coordinates",
        "history",
        "precise_coordinates",
    }
)


@dataclass(frozen=True, slots=True)
class MarketContext:
    """Reusable PH-first market/destination context.

    ``trusted_market`` may be missing. Missing is not replaced with PH.
    Intended PH defaults are an explicit constructor, not fabrication.
    """

    trusted_market: TrustedMarketContext | None
    delivery: DeliveryContext
    display_currency: str = DEFAULT_DISPLAY_CURRENCY
    display_locale: str = DEFAULT_DISPLAY_LOCALE

    def __post_init__(self) -> None:
        currency = (self.display_currency or "").strip().upper()
        if len(currency) < 3 or len(currency) > 8:
            raise ValueError("display_currency must contain 3 to 8 characters")
        locale = (self.display_locale or "").strip()
        if not locale or len(locale) > 16:
            raise ValueError("display_locale must contain 1 to 16 characters")
        if currency != self.display_currency:
            object.__setattr__(self, "display_currency", currency)
        if locale != self.display_locale:
            object.__setattr__(self, "display_locale", locale)

    @property
    def country_code(self) -> str | None:
        return None if self.trusted_market is None else self.trusted_market.country_code

    @property
    def destination_state(self) -> DestinationState:
        if self.delivery.is_known:
            return "known"
        if self.delivery.is_skipped:
            return "skipped"
        return "absent"

    @property
    def destination_is_known_for_cost(self) -> bool:
        return self.delivery.is_known

    @property
    def city(self) -> str | None:
        return self.delivery.city

    @property
    def postal_code(self) -> str | None:
        return self.delivery.postal_code

    @property
    def destination_key(self) -> str:
        return self.delivery.destination_key

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "trusted_country": self.country_code,
            "trusted_source": None if self.trusted_market is None else self.trusted_market.source,
            "display_currency": self.display_currency,
            "display_locale": self.display_locale,
            "destination_state": self.destination_state,
            "city": self.delivery.city,
            "postal_code": self.delivery.postal_code,
            "destination_source": self.delivery.source,
            "destination_key": self.delivery.destination_key,
            "intended_first_market": INTENDED_FIRST_MARKET_COUNTRY,
            "shopping_market_certified": False,
        }
        leaked = _PRIVACY_FORBIDDEN_FIELDS.intersection(payload)
        if leaked:
            raise ValueError("market context must not persist precise location fields")
        return payload


def compose_market_context(
    *,
    trusted_market: TrustedMarketContext | None,
    delivery: DeliveryContext | None = None,
    display_currency: str = DEFAULT_DISPLAY_CURRENCY,
    display_locale: str = DEFAULT_DISPLAY_LOCALE,
) -> MarketContext:
    """Compose existing types. Does not invent a missing trusted market."""

    return MarketContext(
        trusted_market=trusted_market,
        delivery=delivery if delivery is not None else DeliveryContext(),
        display_currency=display_currency,
        display_locale=display_locale,
    )


def intended_ph_product_defaults(
    *,
    delivery: DeliveryContext | None = None,
) -> MarketContext:
    """Explicit PH/PHP/en-PH product defaults.

    This is intended first-market display context. It does not certify PH
    as a supported shopping market and must not be used to fill a missing
    trusted market during research planning.
    """

    return MarketContext(
        trusted_market=TrustedMarketContext(country_code=INTENDED_FIRST_MARKET_COUNTRY),
        delivery=delivery if delivery is not None else DeliveryContext(),
        display_currency=DEFAULT_DISPLAY_CURRENCY,
        display_locale=DEFAULT_DISPLAY_LOCALE,
    )


def require_trusted_market(context: MarketContext) -> TrustedMarketContext:
    """Research planning must not fabricate a country when trusted market is missing."""

    if context.trusted_market is None:
        raise ValueError("trusted market context is required and must not be fabricated")
    return context.trusted_market


def normalize_display_currency(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().upper()
    return cleaned or None


def is_intended_first_market(country_code: str | None) -> bool:
    code = normalize_country_code(country_code)
    return code == INTENDED_FIRST_MARKET_COUNTRY and bool(code and is_valid_country_code(code))
