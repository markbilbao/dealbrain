"""Search-index privacy helpers for personalized consumer decision pages."""

from __future__ import annotations

from starlette.responses import Response

NOINDEX_ROBOTS_TAG = "noindex, nofollow"
PRIVATE_DECISION_PREFIXES = ("/results/", "/compare/", "/why-best-piq/")


def apply_private_decision_noindex(response: Response) -> Response:
    """Mark a personalized decision HTML response as non-indexable."""
    response.headers["X-Robots-Tag"] = NOINDEX_ROBOTS_TAG
    return response


def is_private_decision_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PRIVATE_DECISION_PREFIXES)
