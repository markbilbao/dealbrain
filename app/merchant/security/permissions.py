"""Permission and membership enforcement for the Merchant Platform."""

from __future__ import annotations

from app.domain.entities.merchant import MerchantActor, MerchantPermission
from app.domain.exceptions import MerchantAuthorizationError, MerchantIsolationError


def require_permission(actor: MerchantActor, permission: MerchantPermission) -> MerchantActor:
    """Raise if the actor lacks ``permission``."""
    if not actor.has_permission(permission):
        raise MerchantAuthorizationError(
            f"Account {actor.account_id} lacks permission '{permission.value}'."
        )
    return actor


def require_internal_admin(actor: MerchantActor) -> MerchantActor:
    """Raise unless the actor is an internal admin."""
    if not actor.is_internal_admin:
        raise MerchantAuthorizationError("Internal admin authorization required.")
    return actor


def require_membership(
    actor: MerchantActor,
    organization_id: str,
    *,
    allow_internal_admin: bool = True,
) -> MerchantActor:
    """Ensure the actor belongs to ``organization_id`` (or is internal admin)."""
    if allow_internal_admin and actor.is_internal_admin:
        return actor
    if actor.organization_id != organization_id:
        raise MerchantIsolationError(
            organization_id,
            message=(
                f"Account {actor.account_id} is not a member of organization {organization_id}."
            ),
        )
    if actor.membership is None or not actor.membership.is_active:
        raise MerchantAuthorizationError(
            f"No active membership for account {actor.account_id} in {organization_id}."
        )
    return actor
