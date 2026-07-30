"""SQLAlchemy Merchant Platform repository — Sprint 23."""

from __future__ import annotations

from dataclasses import dataclass

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
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import (
    MERCH_ACCOUNT_TOKENS,
    MERCH_ACCOUNTS,
    MERCH_AUDIT,
    MERCH_CAMPAIGNS,
    MERCH_INVITATIONS,
    MERCH_MARKETPLACE_ACCOUNTS,
    MERCH_MATCH_REVIEWS,
    MERCH_MEMBERSHIPS,
    MERCH_OFFERS,
    MERCH_ORGS,
    MERCH_PREFERENCES,
    MERCH_PRODUCTS,
    MERCH_PROMOTIONS,
    MERCH_USERS,
    MERCH_VERIFICATIONS,
    MERCHANT_STORES,
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


@dataclass(frozen=True, slots=True)
class _AccountTokenRef:
    account_id: str


class SqlAlchemyMerchantRepository(
    MerchantOrganizationRepository,
    MerchantAccountRepository,
    MerchantMembershipRepository,
    MerchantSubmissionRepository,
    MerchantPromotionRepository,
    MerchantCampaignRepository,
    MerchantAuditRepository,
    MerchantAuxiliaryRepository,
    SessionBound,
):
    """SQLAlchemy-backed merchant store mirroring InMemoryMerchantRepository."""

    def __init__(self, *, seed: bool = False, session_factory=None, session=None) -> None:
        super().__init__(session_factory=session_factory, session=session)
        self.matcher = MerchantProductMatcher(DEMO_CATALOG)
        if seed:
            self.seed_demo()

    def clear(self) -> None:
        with self._ops() as ops:
            ops.clear_stores(MERCHANT_STORES)
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

    def _sync_account_token(self, ops, account: MerchantAccount, previous: MerchantAccount | None) -> None:
        if previous is not None and previous.demo_token and previous.demo_token != account.demo_token:
            ops.delete(MERCH_ACCOUNT_TOKENS, previous.demo_token)
        if account.demo_token:
            ops.upsert(
                MERCH_ACCOUNT_TOKENS,
                account.demo_token,
                _AccountTokenRef(account_id=account.account_id),
                secondary_key=account.demo_token,
            )

    # --- organizations ---
    def save_organization(self, org: MerchantOrganization) -> MerchantOrganization:
        with self._ops() as ops:
            return ops.upsert(MERCH_ORGS, org.organization_id, org)

    def get_organization(self, organization_id: str) -> MerchantOrganization | None:
        with self._ops() as ops:
            return ops.get(MERCH_ORGS, organization_id, MerchantOrganization)

    def list_organizations(
        self, *, status: str | None = None, limit: int = 100
    ) -> list[MerchantOrganization]:
        predicate = (
            (lambda o: o.status.value == status) if status else None
        )
        with self._ops() as ops:
            items = ops.list(MERCH_ORGS, MerchantOrganization, predicate=predicate)
        return items[:limit]

    # --- accounts / users ---
    def save_account(self, account: MerchantAccount) -> MerchantAccount:
        email = account.email.strip().lower()
        with self._ops() as ops:
            previous = ops.get(MERCH_ACCOUNTS, account.account_id, MerchantAccount)
            saved = ops.upsert(
                MERCH_ACCOUNTS,
                account.account_id,
                account,
                secondary_key=email,
            )
            self._sync_account_token(ops, account, previous)
            return saved

    def get_account(self, account_id: str) -> MerchantAccount | None:
        with self._ops() as ops:
            return ops.get(MERCH_ACCOUNTS, account_id, MerchantAccount)

    def get_account_by_email(self, email: str) -> MerchantAccount | None:
        with self._ops() as ops:
            return ops.get_by_secondary(MERCH_ACCOUNTS, email.strip().lower(), MerchantAccount)

    def get_account_by_token(self, token: str) -> MerchantAccount | None:
        with self._ops() as ops:
            ref = ops.get(MERCH_ACCOUNT_TOKENS, token, _AccountTokenRef)
            if ref is None:
                ref = ops.get_by_secondary(MERCH_ACCOUNT_TOKENS, token, _AccountTokenRef)
            if ref is None:
                return None
            return ops.get(MERCH_ACCOUNTS, ref.account_id, MerchantAccount)

    def list_accounts(self, *, limit: int = 100) -> list[MerchantAccount]:
        with self._ops() as ops:
            items = ops.list(MERCH_ACCOUNTS, MerchantAccount)
        return items[:limit]

    def save_user(self, user: MerchantUser) -> MerchantUser:
        with self._ops() as ops:
            return ops.upsert(MERCH_USERS, user.user_id, user, owner_id=user.account_id)

    def get_user(self, user_id: str) -> MerchantUser | None:
        with self._ops() as ops:
            return ops.get(MERCH_USERS, user_id, MerchantUser)

    # --- memberships / invitations ---
    def save_membership(self, membership: MerchantMembership) -> MerchantMembership:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_MEMBERSHIPS,
                membership.membership_id,
                membership,
                owner_id=membership.organization_id,
            )

    def get_membership(self, membership_id: str) -> MerchantMembership | None:
        with self._ops() as ops:
            return ops.get(MERCH_MEMBERSHIPS, membership_id, MerchantMembership)

    def get_membership_for_account(
        self, organization_id: str, account_id: str
    ) -> MerchantMembership | None:
        with self._ops() as ops:
            memberships = ops.list(
                MERCH_MEMBERSHIPS,
                MerchantMembership,
                owner_id=organization_id,
            )
        for membership in memberships:
            if membership.account_id == account_id:
                return membership
        return None

    def list_memberships(
        self,
        *,
        organization_id: str | None = None,
        account_id: str | None = None,
        active_only: bool = True,
    ) -> list[MerchantMembership]:
        def _matches(membership: MerchantMembership) -> bool:
            if organization_id and membership.organization_id != organization_id:
                return False
            if account_id and membership.account_id != account_id:
                return False
            if active_only and not membership.is_active:
                return False
            return True

        with self._ops() as ops:
            if organization_id:
                return ops.list(
                    MERCH_MEMBERSHIPS,
                    MerchantMembership,
                    owner_id=organization_id,
                    predicate=_matches,
                )
            return ops.list(MERCH_MEMBERSHIPS, MerchantMembership, predicate=_matches)

    def delete_membership(self, membership_id: str) -> bool:
        with self._ops() as ops:
            return ops.delete(MERCH_MEMBERSHIPS, membership_id)

    def save_invitation(self, invitation: MerchantInvitation) -> MerchantInvitation:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_INVITATIONS,
                invitation.invitation_id,
                invitation,
                owner_id=invitation.organization_id,
            )

    def get_invitation(self, invitation_id: str) -> MerchantInvitation | None:
        with self._ops() as ops:
            return ops.get(MERCH_INVITATIONS, invitation_id, MerchantInvitation)

    def list_invitations(
        self,
        *,
        organization_id: str | None = None,
        email: str | None = None,
        status: str | None = None,
    ) -> list[MerchantInvitation]:
        needle = email.strip().lower() if email else None

        def _matches(invitation: MerchantInvitation) -> bool:
            if organization_id and invitation.organization_id != organization_id:
                return False
            if needle and invitation.email.lower() != needle:
                return False
            if status and invitation.status.value != status:
                return False
            return True

        with self._ops() as ops:
            if organization_id:
                return ops.list(
                    MERCH_INVITATIONS,
                    MerchantInvitation,
                    owner_id=organization_id,
                    predicate=_matches,
                )
            return ops.list(MERCH_INVITATIONS, MerchantInvitation, predicate=_matches)

    # --- submissions ---
    def save_product_submission(
        self, submission: MerchantProductSubmission
    ) -> MerchantProductSubmission:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_PRODUCTS,
                submission.submission_id,
                submission,
                owner_id=submission.organization_id,
            )

    def get_product_submission(self, submission_id: str) -> MerchantProductSubmission | None:
        with self._ops() as ops:
            return ops.get(MERCH_PRODUCTS, submission_id, MerchantProductSubmission)

    def list_product_submissions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantProductSubmission]:
        def _matches(submission: MerchantProductSubmission) -> bool:
            if organization_id and submission.organization_id != organization_id:
                return False
            if status and submission.status.value != status:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                MERCH_PRODUCTS,
                MerchantProductSubmission,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    def save_offer_submission(self, offer: MerchantOfferSubmission) -> MerchantOfferSubmission:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_OFFERS,
                offer.offer_id,
                offer,
                owner_id=offer.organization_id,
            )

    def get_offer_submission(self, offer_id: str) -> MerchantOfferSubmission | None:
        with self._ops() as ops:
            return ops.get(MERCH_OFFERS, offer_id, MerchantOfferSubmission)

    def list_offer_submissions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantOfferSubmission]:
        def _matches(offer: MerchantOfferSubmission) -> bool:
            if organization_id and offer.organization_id != organization_id:
                return False
            if status and offer.status.value != status:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                MERCH_OFFERS,
                MerchantOfferSubmission,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    def save_match_review(self, review: MerchantMatchReview) -> MerchantMatchReview:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_MATCH_REVIEWS,
                review.review_id,
                review,
                owner_id=review.organization_id,
            )

    def list_match_reviews(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantMatchReview]:
        def _matches(review: MerchantMatchReview) -> bool:
            if organization_id and review.organization_id != organization_id:
                return False
            if status and review.status != status:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                MERCH_MATCH_REVIEWS,
                MerchantMatchReview,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    # --- promotions ---
    def save_promotion(self, promotion: MerchantPromotion) -> MerchantPromotion:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_PROMOTIONS,
                promotion.promotion_id,
                promotion,
                owner_id=promotion.organization_id,
            )

    def get_promotion(self, promotion_id: str) -> MerchantPromotion | None:
        with self._ops() as ops:
            return ops.get(MERCH_PROMOTIONS, promotion_id, MerchantPromotion)

    def list_promotions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantPromotion]:
        def _matches(promotion: MerchantPromotion) -> bool:
            if organization_id and promotion.organization_id != organization_id:
                return False
            if status and promotion.status.value != status:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                MERCH_PROMOTIONS,
                MerchantPromotion,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    # --- campaigns ---
    def save_campaign(self, campaign: MerchantCampaign) -> MerchantCampaign:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_CAMPAIGNS,
                campaign.campaign_id,
                campaign,
                owner_id=campaign.organization_id,
            )

    def get_campaign(self, campaign_id: str) -> MerchantCampaign | None:
        with self._ops() as ops:
            return ops.get(MERCH_CAMPAIGNS, campaign_id, MerchantCampaign)

    def list_campaigns(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantCampaign]:
        def _matches(campaign: MerchantCampaign) -> bool:
            if organization_id and campaign.organization_id != organization_id:
                return False
            if status and campaign.status.value != status:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                MERCH_CAMPAIGNS,
                MerchantCampaign,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    # --- audit ---
    def save_audit_event(self, event: MerchantAuditEvent) -> MerchantAuditEvent:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_AUDIT,
                event.event_id,
                event,
                owner_id=event.organization_id,
            )

    def list_audit_events(
        self, *, organization_id: str | None = None, limit: int = 100
    ) -> list[MerchantAuditEvent]:
        predicate = (
            (lambda e: e.organization_id == organization_id) if organization_id else None
        )
        with self._ops() as ops:
            return ops.list(
                MERCH_AUDIT,
                MerchantAuditEvent,
                reverse=True,
                limit=limit,
                predicate=predicate,
            )

    # --- auxiliary ---
    def save_verification(self, verification: MerchantVerification) -> MerchantVerification:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_VERIFICATIONS,
                verification.organization_id,
                verification,
                owner_id=verification.organization_id,
            )

    def get_verification(self, organization_id: str) -> MerchantVerification | None:
        with self._ops() as ops:
            return ops.get(MERCH_VERIFICATIONS, organization_id, MerchantVerification)

    def save_marketplace_account(
        self, account: MerchantMarketplaceAccount
    ) -> MerchantMarketplaceAccount:
        with self._ops() as ops:
            return ops.upsert(
                MERCH_MARKETPLACE_ACCOUNTS,
                account.marketplace_account_id,
                account,
                owner_id=account.organization_id,
            )

    def list_marketplace_accounts(
        self, *, organization_id: str | None = None
    ) -> list[MerchantMarketplaceAccount]:
        predicate = (
            (lambda a: a.organization_id == organization_id) if organization_id else None
        )
        with self._ops() as ops:
            return ops.list(
                MERCH_MARKETPLACE_ACCOUNTS,
                MerchantMarketplaceAccount,
                predicate=predicate,
            )

    def save_notification_preference(
        self, preference: MerchantNotificationPreference
    ) -> MerchantNotificationPreference:
        key = f"{preference.account_id}:{preference.organization_id}"
        with self._ops() as ops:
            return ops.upsert(
                MERCH_PREFERENCES,
                key,
                preference,
                owner_id=preference.organization_id,
            )

    def get_notification_preference(
        self, account_id: str, organization_id: str
    ) -> MerchantNotificationPreference | None:
        key = f"{account_id}:{organization_id}"
        with self._ops() as ops:
            return ops.get(MERCH_PREFERENCES, key, MerchantNotificationPreference)
