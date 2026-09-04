"""Selected shopping-market contract — Sprint 37.2.

A selected market is where the shopper wants PiqSavi to research. It is not
delivery destination, account country, display currency, locale, or certified
shopping coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.core.countries import COUNTRY_NAMES, is_valid_country_code, normalize_country_code
from app.domain.entities.research_execution import TrustedMarketContext
from app.market.context import INTENDED_FIRST_MARKET_COUNTRY

SelectionOrigin = Literal["explicit", "intended_default"]

# Product-facing launch surface remains PH-first. The typed contract accepts any
# valid ISO code so later markets do not require a second model.
PRODUCT_FACING_SHOPPING_MARKETS = frozenset({INTENDED_FIRST_MARKET_COUNTRY})


class ShoppingMarketValidationError(ValueError):
    """Raised when a shopping-market code cannot be accepted."""


@dataclass(frozen=True, slots=True)
class SelectedShoppingMarket:
    """Server-validated selected shopping market.

    ``origin="intended_default"`` means the product default was applied because
    no explicit selection existed. That default is not certification.
    """

    country_code: str
    origin: SelectionOrigin = "explicit"

    def __post_init__(self) -> None:
        code = normalize_country_code(self.country_code)
        if not code or not is_valid_country_code(code):
            raise ShoppingMarketValidationError(
                "selected shopping market must be a valid ISO 3166-1 alpha-2 code"
            )
        if code != self.country_code:
            object.__setattr__(self, "country_code", code)
        if self.origin not in {"explicit", "intended_default"}:
            raise ShoppingMarketValidationError("selected shopping market origin is invalid")

    @property
    def is_intended_default(self) -> bool:
        return self.origin == "intended_default"

    @property
    def display_name(self) -> str:
        return COUNTRY_NAMES[self.country_code]

    def to_cookie_payload(self) -> dict[str, str]:
        return {"country_code": self.country_code}

    def to_dict(self) -> dict[str, Any]:
        return {
            "country_code": self.country_code,
            "origin": self.origin,
            "is_intended_default": self.is_intended_default,
            "display_name": self.display_name,
            "shopping_market_certified": False,
            "product_facing": self.country_code in PRODUCT_FACING_SHOPPING_MARKETS,
        }


def intended_default_shopping_market() -> SelectedShoppingMarket:
    """PH product-context default. Not a certified shopping market."""

    return SelectedShoppingMarket(
        country_code=INTENDED_FIRST_MARKET_COUNTRY,
        origin="intended_default",
    )


def selected_shopping_market_from_code(
    country_code: str | None,
    *,
    origin: SelectionOrigin = "explicit",
) -> SelectedShoppingMarket:
    """Validate an explicit ISO market code. Invalid input fails closed."""

    code = normalize_country_code(country_code)
    if not code or not is_valid_country_code(code):
        raise ShoppingMarketValidationError(
            "Enter a valid ISO 3166-1 alpha-2 shopping market code."
        )
    return SelectedShoppingMarket(country_code=code, origin=origin)


def resolve_selected_shopping_market(
    country_code: str | None,
) -> SelectedShoppingMarket:
    """Use an explicit valid code, or the intended PH default."""

    if country_code is None or not str(country_code).strip():
        return intended_default_shopping_market()
    return selected_shopping_market_from_code(country_code, origin="explicit")


def is_product_facing_shopping_market(country_code: str | None) -> bool:
    code = normalize_country_code(country_code)
    return code in PRODUCT_FACING_SHOPPING_MARKETS if code else False


def trusted_market_from_selected(selected: SelectedShoppingMarket) -> TrustedMarketContext:
    """Build server-trusted market identity from a validated selection.

    This names the selected research market. It does not certify coverage.
    """

    return TrustedMarketContext(country_code=selected.country_code)
