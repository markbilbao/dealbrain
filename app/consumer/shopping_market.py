"""Guest-session shopping-market cookie.

Stores only a validated ISO country code. Delivery destination, street, GPS,
and location history must not appear here.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import unquote

from starlette.responses import Response

from app.market.selection import (
    SelectedShoppingMarket,
    ShoppingMarketValidationError,
    intended_default_shopping_market,
    selected_shopping_market_from_code,
)

SHOPPING_MARKET_COOKIE = "piqsavi_shopping_market"
COOKIE_MAX_BYTES = 128
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
        "city",
        "postal_code",
    }
)


def parse_shopping_market_cookie(raw: str | None) -> SelectedShoppingMarket | None:
    """Return an explicit selection, or None when missing/invalid."""

    if not raw:
        return None
    try:
        payload = json.loads(unquote(raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if _PRIVACY_FORBIDDEN_FIELDS.intersection(payload):
        return None
    try:
        return selected_shopping_market_from_code(payload.get("country_code"), origin="explicit")
    except ShoppingMarketValidationError:
        return None


def shopping_market_from_cookie(raw: str | None) -> SelectedShoppingMarket:
    """Explicit cookie selection, else the intended PH default."""

    parsed = parse_shopping_market_cookie(raw)
    return parsed if parsed is not None else intended_default_shopping_market()


def set_shopping_market_cookie(response: Response, selected: SelectedShoppingMarket) -> None:
    payload = selected.to_cookie_payload()
    leaked = _PRIVACY_FORBIDDEN_FIELDS.intersection(payload)
    if leaked:
        raise ShoppingMarketValidationError("shopping market cookie must not store location fields")
    encoded = json.dumps(payload, separators=(",", ":"))
    if len(encoded) > COOKIE_MAX_BYTES:
        raise ShoppingMarketValidationError("Shopping market context is too large to store.")
    response.set_cookie(
        SHOPPING_MARKET_COOKIE,
        encoded,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_shopping_market_cookie(response: Response) -> None:
    response.delete_cookie(SHOPPING_MARKET_COOKIE, path="/")


def cookie_payload_is_safe(payload: dict[str, Any]) -> bool:
    return not _PRIVACY_FORBIDDEN_FIELDS.intersection(payload)
