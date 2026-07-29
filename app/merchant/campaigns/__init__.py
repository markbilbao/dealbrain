"""Sponsored campaign lifecycle helpers — no billing, no organic rank changes."""

from __future__ import annotations

from app.domain.entities.merchant import MerchantCampaign, MerchantCampaignStatus
from app.domain.exceptions import MerchantValidationError

# Allowed transitions for the draft campaign framework.
_TRANSITIONS: dict[MerchantCampaignStatus, frozenset[MerchantCampaignStatus]] = {
    MerchantCampaignStatus.DRAFT: frozenset(
        {
            MerchantCampaignStatus.PENDING_REVIEW,
            MerchantCampaignStatus.SCHEDULED,
            MerchantCampaignStatus.CANCELLED,
        }
    ),
    MerchantCampaignStatus.PENDING_REVIEW: frozenset(
        {
            MerchantCampaignStatus.SCHEDULED,
            MerchantCampaignStatus.REJECTED,
            MerchantCampaignStatus.CANCELLED,
            MerchantCampaignStatus.DRAFT,
        }
    ),
    MerchantCampaignStatus.SCHEDULED: frozenset(
        {
            MerchantCampaignStatus.ACTIVE,
            MerchantCampaignStatus.PAUSED,
            MerchantCampaignStatus.CANCELLED,
        }
    ),
    MerchantCampaignStatus.ACTIVE: frozenset(
        {
            MerchantCampaignStatus.PAUSED,
            MerchantCampaignStatus.CANCELLED,
            MerchantCampaignStatus.COMPLETED,
        }
    ),
    MerchantCampaignStatus.PAUSED: frozenset(
        {
            MerchantCampaignStatus.ACTIVE,
            MerchantCampaignStatus.CANCELLED,
            MerchantCampaignStatus.COMPLETED,
        }
    ),
    MerchantCampaignStatus.CANCELLED: frozenset(),
    MerchantCampaignStatus.COMPLETED: frozenset(),
    MerchantCampaignStatus.REJECTED: frozenset({MerchantCampaignStatus.DRAFT}),
}


def assert_transition(current: MerchantCampaignStatus, target: MerchantCampaignStatus) -> None:
    allowed = _TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise MerchantValidationError(
            f"Cannot transition campaign from '{current.value}' to '{target.value}'."
        )


def ensure_sponsored_label(campaign: MerchantCampaign) -> MerchantCampaign:
    """Campaigns must remain labeled as sponsored and ranking-independent."""
    if not campaign.organic_ranking_independent:
        raise MerchantValidationError(
            "Sponsored campaigns must remain independent of organic ranking."
        )
    if "sponsored" not in campaign.sponsored_label.lower():
        raise MerchantValidationError("Sponsored campaigns must carry a sponsored label.")
    return campaign
