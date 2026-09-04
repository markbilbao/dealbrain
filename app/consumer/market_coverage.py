"""Attach truthful shopping-market coverage to consumer page views."""

from __future__ import annotations

from dataclasses import replace

from app.consumer.view_models import DecisionPageView
from app.market.coverage import (
    FIXTURE_NOT_CERTIFIED_DISCLOSURE,
    ShoppingMarketCoverage,
    assess_shopping_coverage,
)
from app.market.selection import SelectedShoppingMarket, intended_default_shopping_market


def attach_shopping_coverage(
    view: DecisionPageView,
    selected: SelectedShoppingMarket | None = None,
    *,
    coverage: ShoppingMarketCoverage | None = None,
) -> DecisionPageView:
    market = selected if selected is not None else intended_default_shopping_market()
    assessed = coverage if coverage is not None else assess_shopping_coverage(market)
    disclosure = assessed.disclosure
    if view.presentation_mode == "fixture":
        disclosure = f"{assessed.disclosure} {FIXTURE_NOT_CERTIFIED_DISCLOSURE}"
    return replace(
        view,
        shopping_market_certified=assessed.certified,
        selected_shopping_market=market.country_code,
        shopping_market_origin=market.origin,
        shopping_coverage_available=assessed.coverage_available,
        shopping_coverage_reason=assessed.reason,
        shopping_coverage_disclosure=disclosure,
        connector_invocation_eligible=assessed.connector_invocation_eligible,
    )
