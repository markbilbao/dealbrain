"""Deterministic identity key generation for the Canonical Product Registry.

Builds on domain identity primitives; this module owns registry-specific
key formatting (slug segments and display names).
"""

from __future__ import annotations

import hashlib
import re

from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.exceptions import InsufficientCanonicalIdentityError
from app.domain.identity import missing_identity_fields, normalize_whitespace

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Re-export for callers that historically imported from this module.
normalize_identity_part = normalize_whitespace


def slugify(value: str) -> str:
    """Convert a normalized part into a URL-safe slug segment."""
    slug = _SLUG_RE.sub("-", value).strip("-")
    return slug or "_"


def build_display_name(parsed: CanonicalProduct) -> str:
    """Human-readable display name from canonical attributes."""
    parts = [
        parsed.brand,
        parsed.family,
        parsed.model,
        parsed.storage,
        parsed.color,
    ]
    return " ".join(part.strip() for part in parts if part and str(part).strip())


def build_identity_key(parsed: CanonicalProduct) -> str:
    """Build a deterministic, unique identity key for a parsed product.

    Format::

        {brand}/{family}/{model}/{storage|_|}/{color|_}

    Storage and color participate in identity so variant SKUs remain distinct
    (e.g. 256GB Black Titanium ≠ 512GB White Titanium). Missing optional
    dimensions use ``_`` as a stable sentinel.
    """
    missing = missing_identity_fields(parsed)
    if missing:
        raise InsufficientCanonicalIdentityError(missing)

    brand = slugify(normalize_whitespace(parsed.brand))
    family = slugify(normalize_whitespace(parsed.family))
    model = slugify(normalize_whitespace(parsed.model))
    storage = slugify(normalize_whitespace(parsed.storage)) if parsed.storage else "_"
    color = slugify(normalize_whitespace(parsed.color)) if parsed.color else "_"
    return f"{brand}/{family}/{model}/{storage}/{color}"


def build_identity_hash(identity_key: str) -> str:
    """SHA-256 hex digest of an identity key (sharding / compact indexes)."""
    return hashlib.sha256(identity_key.encode("utf-8")).hexdigest()
