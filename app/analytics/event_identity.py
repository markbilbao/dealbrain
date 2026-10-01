"""Deterministic product-analytics event ids.

The id is a UUID derived from non-PII parts. It is not a raw decision id,
proposal id, or subject cookie. Missing parts must not be replaced with a guess.
"""

from __future__ import annotations

import uuid

_NAMESPACE = uuid.UUID("6ba7b81b-9dad-11d1-80b4-00c04fd430c8")
_PREFIX = "piqsavi.product_analytics.event_id.v1"


def deterministic_event_id(*parts: str) -> str | None:
    """Return a stable UUID, or None when any identity part is missing."""

    if not parts or any(not isinstance(part, str) or not part for part in parts):
        return None
    material = _PREFIX + "\n" + "\n".join(parts)
    return str(uuid.uuid5(_NAMESPACE, material))
