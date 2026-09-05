"""Engineering PII export categories — not a legal completeness certification.

Kept in code so export completeness tests share one source of truth with the
engineering inventory document.
"""

from __future__ import annotations

from typing import Any

EXPORT_SCHEMA = "piqsavi.account_owned_export.v1"
EXPORT_KIND = "account_owned_engineering_export"

# Categories attributable to the requesting consumer account.
PERSONAL_DATA_EXPORT_CATEGORIES: tuple[str, ...] = (
    "account",
    "profile",
    "settings",
    "wishlist",
    "saved_products",
    "saved_comparisons",
    "recommendation_history",
    "saved_searches",
    "recently_viewed",
    "consent_records",
    "sessions",
    "notification_preferences",
)

SECURITY_FIELDS_EXCLUDED_FROM_EXPORT: tuple[str, ...] = (
    "password_hash",
    "token_hash",
    "csrf_token",
    "access_token",
    "reset_token",
    "verification_token",
    "email_change_token",
)

# Browser/server stores that are not account-exportable (guest/session device).
NON_ACCOUNT_BROWSER_STORES: tuple[str, ...] = (
    "piqsavi_decision_owner",
    "piqsavi_delivery",
    "piqsavi_shopping_market",
    "piqsavi_ask_conversation",
)

# Intentionally excluded from consumer export (and why).
EXPORT_EXCLUSIONS: dict[str, str] = {
    "password_hash": "credential secret; never exported",
    "session token_hash / csrf_token / raw access_token": "internal security material",
    "password-reset / email-verification tokens": "raw and hashed security tokens",
    "email-change pending records / token hashes / intended new_email": (
        "security tokens and unconfirmed destination; not an export category"
    ),
    "other users' data": "ownership isolation",
    "Early Access waitlist": "not a User account; no trusted user_id link",
    "application / request logs": "operational, not account-owned export",
    "audit event payloads beyond the user's own consent/deletion metadata": (
        "security evidence; not a consumer export category"
    ),
}


def strip_security_fields(value: Any) -> Any:
    """Recursively drop known security keys from an export payload."""
    if isinstance(value, dict):
        return {
            key: strip_security_fields(item)
            for key, item in value.items()
            if key not in SECURITY_FIELDS_EXCLUDED_FROM_EXPORT
        }
    if isinstance(value, list):
        return [strip_security_fields(item) for item in value]
    return value
