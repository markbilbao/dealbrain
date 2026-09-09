"""Fail-closed minimum-age and country-notice placeholders.

Sprint 28 requires placeholders, not an invented age gate. Counsel still owns
the minimum age, parental-consent rules, and country-specific legal copy.
Until those are published, this module records that no age or country notice
is in force and that registration must not collect date of birth.

Public product state omits counsel-workflow ownership flags.
"""

from __future__ import annotations

from typing import Any

MINIMUM_AGE_YEARS: int | None = None
COUNTRY_NOTICES: tuple[dict[str, Any], ...] = ()


def minimum_age_years() -> int | None:
    """None until counsel publishes an approved minimum age. Do not invent 13/18."""
    return MINIMUM_AGE_YEARS


def age_policy_published() -> bool:
    return minimum_age_years() is not None


def country_notices() -> tuple[dict[str, Any], ...]:
    """Empty until counsel-approved country notices exist. Sprint 37 owns market UI."""
    return COUNTRY_NOTICES


def country_notices_published() -> bool:
    return bool(country_notices())


def collects_date_of_birth() -> bool:
    """Registration does not collect DOB while age policy is unpublished."""
    return False


def eligibility_public_state() -> dict[str, Any]:
    """Product eligibility posture safe for unauthenticated clients."""
    return {
        "minimum_age_years": minimum_age_years(),
        "age_policy_published": age_policy_published(),
        "collects_date_of_birth": collects_date_of_birth(),
        "parental_consent_flow": False,
        "country_notices_published": country_notices_published(),
        "country_notice_count": len(country_notices()),
        "enforced_at_registration": False,
    }


def eligibility_snapshot() -> dict[str, Any]:
    """Operator-visible eligibility posture including counsel ownership."""
    return {
        **eligibility_public_state(),
        "counsel_owned": True,
    }
