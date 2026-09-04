"""Cost-completeness helper for Sprint 37.1.

Wraps existing ``select_price_state``. Does not invent missing amounts or
convert currencies.
"""

from __future__ import annotations

from app.consumer.pricing import MoneyComponent, PriceState, select_price_state
from app.market.context import MarketContext


def select_dominant_price_state(
    *,
    market: MarketContext,
    shipping: MoneyComponent,
    taxes: MoneyComponent,
    import_charges: MoneyComponent | None,
    savings: tuple[MoneyComponent, ...],
    international: bool,
    shipping_material: bool,
    destination_sensitive_stale: bool = False,
) -> PriceState:
    """Choose the honest dominant label from captured completeness + destination state."""

    location_known = market.destination_is_known_for_cost and not destination_sensitive_stale
    return select_price_state(
        shipping=shipping,
        taxes=taxes,
        import_charges=import_charges,
        savings=savings,
        international=international,
        location_known=location_known,
        shipping_material=shipping_material,
    )


def mixed_currency_blocks_compare(
    source_currency: str | None,
    display_currency: str | None,
) -> bool:
    """True when currencies differ.

    Production has no FX quote in 37.3. Display preference is not a rate.
    """

    source = (source_currency or "").strip().upper()
    display = (display_currency or "").strip().upper()
    return bool(source and display and source != display)
