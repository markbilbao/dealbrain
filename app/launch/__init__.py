"""Launch readiness & production preparation (Sprint 22).

Demo/in-memory safe. Does not alter DealScore, organic ranking, or affiliate
ranking. No real cloud deployment, payments, or production secrets.
"""

from app.launch.feature_flags import FeatureFlagRegistry, get_feature_flags
from app.launch.runtime import get_startup_instant, mark_startup, uptime_seconds

__all__ = [
    "FeatureFlagRegistry",
    "get_feature_flags",
    "get_startup_instant",
    "mark_startup",
    "uptime_seconds",
]
