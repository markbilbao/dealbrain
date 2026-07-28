"""Shared product-identity primitives for the Product Identity layer.

These helpers are framework-free and may be used by registry, matcher, and
application services without importing intelligence adapters.
"""

from __future__ import annotations

import re

from app.domain.entities.canonical_product import CanonicalProduct

_WHITESPACE_RE = re.compile(r"\s+")

# Fields required before a parsed product may enter the Canonical Product Registry.
REQUIRED_IDENTITY_FIELDS: tuple[str, ...] = ("brand", "family", "model")


def normalize_whitespace(value: str | None) -> str:
    """Collapse internal whitespace and lowercase for stable comparisons."""
    if value is None:
        return ""
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def missing_identity_fields(parsed: CanonicalProduct) -> list[str]:
    """Return registry-required identity fields that are absent or blank."""
    missing: list[str] = []
    for field_name in REQUIRED_IDENTITY_FIELDS:
        raw = getattr(parsed, field_name, None)
        if raw is None or not str(raw).strip():
            missing.append(field_name)
    return missing


def has_matchable_identity(parsed: CanonicalProduct) -> bool:
    """Return True when a product has enough identity for matching decisions.

    Matching is more permissive than registration: family+model or brand+model
    is sufficient to attempt a comparison. Registration still requires all of
    :data:`REQUIRED_IDENTITY_FIELDS`.
    """
    brand = (parsed.brand or "").strip()
    family = (parsed.family or "").strip()
    model = (parsed.model or "").strip()
    if family and model:
        return True
    return bool(brand and model)
