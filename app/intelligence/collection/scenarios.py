"""Shared fixture scenarios for mock marketplace collectors."""

from __future__ import annotations

from typing import Any

# Scenario tokens recognized by mock collectors.
SCENARIO_SUCCESS = "success"
SCENARIO_EMPTY = "empty"
SCENARIO_PARTIAL_FAILURE = "partial_failure"
SCENARIO_TOTAL_FAILURE = "total_failure"
SCENARIO_UNAVAILABLE = "unavailable"
SCENARIO_MALFORMED = "malformed"
SCENARIO_DUPLICATE = "duplicate"

ALL_SCENARIOS: frozenset[str] = frozenset(
    {
        SCENARIO_SUCCESS,
        SCENARIO_EMPTY,
        SCENARIO_PARTIAL_FAILURE,
        SCENARIO_TOTAL_FAILURE,
        SCENARIO_UNAVAILABLE,
        SCENARIO_MALFORMED,
        SCENARIO_DUPLICATE,
    }
)


def resolve_scenario(explicit: str | None, query: str) -> str:
    """Resolve scenario from explicit field or ``scenario:<name>`` query prefix."""
    if explicit and explicit.strip():
        return explicit.strip().lower()
    cleaned = query.strip().lower()
    if cleaned.startswith("scenario:"):
        token = cleaned.split(":", 1)[1].split(None, 1)[0]
        return token or SCENARIO_SUCCESS
    return SCENARIO_SUCCESS


def strip_scenario_prefix(query: str) -> str:
    """Remove optional ``scenario:<name>`` prefix from a query string."""
    cleaned = query.strip()
    lower = cleaned.lower()
    if not lower.startswith("scenario:"):
        return cleaned
    rest = cleaned.split(":", 1)[1]
    parts = rest.split(None, 1)
    return parts[1] if len(parts) > 1 else ""


def filter_by_query(raw_listings: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Case-insensitive substring match over title/name/seller fields."""
    needle = strip_scenario_prefix(query).strip().lower()
    if not needle:
        return list(raw_listings)
    matches: list[dict[str, Any]] = []
    for raw in raw_listings:
        haystack = " ".join(
            str(raw.get(key, ""))
            for key in ("name", "title", "shop_name", "sellerName", "seller")
        ).lower()
        if needle in haystack:
            matches.append(raw)
    return matches
