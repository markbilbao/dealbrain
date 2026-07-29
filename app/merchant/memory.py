"""In-memory Merchant Platform repository — Sprint 21.

Implements all merchant repository ports in one process-scoped store.
Demo seed data only — prepare for production persistence in Sprint 22.
"""

from __future__ import annotations

from app.domain.entities.merchant import (
    MerchantAccount,
    MerchantAuditEvent,
    MerchantCampaign,
    MerchantInvitation,
    MerchantMarketplaceAccount,
    MerchantMatchReview,
    MerchantMembership,
    MerchantNotificationPreference,
    MerchantOfferSubmission,
    MerchantOrganization,
    MerchantProductSubmission,
    MerchantPromotion,
    MerchantUser,
    MerchantVerification,
)
from app.domain.interfaces.merchant_repository import (
    MerchantAccountRepository,
    MerchantAuditRepository,
    MerchantAuxiliaryRepository,
    MerchantCampaignRepository,
    MerchantMembershipRepository,
    MerchantOrganizationRepository,
    MerchantPromotionRepository,
    MerchantSubmissionRepository,
)
from app.merchant.fixtures import (
    DEMO_CATALOG,
    build_demo_accounts,
    build_demo_campaigns,
    build_demo_invitations,
    build_demo_marketplace_accounts,
    build_demo_memberships,
    build_demo_offer_submissions,
    build_demo_organizations,
    build_demo_product_submissions,
    build_demo_promotions,
    build_demo_users,
    build_demo_verifications,
)
from app.merchant.matching import MerchantProductMatcher


