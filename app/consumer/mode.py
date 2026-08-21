"""Runtime gates for Product Foundation presentation data.

Non-live fixture catalogs are allowed only in approved development, staging, and
explicit test/demo environments. Production must never substitute fixture offer
economics for a missing canonical snapshot.
"""

from __future__ import annotations

from app.core.config import get_settings

APPROVED_FIXTURE_ENVIRONMENTS = frozenset({"development", "staging"})
UNAVAILABLE_CLASSIFICATION = "canonical_offer_economics_unavailable"


def fixture_catalogs_permitted() -> bool:
    """Return True only when non-live Product Foundation catalogs may render."""
    return get_settings().app_env in APPROVED_FIXTURE_ENVIRONMENTS
