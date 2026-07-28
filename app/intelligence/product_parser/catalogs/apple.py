"""Apple product family / model abbreviation catalog.

Compound tokens like ``IP17PM`` encode family + generation + tier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Family abbreviations → canonical family name.
FAMILY_ALIASES: dict[str, str] = {
    "iphone": "iPhone",
    "ip": "iPhone",
    "iph": "iPhone",
    "ipad": "iPad",
    "iwatch": "Apple Watch",
    "watch": "Apple Watch",
    "airpods": "AirPods",
    "app": "AirPods",
    "macbook": "MacBook",
    "mbp": "MacBook Pro",
    "mba": "MacBook Air",
    "imac": "iMac",
}

# Multi-token family refinements: (base_family, next_token) → refined family.
FAMILY_REFINEMENTS: dict[tuple[str, str], str] = {
    ("macbook", "air"): "MacBook Air",
    ("macbook", "pro"): "MacBook Pro",
}

# Model-tier suffixes after the generation number.
TIER_ALIASES: dict[str, str] = {
    "pm": "Pro Max",
    "promax": "Pro Max",
    "pro max": "Pro Max",
    "p": "Pro",
    "pro": "Pro",
    "plus": "Plus",
    "+": "Plus",
    "air": "Air",
    "mini": "Mini",
    "se": "SE",
}

# Standalone family tokens that are not compound with generation.
STANDALONE_FAMILIES: frozenset[str] = frozenset(FAMILY_ALIASES.keys())


@dataclass(frozen=True, slots=True)
class AppleModelMatch:
    """Result of matching an Apple compound model token."""

    family: str
    model: str
    source: str
    generation: str
    tier: str | None
    connector: str | None = None


# IP17PM, IPH16P, IPHONE15PROMAX, IP15+, 17PM (family implied by context)
_COMPOUND_RE = re.compile(
    r"""
    ^
    (?P<family>iphone|iph|ip|ipad)?   # optional family prefix
    (?P<gen>\d{1,2})                  # generation
    (?P<tier>promax|pro\s*max|pm|pro|p|plus|\+|air|mini|se)?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)

# APP2, APP2USBC, AIRPODSPRO2 — AirPods Pro shorthand
_AIRPODS_COMPOUND_RE = re.compile(
    r"""
    ^
    (?:app|airpodspro|appro)
    (?P<gen>\d)
    (?P<connector>usbc|usb-c|typec|type-c)?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)

_CHIP_RE = re.compile(r"^m\d$", re.IGNORECASE)


def match_apple_compound(token: str) -> AppleModelMatch | None:
    """Match a single compound token such as ``IP17PM`` or ``17PM``."""
    cleaned = token.strip().lower().replace("-", "").replace("_", "")
    if not cleaned:
        return None

    airpods = _AIRPODS_COMPOUND_RE.fullmatch(cleaned)
    if airpods:
        gen = airpods.group("gen")
        connector_raw = airpods.group("connector")
        connector = None
        if connector_raw:
            connector = "USB-C"
        return AppleModelMatch(
            family="AirPods",
            model=f"Pro {gen}",
            source=token,
            generation=gen,
            tier="Pro",
            connector=connector,
        )

    match = _COMPOUND_RE.fullmatch(cleaned)
    if not match:
        return None

    family_key = match.group("family")
    gen = match.group("gen")
    tier_key = match.group("tier")

    # Bare generation like ``17`` alone is too ambiguous without family context.
    if family_key is None and tier_key is None:
        return None

    family = FAMILY_ALIASES.get(family_key, "iPhone") if family_key else "iPhone"
    tier_norm = None
    if tier_key:
        tier_norm = TIER_ALIASES.get(tier_key.replace(" ", "").lower()) or TIER_ALIASES.get(
            tier_key.lower()
        )
        if tier_norm is None and tier_key.lower().replace(" ", "") == "promax":
            tier_norm = "Pro Max"

    model = f"{gen} {tier_norm}".strip() if tier_norm else gen
    return AppleModelMatch(
        family=family,
        model=model,
        source=token,
        generation=gen,
        tier=tier_norm,
    )


def resolve_tier(token: str) -> str | None:
    """Resolve a standalone tier token to a canonical tier label."""
    return TIER_ALIASES.get(token.strip().lower())


def is_apple_chip(token: str) -> bool:
    """Return True if token looks like an Apple Silicon chip (M1–M9)."""
    return bool(_CHIP_RE.fullmatch(token.strip().lower()))
