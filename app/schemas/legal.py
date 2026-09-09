"""Legal publication and privacy-readiness API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LegalPublicationStatusResponse(BaseModel):
    """Non-PII publication and privacy-readiness posture.

    Empty/false fields are the production truth until counsel-approved
    documents are published. This is not a published policy.
    """

    terms_published: bool
    privacy_published: bool
    terms_version_id: str | None = None
    privacy_version_id: str | None = None
    terms_acceptance_required: bool = False
    privacy_acceptance_required: bool = False
    cookie_notice_published: bool = False
    counsel_drafts_are_not_public: bool = True
    support_contact: str
    privacy_contact: str
    minimum_age_years: int | None = None
    age_policy_published: bool = False
    collects_date_of_birth: bool = False
    parental_consent_flow: bool = False
    country_notices_published: bool = False
    country_notice_count: int = 0
    enforced_at_registration: bool = False
    counsel_owned: bool = True
    tracking_mode: str = "essential_only"
    cmp_vendor: str | None = None
    analytics_provider: str | None = None
    essential_allowed: bool = True
    analytics_allowed: bool = False
    advertising_allowed: bool = False
    non_essential_tracking_allowed: bool = False
    banner_implemented: bool = False
    ext_22_status: str = "not_started"
    activation_owner: str = "sprint_39"


class AccountConsentAuditResponse(BaseModel):
    """Authenticated caller's own consent records. Empty when unpublished."""

    user_id: str
    terms_published: bool
    privacy_published: bool
    terms_version_id: str | None = None
    privacy_version_id: str | None = None
    records: list[dict[str, Any]] = Field(default_factory=list)
    policy_accepted_events: list[dict[str, Any]] = Field(default_factory=list)
    unpublished: bool
    notes: list[str] = Field(default_factory=list)
