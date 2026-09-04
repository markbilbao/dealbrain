"""Certified / supported shopping-market catalog.

Intended first-market defaults (PH) are not certification. Production remains
empty until a Sprint 32–36 path is production-certified.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.countries import normalize_country_code


@dataclass(frozen=True, slots=True)
class CertifiedShoppingMarketCatalog:
    """Server-owned certified shopping markets. Production starts empty."""

    certified_iso_markets: frozenset[str] = frozenset()

    def is_certified(self, country_code: str | None) -> bool:
        code = normalize_country_code(country_code)
        if not code:
            return False
        return code in self.certified_iso_markets

    def may_invoke_connector(self, country_code: str | None) -> bool:
        """Unsupported / uncertified markets must not invoke a connector."""

        return self.is_certified(country_code)

    def to_tuple(self) -> tuple[str, ...]:
        return tuple(sorted(self.certified_iso_markets))


def production_certified_shopping_markets() -> CertifiedShoppingMarketCatalog:
    """Fail-closed production catalog. Zero certified shopping markets."""

    return CertifiedShoppingMarketCatalog()


def shopping_markets_for_tests(
    markets: frozenset[str] | tuple[str, ...] = (),
) -> CertifiedShoppingMarketCatalog:
    """Explicit test catalog. Callers must pass markets; nothing is implicit."""

    normalized = frozenset(code.strip().upper() for code in markets if code and code.strip())
    return CertifiedShoppingMarketCatalog(certified_iso_markets=normalized)
