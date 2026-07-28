"""Screen size normalization helpers."""

from __future__ import annotations

import re

_SCREEN_RE = re.compile(
    r"^(?P<size>\d{1,2}(?:\.\d)?)\s*(?:-?inch|in|\"|”)?$",
    re.IGNORECASE,
)


def normalize_screen_size(token: str) -> str | None:
    """Normalize tokens like ``13-inch``, ``13"``, ``14inch`` → ``13-inch``."""
    cleaned = token.strip().lower().replace("”", '"').replace("″", '"')
    if not cleaned:
        return None

    # Require an inch marker so bare numbers are not treated as screen sizes.
    if not any(marker in cleaned for marker in ("inch", "in", '"')):
        # Allow forms already joined like 13inch
        if not cleaned.endswith("inch") and not cleaned.endswith("in"):
            return None

    match = _SCREEN_RE.fullmatch(cleaned.replace(" ", ""))
    if not match:
        # Try with spaces stripped differently: "13-inch"
        compact = cleaned.replace(" ", "")
        match = _SCREEN_RE.fullmatch(compact)
    if not match:
        return None

    size = match.group("size")
    return f"{size}-inch"
