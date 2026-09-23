"""Named-market access requirement rule.

A named market needs a legitimate authorized access path whose actual access
requirements are satisfied. That may be either provider approval, provisioning,
and credentials where the selected path requires them, or official provider
documentation of a public/keyless/anonymous mode with no separate credential
or preapproval stage, plus the remaining certification evidence.

The keyless exception applies only when that mode is officially documented.
It does not waive Shopee, Lazada, or any other credential-required path.
Satisfied access requirements do not name a market and do not certify a path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.research.shopify_global_catalog_access_stage import (
    anonymous_global_catalog_access_stage,
)

ApplicationState = Literal["not_required", "not_started", "applied", "satisfied"]
PreapprovalState = Literal["not_required", "not_approved", "approved"]
CredentialsState = Literal["not_required", "not_issued", "issued"]


@dataclass(frozen=True, slots=True)
class LegitimateAccessPath:
    """One selected provider path and the access stages that path actually has."""

    path_id: str
    market: str
    application_required: bool
    separate_provider_preapproval_required: bool
    credentials_required: bool
    official_keyless_anonymous_mode_documented: bool
    application_state: ApplicationState
    provider_preapproval_state: PreapprovalState
    credentials_state: CredentialsState
    remaining_certification_satisfied: bool

    def __post_init__(self) -> None:
        if not self.path_id.strip() or not self.market.strip():
            raise ValueError("access path requires an id and market")
        if self.application_state not in {"not_required", "not_started", "applied", "satisfied"}:
            raise ValueError("application state is unknown and fails closed")
        if self.provider_preapproval_state not in {"not_required", "not_approved", "approved"}:
            raise ValueError("preapproval state is unknown and fails closed")
        if self.credentials_state not in {"not_required", "not_issued", "issued"}:
            raise ValueError("credentials state is unknown and fails closed")


def access_requirements_satisfied(path: LegitimateAccessPath) -> bool:
    """True when this path's own access stages are satisfied.

    Does not grant market naming, certification, eligibility, or routing.
    An undocumented claim that credentials are unnecessary fails closed.
    ``applied`` is not approval.
    """

    keyless = (
        path.official_keyless_anonymous_mode_documented
        and not path.application_required
        and not path.separate_provider_preapproval_required
        and not path.credentials_required
    )
    if keyless:
        return True
    if (
        not path.application_required
        and not path.separate_provider_preapproval_required
        and not path.credentials_required
    ):
        return False
    if path.application_required and path.application_state != "satisfied":
        return False
    if (
        path.separate_provider_preapproval_required
        and path.provider_preapproval_state != "approved"
    ):
        return False
    return not path.credentials_required or path.credentials_state == "issued"


def missing_credentials_block_path(path: LegitimateAccessPath) -> bool:
    """Credential absence blocks only paths that actually require credentials."""

    return path.credentials_required and path.credentials_state != "issued"


def missing_provider_preapproval_blocks_path(path: LegitimateAccessPath) -> bool:
    """Preapproval absence blocks only paths that actually require it."""

    return (
        path.separate_provider_preapproval_required
        and path.provider_preapproval_state != "approved"
    )


def may_name_market(path: LegitimateAccessPath) -> bool:
    """Naming still requires the remaining certification evidence."""

    return access_requirements_satisfied(path) and path.remaining_certification_satisfied


def shopify_anonymous_global_catalog_access_path() -> LegitimateAccessPath:
    """S-1 Anonymous catalog mode. Access stages are satisfied. Naming is not."""

    stage = anonymous_global_catalog_access_stage()
    return LegitimateAccessPath(
        path_id="s1-shopify-global-catalog-anonymous",
        market=stage.market,
        application_required=stage.application_required,
        separate_provider_preapproval_required=stage.separate_provider_preapproval_required,
        credentials_required=stage.credentials_required,
        official_keyless_anonymous_mode_documented=True,
        application_state="not_required",
        provider_preapproval_state="not_required",
        credentials_state="not_required",
        remaining_certification_satisfied=stage.production_certified,
    )


def shopee_ext01_product_data_access_path() -> LegitimateAccessPath:
    """EXT-01 Shopee request remains applied. Approval and credentials are absent."""

    return LegitimateAccessPath(
        path_id="ext-01-shopee-ph-product-data",
        market="PH",
        application_required=True,
        separate_provider_preapproval_required=True,
        credentials_required=True,
        official_keyless_anonymous_mode_documented=False,
        application_state="applied",
        provider_preapproval_state="not_approved",
        credentials_state="not_issued",
        remaining_certification_satisfied=False,
    )


def lazada_ext01_product_data_access_path() -> LegitimateAccessPath:
    """EXT-01 Lazada request remains applied. Approval and credentials are absent."""

    return LegitimateAccessPath(
        path_id="ext-01-lazada-ph-product-data",
        market="PH",
        application_required=True,
        separate_provider_preapproval_required=True,
        credentials_required=True,
        official_keyless_anonymous_mode_documented=False,
        application_state="applied",
        provider_preapproval_state="not_approved",
        credentials_state="not_issued",
        remaining_certification_satisfied=False,
    )


def known_market_access_paths() -> tuple[LegitimateAccessPath, ...]:
    return (
        shopify_anonymous_global_catalog_access_path(),
        shopee_ext01_product_data_access_path(),
        lazada_ext01_product_data_access_path(),
    )
