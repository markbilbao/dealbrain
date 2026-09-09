"""Fail-closed tracking permission — essential-only until Sprint 39 / EXT-22.

PiqSavi currently has no approved non-essential analytics provider. This module
does not implement a CMP banner, does not load third-party pixels, and does not
claim counsel approval. Absence of a CMP or analytics provider fails privacy-safe:
non-essential categories stay OFF.

Public product state and operator EXT/Sprint ownership are split: only the
product fields belong on unauthenticated APIs.
"""

from __future__ import annotations

from typing import Any, Literal

TrackingCategory = Literal["essential", "analytics", "advertising"]
TrackingMode = Literal["essential_only"]

TRACKING_MODE: TrackingMode = "essential_only"
HTML_TRACKING_MODE_ATTR = "essential-only"
CMP_VENDOR: str | None = None
ANALYTICS_PROVIDER: str | None = None

NON_ESSENTIAL_CATEGORIES: tuple[TrackingCategory, ...] = ("analytics", "advertising")

# Operator-only EXT/Sprint ownership. Not a public API field.
EXT_22_STATUS = "not_started"
ACTIVATION_OWNER = "sprint_39"


def tracking_mode() -> TrackingMode:
    """Current product tracking mode. Sprint 39 owns later CMP activation."""
    return TRACKING_MODE


def cmp_vendor() -> str | None:
    """No CMP vendor is wired. EXT-22 remains not_started."""
    return CMP_VENDOR


def analytics_provider() -> str | None:
    """No analytics provider is wired. EXT-15 / Sprint 39 remain owners."""
    return ANALYTICS_PROVIDER


def category_allowed(category: TrackingCategory) -> bool:
    """Return whether a tracking category may execute.

    Essential first-party storage may run. Analytics and advertising cannot
    execute while no provider is configured and no published CMP consent exists.
    """
    return category == "essential"


def non_essential_tracking_allowed() -> bool:
    """True only if a future CMP + provider path explicitly enables a category.

    Current production path is always False.
    """
    if analytics_provider() is None or cmp_vendor() is None:
        return False
    return any(category_allowed(category) for category in NON_ESSENTIAL_CATEGORIES)


def tracking_public_state() -> dict[str, Any]:
    """Product tracking posture safe for unauthenticated clients."""
    return {
        "tracking_mode": tracking_mode(),
        "cmp_vendor": cmp_vendor(),
        "analytics_provider": analytics_provider(),
        "essential_allowed": category_allowed("essential"),
        "analytics_allowed": category_allowed("analytics"),
        "advertising_allowed": category_allowed("advertising"),
        "non_essential_tracking_allowed": non_essential_tracking_allowed(),
        "banner_implemented": False,
    }


def tracking_snapshot() -> dict[str, Any]:
    """Operator-visible tracking posture including EXT-22 / Sprint 39 ownership."""
    return {
        **tracking_public_state(),
        "ext_22_status": EXT_22_STATUS,
        "activation_owner": ACTIVATION_OWNER,
    }
