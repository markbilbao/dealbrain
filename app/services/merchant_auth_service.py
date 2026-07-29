"""Merchant authentication / actor resolution — Sprint 21.

Demo tokens only. No OAuth, MFA, or production identity providers.
"""

from __future__ import annotations

from app.domain.entities.merchant import MerchantActor
from app.domain.exceptions import MerchantAuthorizationError, MerchantValidationError
from app.domain.interfaces.merchant_repository import (
    MerchantAccountRepository,
    MerchantMembershipRepository,
)
from app.merchant.security.validation import validate_identifier


class MerchantAuthService:
    """Resolve a MerchantActor from a demo bearer token and optional org context."""

    def __init__(
        self,
        accounts: MerchantAccountRepository,
        memberships: MerchantMembershipRepository,
    ) -> None:
        self._accounts = accounts
        self._memberships = memberships

    def resolve_actor(
        self,
        token: str | None,
        *,
        organization_id: str | None = None,
    ) -> MerchantActor:
        if not token or not str(token).strip():
            raise MerchantAuthorizationError("Authentication required.")
        cleaned = str(token).strip()
        account = self._accounts.get_account_by_token(cleaned)
        if account is None:
            # Also allow account_id as a convenience for deterministic demo tests.
            account = self._accounts.get_account(cleaned)
        if account is None or not account.is_active:
            raise MerchantAuthorizationError("Invalid or inactive merchant credentials.")

        membership = None
        org_id = organization_id
        if org_id:
            org_id = validate_identifier(org_id, field="organization_id")
            membership = self._memberships.get_membership_for_account(org_id, account.account_id)
            if membership is None and not account.is_internal_admin:
                raise MerchantAuthorizationError(
                    f"Account is not a member of organization {org_id}."
                )
        elif not account.is_internal_admin:
            # Default to the caller's first active membership when org not specified.
            memberships = self._memberships.list_memberships(
                account_id=account.account_id, active_only=True
            )
            if memberships:
                membership = memberships[0]
                org_id = membership.organization_id

        return MerchantActor(account=account, membership=membership, organization_id=org_id)

    def require_token(self, authorization: str | None) -> str:
        """Extract bearer token from Authorization header value."""
        if not authorization:
            raise MerchantAuthorizationError("Authorization header required.")
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
            if token:
                return token
        # Allow raw demo token without Bearer prefix for demo UI simplicity.
        if authorization.strip():
            return authorization.strip()
        raise MerchantValidationError("Malformed Authorization header.")
