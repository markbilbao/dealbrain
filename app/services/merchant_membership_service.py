"""Merchant membership and invitation management — Sprint 21."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.entities.merchant import (
    InvitationStatus,
    MerchantActor,
    MerchantAuditAction,
    MerchantInvitation,
    MerchantMembership,
    MerchantPermission,
    MerchantRole,
)
from app.domain.exceptions import (
    MerchantInvitationNotFoundError,
    MerchantMembershipNotFoundError,
    MerchantValidationError,
)
from app.domain.interfaces.merchant_repository import (
    MerchantAccountRepository,
    MerchantAuditRepository,
    MerchantMembershipRepository,
)
from app.merchant.security.permissions import require_membership, require_permission
from app.merchant.security.redaction import MerchantAuditHook, redact_secrets
from app.merchant.security.validation import validate_email


class MerchantMembershipService:
    """Invite users, accept/reject invitations, manage roles and memberships."""

    def __init__(
        self,
        memberships: MerchantMembershipRepository,
        accounts: MerchantAccountRepository,
        audit: MerchantAuditRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._memberships = memberships
        self._accounts = accounts
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._audit_hook = MerchantAuditHook(clock=self._clock, id_factory=self._id_factory)

    def list_members(self, actor: MerchantActor, organization_id: str) -> list[MerchantMembership]:
        require_membership(actor, organization_id)
        return self._memberships.list_memberships(
            organization_id=organization_id, active_only=False
        )

    def invite(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        email: str,
        role: str,
    ) -> MerchantInvitation:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.USER_MANAGE)
        cleaned_email = validate_email(email)
        merchant_role = self._parse_role(role)
        if merchant_role == MerchantRole.INTERNAL_ADMIN:
            raise MerchantValidationError("Cannot invite users as INTERNAL_ADMIN.")
        if merchant_role == MerchantRole.OWNER and actor.role != MerchantRole.OWNER:
            raise MerchantValidationError("Only an OWNER may invite another OWNER.")
        existing = self._memberships.list_invitations(
            organization_id=organization_id, email=cleaned_email, status="pending"
        )
        if existing:
            raise MerchantValidationError("A pending invitation already exists for this email.")
        stamp = self._clock()
        invitation = MerchantInvitation(
            invitation_id=f"inv-{self._id_factory()}",
            organization_id=organization_id,
            email=cleaned_email,
            role=merchant_role,
            invited_by_account_id=actor.account_id,
            status=InvitationStatus.PENDING,
            created_at=stamp,
            updated_at=stamp,
            expires_at=stamp + timedelta(days=14),
        )
        self._memberships.save_invitation(invitation)
        self._record(
            actor,
            MerchantAuditAction.USER_INVITED,
            "invitation",
            invitation.invitation_id,
            organization_id=organization_id,
            metadata={"email": cleaned_email, "role": merchant_role.value},
        )
        return invitation

    def accept_invitation(self, actor: MerchantActor, invitation_id: str) -> MerchantMembership:
        invitation = self._require_invitation(invitation_id)
        if invitation.status != InvitationStatus.PENDING:
            raise MerchantValidationError("Invitation is not pending.")
        if invitation.expires_at and self._clock() > invitation.expires_at:
            expired = replace(invitation, status=InvitationStatus.EXPIRED, updated_at=self._clock())
            self._memberships.save_invitation(expired)
            raise MerchantValidationError("Invitation has expired.")
        if actor.account.email.lower() != invitation.email.lower():
            raise MerchantValidationError("Invitation email does not match authenticated account.")
        existing = self._memberships.get_membership_for_account(
            invitation.organization_id, actor.account_id
        )
        stamp = self._clock()
        if existing and existing.is_active:
            raise MerchantValidationError("Account is already a member of this organization.")
        membership = MerchantMembership(
            membership_id=existing.membership_id if existing else f"mem-{self._id_factory()}",
            organization_id=invitation.organization_id,
            account_id=actor.account_id,
            role=invitation.role,
            created_at=existing.created_at if existing else stamp,
            updated_at=stamp,
            is_active=True,
        )
        self._memberships.save_membership(membership)
        self._memberships.save_invitation(
            replace(invitation, status=InvitationStatus.ACCEPTED, updated_at=stamp)
        )
        self._record(
            actor,
            MerchantAuditAction.INVITATION_ACCEPTED,
            "invitation",
            invitation_id,
            organization_id=invitation.organization_id,
        )
        self._record(
            actor,
            MerchantAuditAction.MEMBERSHIP_ADDED,
            "membership",
            membership.membership_id,
            organization_id=invitation.organization_id,
        )
        return membership

    def reject_invitation(self, actor: MerchantActor, invitation_id: str) -> MerchantInvitation:
        invitation = self._require_invitation(invitation_id)
        if invitation.status != InvitationStatus.PENDING:
            raise MerchantValidationError("Invitation is not pending.")
        if actor.account.email.lower() != invitation.email.lower() and not actor.is_internal_admin:
            raise MerchantValidationError("Invitation email does not match authenticated account.")
        stamp = self._clock()
        updated = replace(invitation, status=InvitationStatus.REJECTED, updated_at=stamp)
        self._memberships.save_invitation(updated)
        self._record(
            actor,
            MerchantAuditAction.INVITATION_REJECTED,
            "invitation",
            invitation_id,
            organization_id=invitation.organization_id,
        )
        return updated

    def change_role(
        self,
        actor: MerchantActor,
        organization_id: str,
        membership_id: str,
        *,
        role: str,
    ) -> MerchantMembership:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.USER_MANAGE)
        membership = self._require_membership(membership_id)
        if membership.organization_id != organization_id:
            raise MerchantValidationError("Membership does not belong to this organization.")
        new_role = self._parse_role(role)
        if new_role == MerchantRole.INTERNAL_ADMIN:
            raise MerchantValidationError("Cannot assign INTERNAL_ADMIN via membership.")
        # Prevent privilege escalation: non-owners cannot grant OWNER/ADMIN.
        if (
            actor.role != MerchantRole.OWNER
            and new_role in (MerchantRole.OWNER, MerchantRole.ADMIN)
            and (actor.role != MerchantRole.ADMIN or new_role == MerchantRole.OWNER)
        ):
            raise MerchantValidationError("Insufficient privilege to assign this role.")
        if membership.role == MerchantRole.OWNER and new_role != MerchantRole.OWNER:
            raise MerchantValidationError(
                "Cannot demote the organization owner via role change — use assign_owner."
            )
        updated = replace(membership, role=new_role, updated_at=self._clock())
        self._memberships.save_membership(updated)
        self._record(
            actor,
            MerchantAuditAction.ROLE_CHANGED,
            "membership",
            membership_id,
            organization_id=organization_id,
            metadata={"role": new_role.value},
        )
        return updated

    def remove_member(self, actor: MerchantActor, organization_id: str, membership_id: str) -> bool:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.USER_MANAGE)
        membership = self._require_membership(membership_id)
        if membership.organization_id != organization_id:
            raise MerchantValidationError("Membership does not belong to this organization.")
        if membership.role == MerchantRole.OWNER:
            raise MerchantValidationError("Cannot remove the organization owner.")
        if membership.account_id == actor.account_id:
            raise MerchantValidationError("Cannot remove your own membership.")
        stamp = self._clock()
        self._memberships.save_membership(replace(membership, is_active=False, updated_at=stamp))
        self._record(
            actor,
            MerchantAuditAction.MEMBERSHIP_REMOVED,
            "membership",
            membership_id,
            organization_id=organization_id,
        )
        return True

    def _parse_role(self, role: str) -> MerchantRole:
        try:
            return MerchantRole(str(role).strip().lower())
        except ValueError as exc:
            raise MerchantValidationError(f"Invalid merchant role: {role}") from exc

    def _require_invitation(self, invitation_id: str) -> MerchantInvitation:
        invitation = self._memberships.get_invitation(invitation_id)
        if invitation is None:
            raise MerchantInvitationNotFoundError(invitation_id)
        return invitation

    def _require_membership(self, membership_id: str) -> MerchantMembership:
        membership = self._memberships.get_membership(membership_id)
        if membership is None:
            raise MerchantMembershipNotFoundError(membership_id)
        return membership

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
