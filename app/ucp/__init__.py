"""Public UCP protocol documents hosted by the PiqSavi FastAPI application."""

from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE,
    PIQSAVI_UCP_AGENT_PROFILE_PATH,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
    PIQSAVI_UCP_VERSION,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    TRUSTED_PIQSAVI_UCP_AGENT_PROFILE_URLS,
    piqsavi_profile_deployed_for_url,
    piqsavi_profile_is_shopify_negotiated,
    serialize_piqsavi_ucp_agent_profile,
    trusted_piqsavi_ucp_agent_profile_url,
)

__all__ = [
    "PIQSAVI_UCP_AGENT_PROFILE",
    "PIQSAVI_UCP_AGENT_PROFILE_PATH",
    "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED",
    "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL",
    "PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED",
    "PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL",
    "PIQSAVI_UCP_VERSION",
    "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE",
    "TRUSTED_PIQSAVI_UCP_AGENT_PROFILE_URLS",
    "piqsavi_profile_deployed_for_url",
    "piqsavi_profile_is_shopify_negotiated",
    "serialize_piqsavi_ucp_agent_profile",
    "trusted_piqsavi_ucp_agent_profile_url",
]
