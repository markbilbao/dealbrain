"""Merchant Platform persistence ports — Sprint 21."""

from __future__ import annotations

from abc import ABC, abstractmethod

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


class MerchantOrganizationRepository(ABC):
    """Persistence for merchant organizations and profiles."""

    @abstractmethod
    def save_organization(self, org: MerchantOrganization) -> MerchantOrganization:
        """Create or replace an organization."""

    @abstractmethod
    def get_organization(self, organization_id: str) -> MerchantOrganization | None:
        """Return an organization by id, or None."""

    @abstractmethod
    def list_organizations(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantOrganization]:
        """Return organizations in insertion order, optionally filtered."""


class MerchantAccountRepository(ABC):
    """Persistence for merchant accounts and users."""

    @abstractmethod
    def save_account(self, account: MerchantAccount) -> MerchantAccount:
        """Create or replace an account."""

    @abstractmethod
    def get_account(self, account_id: str) -> MerchantAccount | None:
        """Return an account by id, or None."""

    @abstractmethod
    def get_account_by_email(self, email: str) -> MerchantAccount | None:
        """Return an account by email, or None."""

    @abstractmethod
    def get_account_by_token(self, token: str) -> MerchantAccount | None:
        """Return an account by demo token, or None."""

    @abstractmethod
    def list_accounts(self, *, limit: int = 100) -> list[MerchantAccount]:
        """Return accounts in insertion order."""

    @abstractmethod
    def save_user(self, user: MerchantUser) -> MerchantUser:
        """Create or replace a merchant user record."""

    @abstractmethod
    def get_user(self, user_id: str) -> MerchantUser | None:
        """Return a user by id, or None."""


class MerchantMembershipRepository(ABC):
    """Persistence for memberships and invitations."""

    @abstractmethod
    def save_membership(self, membership: MerchantMembership) -> MerchantMembership:
        """Create or replace a membership."""

    @abstractmethod
    def get_membership(self, membership_id: str) -> MerchantMembership | None:
        """Return a membership by id, or None."""

    @abstractmethod
    def get_membership_for_account(
        self, organization_id: str, account_id: str
    ) -> MerchantMembership | None:
        """Return the membership for an account in an organization, or None."""

    @abstractmethod
    def list_memberships(
        self,
        *,
        organization_id: str | None = None,
        account_id: str | None = None,
        active_only: bool = True,
    ) -> list[MerchantMembership]:
        """Return memberships, optionally filtered."""

    @abstractmethod
    def delete_membership(self, membership_id: str) -> bool:
        """Delete a membership. Returns False if missing."""

    @abstractmethod
    def save_invitation(self, invitation: MerchantInvitation) -> MerchantInvitation:
        """Create or replace an invitation."""

    @abstractmethod
    def get_invitation(self, invitation_id: str) -> MerchantInvitation | None:
        """Return an invitation by id, or None."""

    @abstractmethod
    def list_invitations(
        self,
        *,
        organization_id: str | None = None,
        email: str | None = None,
        status: str | None = None,
    ) -> list[MerchantInvitation]:
        """Return invitations, optionally filtered."""


class MerchantSubmissionRepository(ABC):
    """Persistence for product and offer submissions."""

    @abstractmethod
    def save_product_submission(
        self, submission: MerchantProductSubmission
    ) -> MerchantProductSubmission:
        """Create or replace a product submission."""

    @abstractmethod
    def get_product_submission(self, submission_id: str) -> MerchantProductSubmission | None:
        """Return a product submission by id, or None."""

    @abstractmethod
    def list_product_submissions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantProductSubmission]:
        """Return product submissions newest-first, optionally filtered."""

    @abstractmethod
    def save_offer_submission(self, offer: MerchantOfferSubmission) -> MerchantOfferSubmission:
        """Create or replace an offer submission."""

    @abstractmethod
    def get_offer_submission(self, offer_id: str) -> MerchantOfferSubmission | None:
        """Return an offer by id, or None."""

    @abstractmethod
    def list_offer_submissions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantOfferSubmission]:
        """Return offer submissions newest-first, optionally filtered."""

    @abstractmethod
    def save_match_review(self, review: MerchantMatchReview) -> MerchantMatchReview:
        """Create or replace a match review record."""

    @abstractmethod
    def list_match_reviews(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantMatchReview]:
        """Return match reviews newest-first."""


class MerchantPromotionRepository(ABC):
    """Persistence for merchant promotions."""

    @abstractmethod
    def save_promotion(self, promotion: MerchantPromotion) -> MerchantPromotion:
        """Create or replace a promotion."""

    @abstractmethod
    def get_promotion(self, promotion_id: str) -> MerchantPromotion | None:
        """Return a promotion by id, or None."""

    @abstractmethod
    def list_promotions(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantPromotion]:
        """Return promotions newest-first, optionally filtered."""


class MerchantCampaignRepository(ABC):
    """Persistence for sponsored campaign drafts."""

    @abstractmethod
    def save_campaign(self, campaign: MerchantCampaign) -> MerchantCampaign:
        """Create or replace a campaign."""

    @abstractmethod
    def get_campaign(self, campaign_id: str) -> MerchantCampaign | None:
        """Return a campaign by id, or None."""

    @abstractmethod
    def list_campaigns(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantCampaign]:
        """Return campaigns newest-first, optionally filtered."""


class MerchantAuditRepository(ABC):
    """Persistence for merchant audit events."""

    @abstractmethod
    def save_audit_event(self, event: MerchantAuditEvent) -> MerchantAuditEvent:
        """Append an audit event."""

    @abstractmethod
    def list_audit_events(
        self,
        *,
        organization_id: str | None = None,
        limit: int = 100,
    ) -> list[MerchantAuditEvent]:
        """Return audit events newest-first."""


class MerchantAuxiliaryRepository(ABC):
    """Persistence for verification, marketplace accounts, preferences."""

    @abstractmethod
    def save_verification(self, verification: MerchantVerification) -> MerchantVerification:
        """Create or replace a verification record."""

    @abstractmethod
    def get_verification(self, organization_id: str) -> MerchantVerification | None:
        """Return the latest verification for an organization, or None."""

    @abstractmethod
    def save_marketplace_account(
        self, account: MerchantMarketplaceAccount
    ) -> MerchantMarketplaceAccount:
        """Create or replace a marketplace account link."""

    @abstractmethod
    def list_marketplace_accounts(
        self, *, organization_id: str | None = None
    ) -> list[MerchantMarketplaceAccount]:
        """Return marketplace account links."""

    @abstractmethod
    def save_notification_preference(
        self, preference: MerchantNotificationPreference
    ) -> MerchantNotificationPreference:
        """Create or replace notification preferences."""

    @abstractmethod
    def get_notification_preference(
        self, account_id: str, organization_id: str
    ) -> MerchantNotificationPreference | None:
        """Return notification preferences, or None."""