class InMemoryMerchantRepository(
    MerchantOrganizationRepository,
    MerchantAccountRepository,
    MerchantMembershipRepository,
    MerchantSubmissionRepository,
    MerchantPromotionRepository,
    MerchantCampaignRepository,
    MerchantAuditRepository,
    MerchantAuxiliaryRepository,
):
    """Process-local dict store for Merchant Platform aggregates."""

    def __init__(self, *, seed: bool = True) -> None:
        self._organizations: dict[str, MerchantOrganization] = {}
        self._org_order: list[str] = []
        self._accounts: dict[str, MerchantAccount] = {}
        self._account_order: list[str] = []
        self._users: dict[str, MerchantUser] = {}
        self._memberships: dict[str, MerchantMembership] = {}
        self._membership_order: list[str] = []
        self._invitations: dict[str, MerchantInvitation] = {}
        self._invitation_order: list[str] = []
        self._products: dict[str, MerchantProductSubmission] = {}
        self._product_order: list[str] = []
        self._offers: dict[str, MerchantOfferSubmission] = {}
        self._offer_order: list[str] = []
        self._match_reviews: dict[str, MerchantMatchReview] = {}
        self._match_review_order: list[str] = []
        self._promotions: dict[str, MerchantPromotion] = {}
        self._promotion_order: list[str] = []
        self._campaigns: dict[str, MerchantCampaign] = {}
        self._campaign_order: list[str] = []
        self._audit_events: dict[str, MerchantAuditEvent] = {}
        self._audit_order: list[str] = []
        self._verifications: dict[str, MerchantVerification] = {}
        self._marketplace_accounts: dict[str, MerchantMarketplaceAccount] = {}
        self._marketplace_order: list[str] = []
        self._preferences: dict[str, MerchantNotificationPreference] = {}
        self.matcher = MerchantProductMatcher(DEMO_CATALOG)
        if seed:
            self.seed_demo()

    def clear(self) -> None:
        self._organizations.clear()
        self._org_order.clear()
        self._accounts.clear()
        self._account_order.clear()
        self._users.clear()
        self._memberships.clear()
        self._membership_order.clear()
        self._invitations.clear()
        self._invitation_order.clear()
        self._products.clear()
        self._product_order.clear()
        self._offers.clear()
        self._offer_order.clear()
        self._match_reviews.clear()
        self._match_review_order.clear()
        self._promotions.clear()
        self._promotion_order.clear()
        self._campaigns.clear()
        self._campaign_order.clear()
        self._audit_events.clear()
        self._audit_order.clear()
        self._verifications.clear()
        self._marketplace_accounts.clear()
        self._marketplace_order.clear()
        self._preferences.clear()
        self.matcher = MerchantProductMatcher(DEMO_CATALOG)

    def seed_demo(self) -> None:
        for account in build_demo_accounts():
            self.save_account(account)
        for user in build_demo_users():
            self.save_user(user)
        for org in build_demo_organizations():
            self.save_organization(org)
        for membership in build_demo_memberships():
            self.save_membership(membership)
        for invitation in build_demo_invitations():
            self.save_invitation(invitation)
        for verification in build_demo_verifications():
            self.save_verification(verification)
        for mkt in build_demo_marketplace_accounts():
            self.save_marketplace_account(mkt)
        for product in build_demo_product_submissions():
            self.save_product_submission(product)
        for offer in build_demo_offer_submissions():
            self.save_offer_submission(offer)
        for promotion in build_demo_promotions():
            self.save_promotion(promotion)
        for campaign in build_demo_campaigns():
            self.save_campaign(campaign)

    # --- organizations ---
    def save_organization(self, org: MerchantOrganization) -> MerchantOrganization:
        if org.organization_id not in self._organizations:
            self._org_order.append(org.organization_id)
        self._organizations[org.organization_id] = org
        return org

    def get_organization(self, organization_id: str) -> MerchantOrganization | None:
        return self._organizations.get(organization_id)

    def list_organizations(
        self, *, status: str | None = None, limit: int = 100
    ) -> list[MerchantOrganization]:
        items = [self._organizations[i] for i in self._org_order if i in self._organizations]
        if status:
            items = [o for o in items if o.status.value == status]
        return items[:limit]

    # --- accounts / users ---
    def save_account(self, account: MerchantAccount) -> MerchantAccount:
        if account.account_id not in self._accounts:
            self._account_order.append(account.account_id)
        self._accounts[account.account_id] = account
        return account

    def get_account(self, account_id: str) -> MerchantAccount | None:
        return self._accounts.get(account_id)

    def get_account_by_email(self, email: str) -> MerchantAccount | None:
        needle = email.strip().lower()
        for account_id in self._account_order:
            account = self._accounts[account_id]
            if account.email.lower() == needle:
                return account
        return None

    def get_account_by_token(self, token: str) -> MerchantAccount | None:
        for account_id in self._account_order:
            account = self._accounts[account_id]
            if account.demo_token and account.demo_token == token:
                return account
        return None

    def list_accounts(self, *, limit: int = 100) -> list[MerchantAccount]:
        return [self._accounts[i] for i in self._account_order[:limit]]

    def save_user(self, user: MerchantUser) -> MerchantUser:
        self._users[user.user_id] = user
        return user

    def get_user(self, user_id: str) -> MerchantUser | None:
        return self._users.get(user_id)

    # --- memberships / invitations ---
    def save_membership(self, membership: MerchantMembership) -> MerchantMembership:
        if membership.membership_id not in self._memberships:
            self._membership_order.append(membership.membership_id)
        self._memberships[membership.membership_id] = membership
        return membership

    def get_membership(self, membership_id: str) -> MerchantMembership | None:
        return self._memberships.get(membership_id)

    def get_membership_for_account(
        self, organization_id: str, account_id: str
    ) -> MerchantMembership | None:
        for membership_id in self._membership_order:
            m = self._memberships[membership_id]
            if m.organization_id == organization_id and m.account_id == account_id:
                return m
        return None

    def list_memberships(
        self,
        *,
        organization_id: str | None = None,
        account_id: str | None = None,
        active_only: bool = True,
    ) -> list[MerchantMembership]:
        items = [self._memberships[i] for i in self._membership_order]
        if organization_id:
            items = [m for m in items if m.organization_id == organization_id]
        if account_id:
            items = [m for m in items if m.account_id == account_id]
        if active_only:
            items = [m for m in items if m.is_active]
        return items

    def delete_membership(self, membership_id: str) -> bool:
        if membership_id not in self._memberships:
            return False
        del self._memberships[membership_id]
        self._membership_order = [i for i in self._membership_order if i != membership_id]
        return True

    def save_invitation(self, invitation: MerchantInvitation) -> MerchantInvitation:
        if invitation.invitation_id not in self._invitations:
            self._invitation_order.append(invitation.invitation_id)
        self._invitations[invitation.invitation_id] = invitation
        return invitation

    def get_invitation(self, invitation_id: str) -> MerchantInvitation | None:
        return self._invitations.get(invitation_id)

    def list_invitations(
        self,
        *,
        organization_id: str | None = None,
        email: str | None = None,
        status: str | None = None,
    ) -> list[MerchantInvitation]:
        items = [self._invitations[i] for i in self._invitation_order]
        if organization_id:
            items = [i for i in items if i.organization_id == organization_id]
        if email:
            needle = email.strip().lower()
            items = [i for i in items if i.email.lower() == needle]
        if status:
            items = [i for i in items if i.status.value == status]
        return items

    # --- submissions ---
    def save_product_submission(
        self, submission: MerchantProductSubmission
    ) -> MerchantProductSubmission:
        if submission.submission_id not in self._products:
            self._product_order.append(submission.submission_id)
        self._products[submission.submission_id] = submission
        return submission

    def get_product_submission(self, submission_id: str) -> MerchantProductSubmission | None:
        return self._products.get(submission_id)

    def list_product_submissions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantProductSubmission]:
        items = [self._products[i] for i in reversed(self._product_order)]
        if organization_id:
            items = [p for p in items if p.organization_id == organization_id]
        if status:
            items = [p for p in items if p.status.value == status]
        return items[:limit]

    def save_offer_submission(self, offer: MerchantOfferSubmission) -> MerchantOfferSubmission:
        if offer.offer_id not in self._offers:
            self._offer_order.append(offer.offer_id)
        self._offers[offer.offer_id] = offer
        return offer

    def get_offer_submission(self, offer_id: str) -> MerchantOfferSubmission | None:
        return self._offers.get(offer_id)

    def list_offer_submissions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantOfferSubmission]:
        items = [self._offers[i] for i in reversed(self._offer_order)]
        if organization_id:
            items = [o for o in items if o.organization_id == organization_id]
        if status:
            items = [o for o in items if o.status.value == status]
        return items[:limit]

    def save_match_review(self, review: MerchantMatchReview) -> MerchantMatchReview:
        if review.review_id not in self._match_reviews:
            self._match_review_order.append(review.review_id)
        self._match_reviews[review.review_id] = review
        return review

    def list_match_reviews(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantMatchReview]:
        items = [self._match_reviews[i] for i in reversed(self._match_review_order)]
        if organization_id:
            items = [r for r in items if r.organization_id == organization_id]
        if status:
            items = [r for r in items if r.status == status]
        return items[:limit]

    # --- promotions ---
    def save_promotion(self, promotion: MerchantPromotion) -> MerchantPromotion:
        if promotion.promotion_id not in self._promotions:
            self._promotion_order.append(promotion.promotion_id)
        self._promotions[promotion.promotion_id] = promotion
        return promotion

    def get_promotion(self, promotion_id: str) -> MerchantPromotion | None:
        return self._promotions.get(promotion_id)

    def list_promotions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantPromotion]:
        items = [self._promotions[i] for i in reversed(self._promotion_order)]
        if organization_id:
            items = [p for p in items if p.organization_id == organization_id]
        if status:
            items = [p for p in items if p.status.value == status]
        return items[:limit]

    # --- campaigns ---
    def save_campaign(self, campaign: MerchantCampaign) -> MerchantCampaign:
        if campaign.campaign_id not in self._campaigns:
            self._campaign_order.append(campaign.campaign_id)
        self._campaigns[campaign.campaign_id] = campaign
        return campaign

    def get_campaign(self, campaign_id: str) -> MerchantCampaign | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantCampaign]:
        items = [self._campaigns[i] for i in reversed(self._campaign_order)]
        if organization_id:
            items = [c for c in items if c.organization_id == organization_id]
        if status:
            items = [c for c in items if c.status.value == status]
        return items[:limit]

    # --- audit ---
    def save_audit_event(self, event: MerchantAuditEvent) -> MerchantAuditEvent:
        if event.event_id not in self._audit_events:
            self._audit_order.append(event.event_id)
        self._audit_events[event.event_id] = event
        return event

    def list_audit_events(
        self, *, organization_id: str | None = None, limit: int = 100
    ) -> list[MerchantAuditEvent]:
        items = [self._audit_events[i] for i in reversed(self._audit_order)]
        if organization_id:
            items = [e for e in items if e.organization_id == organization_id]
        return items[:limit]

    # --- auxiliary ---
    def save_verification(self, verification: MerchantVerification) -> MerchantVerification:
        self._verifications[verification.organization_id] = verification
        return verification

    def get_verification(self, organization_id: str) -> MerchantVerification | None:
        return self._verifications.get(organization_id)

    def save_marketplace_account(
        self, account: MerchantMarketplaceAccount
    ) -> MerchantMarketplaceAccount:
        if account.marketplace_account_id not in self._marketplace_accounts:
            self._marketplace_order.append(account.marketplace_account_id)
        self._marketplace_accounts[account.marketplace_account_id] = account
        return account

    def list_marketplace_accounts(
        self, *, organization_id: str | None = None
    ) -> list[MerchantMarketplaceAccount]:
        items = [self._marketplace_accounts[i] for i in self._marketplace_order]
        if organization_id:
            items = [a for a in items if a.organization_id == organization_id]
        return items

    def save_notification_preference(
        self, preference: MerchantNotificationPreference
    ) -> MerchantNotificationPreference:
        key = f"{preference.account_id}:{preference.organization_id}"
        self._preferences[key] = preference
        return preference

    def get_notification_preference(
        self, account_id: str, organization_id: str
    ) -> MerchantNotificationPreference | None:
        return self._preferences.get(f"{account_id}:{organization_id}")
