"""Storage capacity catalog and normalization helpers."""

from __future__ import annotations

import re

# Bare numeric capacities commonly seen in mobile listings (GB implied).
BARE_STORAGE_GB: frozenset[str] = frozenset(
    {"16", "32", "64", "128", "256", "512", "1024"}
)

# Explicit alias → canonical storage label.
STORAGE_ALIASES: dict[str, str] = {
    "1tb": "1TB",
    "1t": "1TB",
    "2tb": "2TB",
    "2t": "2TB",
    "1tbssd": "1TB",
    "512gb": "512GB",
    "512g": "512GB",
    "256gb": "256GB",
    "256g": "256GB",
    "128gb": "128GB",
    "128g": "128GB",
    "64gb": "64GB",
    "64g": "64GB",
    "32gb": "32GB",
    "32g": "32GB",
    "16gb": "16GB",
    "16g": "16GB",
    "1024gb": "1TB",
    "1024g": "1TB",
}

_EXPLICIT_STORAGE_RE = re.compile(
    r"^(?P<num>\d+)\s*(?P<unit>tb|t|gb|g)$",
    re.IGNORECASE,
)


def normalize_storage(token: str) -> str | None:
    """Return canonical storage label for a token, or None if not storage."""
    cleaned = token.strip().lower().replace(" ", "")
    if not cleaned:
        return None

    if cleaned in STORAGE_ALIASES:
        return STORAGE_ALIASES[cleaned]

    match = _EXPLICIT_STORAGE_RE.fullmatch(cleaned)
    if match:
        num = int(match.group("num"))
        unit = match.group("unit").lower()
        if unit in {"tb", "t"}:
            return f"{num}TB"
        if num == 1024:
            return "1TB"
        return f"{num}GB"

    if cleaned in BARE_STORAGE_GB:
        return f"{cleaned}GB"

    return None
