"""URL trust-boundary checks.

Browser destinations and server-side fetches do not share one policy.
"""

from app.security.url_trust import (
    BROWSER_URL_SCHEMES,
    SERVER_FETCH_SCHEMES,
    UrlTrustError,
    validate_browser_destination,
    validate_server_fetch_url,
)

__all__ = [
    "BROWSER_URL_SCHEMES",
    "SERVER_FETCH_SCHEMES",
    "UrlTrustError",
    "validate_browser_destination",
    "validate_server_fetch_url",
]
