"""Shopping-market coverage assessment — Sprint 37.2.

Coverage is decided only by the server-owned certified shopping-market catalog.
Account country, delivery destination, locale, currency, and affiliate
availability cannot certify a market.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.core.countries import COUNTRY_NAMES
from app.domain.entities.research_execution import (
    ResearchPlanningResult,
    TrustedMarketContext,
)
from app.market.context import INTENDED_FIRST_MARKET_COUNTRY
from app.market.selection import SelectedShoppingMarket, intended_default_shopping_market
from app.market.support import (
    CertifiedShoppingMarketCatalog,
    production_certified_shopping_markets,
)
from app.services.research_execution_router import plan_authorized_research

CoverageReason = Literal["certified_coverage_available", "no_certified_shopping_market"]

UNSUPPORTED_COVERAGE_DISCLOSURE = "Shopping coverage for this market is not yet available."
PH_PREPARING_COVERAGE_DISCLOSURE = (
    "PiqSavi is preparing shopping-source coverage for the Philippines."
)
FIXTURE_NOT_CERTIFIED_DISCLOSURE = (
    "This page uses a labeled demo catalog. It is not certified shopping coverage."
)


@dataclass(frozen=True, slots=True)
class ShoppingMarketCoverage:
    """Truthful coverage state for one selected shopping market."""

    selected: SelectedShoppingMarket
    certified: bool
    coverage_available: bool
    reason: CoverageReason
    disclosure: str
    connector_invocation_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_market": self.selected.country_code,
            "selected_origin": self.selected.origin,
            "display_name": self.selected.display_name,
            "certified": self.certified,
            "coverage_available": self.coverage_available,
            "reason": self.reason,
            "disclosure": self.disclosure,
            "connector_invocation_eligible": self.connector_invocation_eligible,
            "intended_default": self.selected.is_intended_default,
        }


def assess_shopping_coverage(
    selected: SelectedShoppingMarket | None = None,
    *,
    catalog: CertifiedShoppingMarketCatalog | None = None,
    account_country: str | None = None,
    display_currency: str | None = None,
    affiliate_available: bool = False,
    delivery_country: str | None = None,
) -> ShoppingMarketCoverage:
    """Assess certified coverage. Non-catalog inputs are ignored."""

    _ = account_country, display_currency, affiliate_available, delivery_country
    market = selected if selected is not None else intended_default_shopping_market()
    certified_catalog = catalog or production_certified_shopping_markets()
    certified = certified_catalog.is_certified(market.country_code)
    if certified:
        name = COUNTRY_NAMES.get(market.country_code, market.country_code)
        return ShoppingMarketCoverage(
            selected=market,
            certified=True,
            coverage_available=True,
            reason="certified_coverage_available",
            disclosure=f"Certified shopping coverage is available for {name}.",
            connector_invocation_eligible=True,
        )
    disclosure = UNSUPPORTED_COVERAGE_DISCLOSURE
    if market.country_code == INTENDED_FIRST_MARKET_COUNTRY:
        disclosure = PH_PREPARING_COVERAGE_DISCLOSURE
    return ShoppingMarketCoverage(
        selected=market,
        certified=False,
        coverage_available=False,
        reason="no_certified_shopping_market",
        disclosure=disclosure,
        connector_invocation_eligible=False,
    )


def connector_invocation_eligible(
    selected: SelectedShoppingMarket | None = None,
    *,
    catalog: CertifiedShoppingMarketCatalog | None = None,
    account_country: str | None = None,
    display_currency: str | None = None,
    affiliate_available: bool = False,
) -> bool:
    """True only when the trusted certified-market catalog allows a connector."""

    return assess_shopping_coverage(
        selected,
        catalog=catalog,
        account_country=account_country,
        display_currency=display_currency,
        affiliate_available=affiliate_available,
    ).connector_invocation_eligible


def plan_authorized_research_if_coverage_allows(
    authorization,
    *,
    owner,
    conversation_id: str,
    decision_id: str,
    canonical_context_version: int,
    registry,
    selected: SelectedShoppingMarket,
    trusted_market: TrustedMarketContext | None = None,
    catalog=None,
    routing_policy=None,
    shopping_markets: CertifiedShoppingMarketCatalog | None = None,
    proposal=None,
    expected_scope_digest: str | None = None,
    expected_proposal_id: str | None = None,
    expected_proposal_version: int | None = None,
) -> ResearchPlanningResult:
    """Plan only when the selected shopping market has certified coverage.

    Does not execute research. Uncertified markets never become connector-eligible.
    """

    coverage = assess_shopping_coverage(selected, catalog=shopping_markets)
    if not coverage.connector_invocation_eligible:
        return ResearchPlanningResult(planned=False, reason="unsupported_shopping_market")
    return plan_authorized_research(
        authorization,
        owner=owner,
        conversation_id=conversation_id,
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        registry=registry,
        catalog=catalog,
        routing_policy=routing_policy,
        trusted_market=trusted_market,
        proposal=proposal,
        expected_scope_digest=expected_scope_digest,
        expected_proposal_id=expected_proposal_id,
        expected_proposal_version=expected_proposal_version,
    )
