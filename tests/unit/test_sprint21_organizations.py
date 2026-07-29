"""Sprint 21 Merchant Platform — organizations, memberships, roles, isolation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.merchant import MerchantPermission, MerchantRole
from app.domain.exceptions import (
    MerchantAuthorizationError,
    MerchantIsolationError,
    MerchantValidationError,
)
from app.merchant.memory import InMemoryMerchantRepository
from app.services.merchant_auth_service import MerchantAuthService
from app.services.merchant_membership_service import MerchantMembershipService
from app.services.merchant_organization_service import MerchantOrganizationService

FIXED_NOW = datetime(2026, 7, 29, 15, 0, tzinfo=UTC)


def _ids():
    n = {"i": 0}

    def factory() -> str:
        n["i"] += 1
        return f"test-{n['i']:04d}"

    return factory


def _stack(*, seed: bool = True):
    repo = InMemoryMerchantRepository(seed=seed)
    clock = lambda: FIXED_NOW  # noqa: E731
    ids = _ids()
    auth = MerchantAuthService(repo, repo)
    orgs = MerchantOrganizationService(repo, repo, repo, clock=clock, id_factory=ids)
    members = MerchantMembershipService(repo, repo, repo, clock=clock, id_factory=ids)
    return repo, auth, orgs, members


def test_merchant_creation_and_profile_update() -> None:
    _, auth, orgs, _ = _stack(seed=True)
    actor = auth.resolve_actor("demo-token-techhaven-owner")
    created = orgs.create_organization(
        actor,
        business_name="NewCo LLC",
        legal_name="NewCo Limited",
        display_name="NewCo",
        country="US",
        business_category="electronics",
        accept_terms=True,
        website="https://newco.demo",
        support_email="hello@newco.demo",
    )
    assert created.status.value == "pending"
    assert created.profile.terms_accepted_at is not None

    owner = auth.resolve_actor(
        "demo-token-techhaven-owner", organization_id=created.organization_id
    )
    assert owner.membership is not None
    updated = orgs.update_profile(owner, created.organization_id, display_name="NewCo Retail")
    assert updated.profile.display_name == "NewCo Retail"


def test_merchant_archive_behavior() -> None:
    _, auth, orgs, _ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    archived = orgs.archive(actor, "org-techhaven")
    assert archived.status.value == "archived"
    assert archived.archived_at is not None
    with pytest.raises(MerchantValidationError):
        orgs.update_profile(actor, "org-techhaven", display_name="Nope")


def test_invitations_accept_and_role_assignment() -> None:
    repo, auth, _, members = _stack()
    owner = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    invitation = members.invite(
        owner, "org-techhaven", email="new.analyst@techhaven.demo", role="analyst"
    )
    assert invitation.status.value == "pending"

    from app.domain.entities.merchant import MerchantAccount

    invitee = MerchantAccount(
        account_id="acct-new-analyst",
        email="new.analyst@techhaven.demo",
        display_name="New Analyst",
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
        demo_token="demo-token-new-analyst",
    )
    repo.save_account(invitee)
    invitee_actor = auth.resolve_actor("demo-token-new-analyst")
    membership = members.accept_invitation(invitee_actor, invitation.invitation_id)
    assert membership.role == MerchantRole.ANALYST
    assert membership.is_active

    changed = members.change_role(owner, "org-techhaven", membership.membership_id, role="viewer")
    assert changed.role == MerchantRole.VIEWER


def test_permission_enforcement_and_privilege_escalation() -> None:
    _, auth, orgs, members = _stack()
    editor = auth.resolve_actor("demo-token-techhaven-editor", organization_id="org-techhaven")
    assert not editor.has_permission(MerchantPermission.USER_MANAGE)
    with pytest.raises(MerchantAuthorizationError):
        members.invite(editor, "org-techhaven", email="x@techhaven.demo", role="admin")
    with pytest.raises(MerchantAuthorizationError):
        orgs.update_profile(editor, "org-techhaven", display_name="Hacked")

    # Editor cannot grant OWNER
    owner = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    with pytest.raises(MerchantValidationError):
        members.invite(owner, "org-techhaven", email="evil@x.demo", role="internal_admin")


def test_cross_merchant_isolation() -> None:
    _, auth, orgs, _ = _stack()
    th = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    with pytest.raises(MerchantIsolationError):
        orgs.get_organization(th, "org-gadgetgrove")
    gg = auth.resolve_actor("demo-token-gadgetgrove-owner", organization_id="org-gadgetgrove")
    listed = orgs.list_organizations(gg)
    assert all(o.organization_id == "org-gadgetgrove" for o in listed)
