"""PiqSavi-owned UCP agent profile — production-intended, not yet deployed.

Static server-owned JSON for Shopify/UCP capability negotiation. This is not
Shopify's hosted test fixture, not a business ``/.well-known/ucp`` document,
and not a production certification of Shopify.

Least privilege: product discovery / comparison only. Declaring
``dev.ucp.shopping.catalog.lookup`` is required because official
``dev.shopify.catalog.global`` extends both catalog.search and catalog.lookup,
and UCP maps ``get_product`` to Lookup. It is not permission to run bulk
``lookup_catalog`` from the Sprint 32 probe.
"""

from __future__ import annotations

import json
from typing import Any, Final

PIQSAVI_UCP_VERSION: Final = "2026-08-25"
PIQSAVI_UCP_AGENT_PROFILE_PATH: Final = "/ucp/agent-profiles/2026-08-25/piqsavi.json"
PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL: Final = (
    "https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json"
)
PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL: Final = (
    "https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json"
)
SHOPIFY_TECHNICAL_TEST_AGENT_PROFILE_URL: Final = (
    "https://shopify.dev/ucp/agent-profiles/2026-08-25/valid-with-capabilities.json"
)
PIQSAVI_UCP_AGENT_PROFILE_CONTENT_TYPE: Final = "application/json"
PIQSAVI_UCP_AGENT_PROFILE_CACHE_CONTROL: Final = "public, max-age=300"
PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED: Final = False
SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE: Final = False

CAPABILITY_CATALOG_SEARCH: Final = "dev.ucp.shopping.catalog.search"
CAPABILITY_CATALOG_LOOKUP: Final = "dev.ucp.shopping.catalog.lookup"
CAPABILITY_SHOPIFY_GLOBAL_CATALOG: Final = "dev.shopify.catalog.global"

DECLARED_CAPABILITY_NAMES: Final[tuple[str, ...]] = (
    CAPABILITY_CATALOG_SEARCH,
    CAPABILITY_CATALOG_LOOKUP,
    CAPABILITY_SHOPIFY_GLOBAL_CATALOG,
)

FORBIDDEN_PROFILE_CAPABILITIES: Final[tuple[str, ...]] = (
    "dev.ucp.shopping.cart",
    "dev.ucp.shopping.checkout",
    "dev.ucp.shopping.order",
    "dev.ucp.shopping.fulfillment",
    "dev.ucp.shopping.buyer_consent",
    "dev.ucp.shopping.discount",
    "dev.ucp.shopping.payment",
    "dev.shopify.catalog",
)

_SECRET_MARKERS: Final[tuple[str, ...]] = (
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "bearer ",
    "private_key",
    "begin rsa",
    "begin openssh",
    "akia",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    ".internal",
    ".local",
    "credential",
    "account_id",
)

PIQSAVI_UCP_AGENT_PROFILE: Final[dict[str, Any]] = {
    "ucp": {
        "version": PIQSAVI_UCP_VERSION,
        "capabilities": {
            CAPABILITY_CATALOG_SEARCH: [
                {
                    "version": PIQSAVI_UCP_VERSION,
                    "spec": "https://ucp.dev/2026-08-25/specification/catalog/search",
                    "schema": "https://ucp.dev/2026-08-25/schemas/shopping/catalog_search.json",
                }
            ],
            CAPABILITY_CATALOG_LOOKUP: [
                {
                    "version": PIQSAVI_UCP_VERSION,
                    "spec": "https://ucp.dev/2026-08-25/specification/catalog/lookup",
                    "schema": "https://ucp.dev/2026-08-25/schemas/shopping/catalog_lookup.json",
                }
            ],
            CAPABILITY_SHOPIFY_GLOBAL_CATALOG: [
                {
                    "version": PIQSAVI_UCP_VERSION,
                    "spec": "https://shopify.dev/docs/agents/catalog/global-catalog",
                    "schema": (
                        "https://shopify.dev/ucp/schemas/2026-08-25/shopify_catalog_global.json"
                    ),
                    "extends": [
                        CAPABILITY_CATALOG_SEARCH,
                        CAPABILITY_CATALOG_LOOKUP,
                    ],
                }
            ],
        },
    }
}


def serialize_piqsavi_ucp_agent_profile() -> str:
    """Return the deterministic public JSON document, including trailing newline."""

    return json.dumps(PIQSAVI_UCP_AGENT_PROFILE, ensure_ascii=True, indent=2) + "\n"


def declared_capability_names(profile: dict[str, Any] | None = None) -> tuple[str, ...]:
    document = profile if profile is not None else PIQSAVI_UCP_AGENT_PROFILE
    ucp = document.get("ucp") if isinstance(document, dict) else None
    capabilities = ucp.get("capabilities") if isinstance(ucp, dict) else None
    if not isinstance(capabilities, dict):
        return ()
    return tuple(capabilities)


def profile_contains_secrets(document: dict[str, Any] | str | None = None) -> bool:
    """True when the public profile would leak credentials or private infrastructure."""

    if document is None:
        blob = serialize_piqsavi_ucp_agent_profile()
    elif isinstance(document, str):
        blob = document
    else:
        blob = json.dumps(document)
    lowered = blob.casefold()
    return any(marker in lowered for marker in _SECRET_MARKERS)


def trusted_piqsavi_ucp_agent_profile_url() -> str:
    """Server-owned HTTPS URL. Never derived from request, cookies, or query."""

    from app.core.config import get_settings

    configured = str(getattr(get_settings(), "piqsavi_ucp_agent_profile_url", "") or "").strip()
    url = configured or PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    if not url.startswith("https://"):
        raise ValueError("PIQSAVI_UCP_AGENT_PROFILE_URL must be a public HTTPS URL")
    if url.rstrip("/") == SHOPIFY_TECHNICAL_TEST_AGENT_PROFILE_URL.rstrip("/"):
        raise ValueError(
            "PIQSAVI_UCP_AGENT_PROFILE_URL must be PiqSavi-owned, not Shopify's test fixture"
        )
    if "shopify.dev/ucp/agent-profiles" in url:
        raise ValueError(
            "PIQSAVI_UCP_AGENT_PROFILE_URL must not impersonate Shopify hosted agent profiles"
        )
    return url
