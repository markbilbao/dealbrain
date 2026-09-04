"""Attach truthful currency-conversion state to consumer page views."""

from __future__ import annotations

from dataclasses import replace

from app.consumer.view_models import DecisionPageView, ProductCardView
from app.market.context import DEFAULT_DISPLAY_CURRENCY
from app.market.currency import assess_offer_currencies
from app.market.fx import CurrencyAuthorityError, FxQuote, normalize_currency_code


def attach_currency_presentation(
    view: DecisionPageView,
    *,
    preferred_currency: str | None = None,
    quote: FxQuote | None = None,
) -> DecisionPageView:
    preferred = preferred_currency or DEFAULT_DISPLAY_CURRENCY
    assessed = assess_offer_currencies(
        _source_currencies(view),
        preferred_currency=preferred,
        quote=quote,
    )
    return replace(
        view,
        preferred_display_currency=assessed.preferred_currency,
        currency_conversion_state=assessed.state,
        currency_conversion_disclosure=assessed.disclosure,
        source_currencies=assessed.source_currencies,
    )


def _source_currencies(view: DecisionPageView) -> tuple[str, ...]:
    cards: tuple[ProductCardView, ...] = (
        view.best_piq,
        *view.alternatives,
        *view.compared,
    )
    seen: list[str] = []
    for card in cards:
        listing = card.economics.listing
        code = normalize_currency_code(listing.currency)
        if listing.amount is not None and code is None:
            raise CurrencyAuthorityError("source currency is required and must not be assumed")
        if code and code not in seen:
            seen.append(code)
    return tuple(seen)
