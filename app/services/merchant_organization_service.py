"""Merchant organization management — Sprint 21."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.merchant import (
    MerchantActor,
    MerchantAuditAction,
    MerchantMembership,
    MerchantOrganization,
    MerchantOrgStatus,
    MerchantPermission,
    MerchantProfile,
    MerchantRole,
    MerchantVerificationStatus,
)
from app.domain.exceptions import (
    MerchantOrganizationNotFoundError,
    MerchantValidationError,
)
from app.domain.interfaces.merchant_repository import (
    MerchantAuditRepository,
    MerchantMembershipRepository,
    MerchantOrganizationRepository,
)
from app.merchant.security.permissions import require_membership, require_permission
from app.merchant.security.redaction import MerchantAuditHook, redact_secrets
from app.merchant.security.validation import (
    MAX_DESCRIPTION_LENGTH,
    validate_email,
    validate_safe_url,
    validate_text_length,
)


class MerchantOrganizationService:
    """Create, update, activate/deactivate, and archive merchant organizations."""

    def __init__(
        self,
        organizations: MerchantOrganizationRepository,
        memberships: MerchantMembershipRepository,
        audit: MerchantAuditRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._audit_hook = MerchantAuditHook(clock=self._clock, id_factory=self._id_factory)

    def list_organizations(
        self,
        actor: MerchantActor,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantOrganization]:
        orgs = self._organizations.list_organizations(status=status, limit=limit)
        if actor.is_internal_admin:
            return orgs
        # Non-admins only see orgs they belong to.
        member_ids = {
            m.organization_id
            for m in self._memberships.list_memberships(
                account_id=actor.account_id, active_only=True
            )
        }
        return [o for o in orgs if o.organization_id in member_ids]

    def get_organization(self, actor: MerchantActor, organization_id: str) -> MerchantOrganization:
        org = self._require_org(organization_id)
        require_membership(actor, organization_id)
        return org

    def create_organization(
        self,
        actor: MerchantActor,
        *,
        business_name: str,
        legal_name: str,
        display_name: str,
        country: str,
        business_category: str,
        website: str | None = None,
        support_email: str | None = None,
        marketplace_presence: list[str] | None = None,
        business_description: str = "",
        logo_reference: str | None = None,
        contact_references: list[str] | None = None,
        affiliate_merchant_id: str | None = None,
        organization_id: str | None = None,
        accept_terms: bool = False,
    ) -> MerchantOrganization:
        if not accept_terms:
            raise MerchantValidationError("Terms must be accepted to create an organization.")
        stamp = self._clock()
        profile = self._build_profile(
            business_name=business_name,
            legal_name=legal_name,
            display_name=display_name,
            country=country,
            business_category=business_category,
            website=website,
            support_email=support_email,
            marketplace_presence=marketplace_presence,
            business_description=business_description,
            logo_reference=logo_reference,
            contact_references=contact_references,
            terms_accepted_at=stamp,
        )
        org_id = organization_id or f"org-{self._id_factory()}"
        org = MerchantOrganization(
            organization_id=org_id,
            profile=profile,
            status=MerchantOrgStatus.PENDING,
            owner_account_id=actor.account_id,
            created_at=stamp,
            updated_at=stamp,
            affiliate_merchant_id=affiliate_merchant_id,
        )
        self._organizations.save_organization(org)
        membership = MerchantMembership(
            membership_id=f"mem-{self._id_factory()}",
            organization_id=org_id,
            account_id=actor.account_id,
            role=MerchantRole.OWNER,
            created_at=stamp,
            updated_at=stamp,
        )
        self._memberships.save_membership(membership)
        self._record(
            actor,
            MerchantAuditAction.ORGANIZATION_CREATED,
            "organization",
            org_id,
            organization_id=org_id,
            metadata={"display_name": display_name},
        )
        return org

    def update_profile(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        business_name: str | None = None,
        legal_name: str | None = None,
        display_name: str | None = None,
        country: str | None = None,
        business_category: str | None = None,
        website: str | None = None,
        support_email: str | None = None,
        marketplace_presence: list[str] | None = None,
        business_description: str | None = None,
        logo_reference: str | None = None,
        contact_references: list[str] | None = None,
    ) -> MerchantOrganization:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.ORGANIZATION_MANAGE)
        org = self._require_org(organization_id)
        if org.status == MerchantOrgStatus.ARCHIVED:
            raise MerchantValidationError("Cannot update an archived organization.")
        current = org.profile
        profile = self._build_profile(
            business_name=business_name if business_name is not None else current.business_name,
            legal_name=legal_name if legal_name is not None else current.legal_name,
            display_name=display_name if display_name is not None else current.display_name,
            country=country if country is not None else current.country,
            business_category=(
                business_category if business_category is not None else current.business_category
            ),
            website=website if website is not None else current.website,
            support_email=support_email if support_email is not None else current.support_email,
            marketplace_presence=(
                marketplace_presence
                if marketplace_presence is not None
                else list(current.marketplace_presence)
            ),
            business_description=(
                business_description
                if business_description is not None
                else current.business_description
            ),
            logo_reference=(
                logo_reference if logo_reference is not None else current.logo_reference
            ),
            contact_references=(
                contact_references
                if contact_references is not None
                else list(current.contact_references)
            ),
            verification_status=current.verification_status,
            terms_accepted_at=current.terms_accepted_at,
        )
        updated = replace(org, profile=profile, updated_at=self._clock())
        self._organizations.save_organization(updated)
        self._record(
            actor,
            MerchantAuditAction.PROFILE_UPDATED,
            "organization",
            organization_id,
            organization_id=organization_id,
        )
        return updated

    def activate(self, actor: MerchantActor, organization_id: str) -> MerchantOrganization:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.ORGANIZATION_MANAGE)
        return self._set_status(
            actor,
            organization_id,
            MerchantOrgStatus.ACTIVE,
            MerchantAuditAction.ORGANIZATION_ACTIVATED,
        )

    def deactivate(self, actor: MerchantActor, organization_id: str) -> MerchantOrganization:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.ORGANIZATION_MANAGE)
        return self._set_status(
            actor,
            organization_id,
            MerchantOrgStatus.INACTIVE,
            MerchantAuditAction.ORGANIZATION_DEACTIVATED,
        )

    def archive(self, actor: MerchantActor, organization_id: str) -> MerchantOrganization:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.ORGANIZATION_MANAGE)
        org = self._require_org(organization_id)
        stamp = self._clock()
        updated = replace(
            org, status=MerchantOrgStatus.ARCHIVED, archived_at=stamp, updated_at=stamp
        )
        self._organizations.save_organization(updated)
        self._record(
            actor,
            MerchantAuditAction.ORGANIZATION_ARCHIVED,
            "organization",
            organization_id,
            organization_id=organization_id,
        )
        return updated

    def assign_owner(
        self, actor: MerchantActor, organization_id: str, new_owner_account_id: str
    ) -> MerchantOrganization:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.ORGANIZATION_MANAGE)
        org = self._require_org(organization_id)
        membership = self._memberships.get_membership_for_account(
            organization_id, new_owner_account_id
        )
        if membership is None or not membership.is_active:
            raise MerchantValidationError("New owner must be an active organization member.")
        stamp = self._clock()
        # Promote new owner; demote previous owner to admin if still a member.
        self._memberships.save_membership(
            replace(membership, role=MerchantRole.OWNER, updated_at=stamp)
        )
        previous = self._memberships.get_membership_for_account(
            organization_id, org.owner_account_id
        )
        if previous and previous.account_id != new_owner_account_id:
            self._memberships.save_membership(
                replace(previous, role=MerchantRole.ADMIN, updated_at=stamp)
            )
        updated = replace(org, owner_account_id=new_owner_account_id, updated_at=stamp)
        self._organizations.save_organization(updated)
        self._record(
            actor,
            MerchantAuditAction.ROLE_CHANGED,
            "organization",
            organization_id,
            organization_id=organization_id,
            metadata={"new_owner_account_id": new_owner_account_id},
        )
        return updated

    def _set_status(
        self,
        actor: MerchantActor,
        organization_id: str,
        status: MerchantOrgStatus,
        action: MerchantAuditAction,
    ) -> MerchantOrganization:
        org = self._require_org(organization_id)
        if org.status == MerchantOrgStatus.ARCHIVED:
            raise MerchantValidationError("Archived organizations cannot change status.")
        updated = replace(org, status=status, updated_at=self._clock())
        self._organizations.save_organization(updated)
        self._record(
            actor, action, "organization", organization_id, organization_id=organization_id
        )
        return updated

    def _require_org(self, organization_id: str) -> MerchantOrganization:
        org = self._organizations.get_organization(organization_id)
        if org is None:
            raise MerchantOrganizationNotFoundError(organization_id)
        return org

    def _build_profile(
        self,
        *,
        business_name: str,
        legal_name: str,
        display_name: str,
        country: str,
        business_category: str,
        website: str | None,
        support_email: str | None,
        marketplace_presence: list[str] | None,
        business_description: str,
        logo_reference: str | None,
        contact_references: list[str] | None,
        verification_status: MerchantVerificationStatus = MerchantVerificationStatus.UNVERIFIED,
        terms_accepted_at: datetime | None = None,
    ) -> MerchantProfile:
        return MerchantProfile(
            business_name=validate_text_length(business_name, field="business_name", required=True),
            legal_name=validate_text_length(legal_name, field="legal_name", required=True),
            display_name=validate_text_length(display_name, field="display_name", required=True),
            country=validate_text_length(
                country, field="country", max_length=8, required=True
            ).upper(),
            business_category=validate_text_length(
                business_category, field="business_category", required=True
            ),
            website=validate_safe_url(website),
            support_email=validate_email(support_email) if support_email else None,
            marketplace_presence=tuple(marketplace_presence or ()),
            business_description=validate_text_length(
                business_description,
                field="business_description",
                max_length=MAX_DESCRIPTION_LENGTH,
            ),
            logo_reference=validate_safe_url(logo_reference),
            contact_references=tuple(contact_references or ()),
            verification_status=verification_status,
            terms_accepted_at=terms_accepted_at,
        )

    def _record(
        self,
        actor: MerchantActor,
        action: MerchantAuditAction,
        target_type: str,
        target_id: str,
        *,
        organization_id: str | None,
        metadata: dict | None = None,
    ) -> None:
        event = self._audit_hook.record(
            actor_account_id=actor.account_id,
            organization_id=organization_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=redact_secrets(metadata or {}),
        )
        self._audit.save_audit_event(event)
