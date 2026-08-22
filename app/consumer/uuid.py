"""Canonical decision UUID recognition for consumer document routes."""

from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def is_canonical_uuid(decision_id: str) -> bool:
    """Return True when the path segment is a server-owned decision UUID."""

    return bool(decision_id and _UUID_RE.match(decision_id.strip()))
