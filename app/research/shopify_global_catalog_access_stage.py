"""Sprint 32 Shopify Global Catalog access-stage record.

Narrow path-applicability record for the documented Anonymous Global Catalog
catalog mode. It is not a second certification framework and it does not
change Sprint 31 certification states.

Signed and Token tiers are optional stronger identification modes. They are
not required to prove Anonymous catalog-tool access. Promoted placement is a
different path and stays not enrolled, disabled, and policy-unknown.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.research.shopify_global_catalog_capability_policy import (
    PRODUCTION_CERTIFIED,
    SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID,
    SHOPIFY_GLOBAL_CATALOG_MARKET,
)
from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
)

CATALOG_MODE_ANONYMOUS = "anonymous_global_catalog"
APPLICATION_NOT_REQUIRED = "NO SEPARATE APPLICATION REQUIRED FOR DOCUMENTED ANONYMOUS CATALOG MODE"
PREAPPROVAL_NOT_REQUIRED = (
    "NO SEPARATE PRE-APPROVAL DOCUMENTED FOR ORDINARY ANONYMOUS CATALOG TOOLS"
)
STAGING_AGENT_PROFILE_VALIDATED = "DEPLOYED / OWNER HTTPS-VALIDATED"
TECHNICAL_CONNECTION_VALIDATED = "VALIDATED IN STAGING / LIVE SHOPIFY RESPONSE"
PRODUCTION_PROFILE_UNDEPLOYED = "UNDEPLOYED"
CONTRACTUAL_REDUCED_MODE_RECORDED = "recorded/prepared"
PROMOTED_PLACEMENT_POLICY = "unknown"
SPRINT_32_STATUS = "COMPLETE / CLOSED"
SPRINT_38_STATUS = "UNSTARTED"
SPRINT_41_STATUS = "UNSTARTED"

_FORBIDDEN_CLAIMS = (
    "shopify partner",
    "partnership with shopify",
    "shopify endorsement",
    "endorsed by shopify",
    "preferred developer",
    "preferred-developer",
    "production-app approval",
    "production app approval",
    "special approval",
)


@dataclass(frozen=True, slots=True)
class ShopifyGlobalCatalogAccessStage:
    """Applicability of access stages for one documented catalog mode."""

    catalog_mode: str
    provider_id: str
    market: str
    application_required: bool
    application_disposition: str
    separate_provider_preapproval_required: bool
    preapproval_disposition: str
    credentials_required: bool
    agent_profile_required: bool
    staging_agent_profile_deployed: bool
    staging_agent_profile_disposition: str
    technical_connection_validated: bool
    technical_connection_disposition: str
    contractual_reduced_mode_evidence: str
    production_profile_deployed: bool
    production_profile_disposition: str
    production_certified: bool
    promoted_placement_enrolled: bool
    promoted_placement_enabled: bool
    promoted_placement_policy: str
    signed_or_token_required_for_anonymous_catalog_tools: bool
    ph_technical_coverage_validated: bool
    production_provider_registered: bool
    executable_production_certification: bool
    routing_policy_registered: bool
    sprint_32_status: str
    sprint_38_status: str
    sprint_41_status: str
    production_ready: bool

    def __post_init__(self) -> None:
        if self.catalog_mode != CATALOG_MODE_ANONYMOUS:
            raise ValueError("this record is only the documented Anonymous catalog mode")
        if self.application_required or self.separate_provider_preapproval_required:
            raise ValueError("Anonymous catalog mode must not invent application or preapproval")
        if self.credentials_required:
            raise ValueError("Anonymous catalog mode must not require credentials")
        if not self.agent_profile_required:
            raise ValueError("Anonymous catalog mode still requires an agent profile")
        if self.signed_or_token_required_for_anonymous_catalog_tools:
            raise ValueError("Signed or Token tiers are not required for Anonymous catalog tools")
        if self.production_certified or self.production_ready:
            raise ValueError(
                "reduced capability certification is not production deployment readiness"
            )
        if self.promoted_placement_enrolled or self.promoted_placement_enabled:
            raise ValueError("promoted placement is not enrolled")
        if self.promoted_placement_policy != "unknown":
            raise ValueError("promoted placement policy stays unknown")
        if self.executable_production_certification:
            raise ValueError("executable production certification stays absent")
        if self.routing_policy_registered:
            raise ValueError("routing policy stays absent")
        _reject_implied_shopify_approval(self.application_disposition)
        _reject_implied_shopify_approval(self.preapproval_disposition)
        _reject_implied_shopify_approval(self.technical_connection_disposition)

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "catalog_mode": self.catalog_mode,
            "provider_id": self.provider_id,
            "market": self.market,
            "application_required": self.application_required,
            "application_disposition": self.application_disposition,
            "separate_provider_preapproval_required": (self.separate_provider_preapproval_required),
            "preapproval_disposition": self.preapproval_disposition,
            "credentials_required": self.credentials_required,
            "agent_profile_required": self.agent_profile_required,
            "staging_agent_profile_deployed": self.staging_agent_profile_deployed,
            "staging_agent_profile_disposition": self.staging_agent_profile_disposition,
            "technical_connection_validated": self.technical_connection_validated,
            "technical_connection_disposition": self.technical_connection_disposition,
            "contractual_reduced_mode_evidence": self.contractual_reduced_mode_evidence,
            "production_profile_deployed": self.production_profile_deployed,
            "production_profile_disposition": self.production_profile_disposition,
            "production_certified": self.production_certified,
            "promoted_placement_enrolled": self.promoted_placement_enrolled,
            "promoted_placement_enabled": self.promoted_placement_enabled,
            "promoted_placement_policy": self.promoted_placement_policy,
            "signed_or_token_required_for_anonymous_catalog_tools": (
                self.signed_or_token_required_for_anonymous_catalog_tools
            ),
            "ph_technical_coverage_validated": self.ph_technical_coverage_validated,
            "production_provider_registered": self.production_provider_registered,
            "executable_production_certification": self.executable_production_certification,
            "routing_policy_registered": self.routing_policy_registered,
            "sprint_32_status": self.sprint_32_status,
            "sprint_38_status": self.sprint_38_status,
            "sprint_41_status": self.sprint_41_status,
            "production_ready": self.production_ready,
        }


def anonymous_global_catalog_access_stage() -> ShopifyGlobalCatalogAccessStage:
    """Current Anonymous Global Catalog access-stage truth. Not production-ready."""

    staging_deployed = PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    production_deployed = PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is True
    technical_validated = staging_deployed and SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is True
    return ShopifyGlobalCatalogAccessStage(
        catalog_mode=CATALOG_MODE_ANONYMOUS,
        provider_id=SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID,
        market=SHOPIFY_GLOBAL_CATALOG_MARKET,
        application_required=False,
        application_disposition=APPLICATION_NOT_REQUIRED,
        separate_provider_preapproval_required=False,
        preapproval_disposition=PREAPPROVAL_NOT_REQUIRED,
        credentials_required=False,
        agent_profile_required=True,
        staging_agent_profile_deployed=staging_deployed,
        staging_agent_profile_disposition=(
            STAGING_AGENT_PROFILE_VALIDATED if staging_deployed else "NOT VALIDATED"
        ),
        technical_connection_validated=technical_validated,
        technical_connection_disposition=(
            TECHNICAL_CONNECTION_VALIDATED if technical_validated else "NOT VALIDATED"
        ),
        contractual_reduced_mode_evidence=CONTRACTUAL_REDUCED_MODE_RECORDED,
        production_profile_deployed=production_deployed,
        production_profile_disposition=(
            "DEPLOYED" if production_deployed else PRODUCTION_PROFILE_UNDEPLOYED
        ),
        production_certified=PRODUCTION_CERTIFIED,
        promoted_placement_enrolled=False,
        promoted_placement_enabled=False,
        promoted_placement_policy=PROMOTED_PLACEMENT_POLICY,
        signed_or_token_required_for_anonymous_catalog_tools=False,
        ph_technical_coverage_validated=True,
        production_provider_registered=True,
        executable_production_certification=False,
        routing_policy_registered=False,
        sprint_32_status=SPRINT_32_STATUS,
        sprint_38_status=SPRINT_38_STATUS,
        sprint_41_status=SPRINT_41_STATUS,
        production_ready=False,
    )


def shopify_anonymous_catalog_stage_truth() -> dict[str, str]:
    """Section-5 stage report. Evidence and staging validation are not production."""

    stage = anonymous_global_catalog_access_stage()
    return {
        "application_required": "N/A for documented Anonymous catalog mode",
        "provider_preapproval_required": ("N/A for ordinary documented Anonymous catalog tools"),
        "credentials": "N/A / not required for Anonymous catalog mode",
        "agent_profile": "required" if stage.agent_profile_required else "not required",
        "staging_profile": "validated" if stage.staging_agent_profile_deployed else "not validated",
        "live_technical_connection": (
            "validated" if stage.technical_connection_validated else "not validated"
        ),
        "ph_technical_coverage": (
            "validated" if stage.ph_technical_coverage_validated else "not validated"
        ),
        "capability_policy_evidence": stage.contractual_reduced_mode_evidence,
        "production_profile": (
            "not deployed" if not stage.production_profile_deployed else "deployed"
        ),
        "production_provider": "registered, operationally disabled",
        "executable_production_certification": "none",
        "routing": "none",
        "production_certified": "NO",
        "sprint_32": stage.sprint_32_status,
        "sprint_38": stage.sprint_38_status,
        "sprint_41": stage.sprint_41_status,
        "production_ready": "NO",
    }


def _reject_implied_shopify_approval(text: str) -> None:
    lowered = text.casefold()
    for phrase in _FORBIDDEN_CLAIMS:
        if phrase in lowered:
            raise ValueError("access-stage wording must not imply Shopify approval or endorsement")
