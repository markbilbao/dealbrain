"""Sponsored campaign draft framework — Sprint 21.

No real billing. Never alters organic rankings. Always labeled sponsored.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.merchant import (
    SPONSORED_LABEL,
    CampaignPlacementType,
    MerchantActor,
    MerchantAuditAction,
    MerchantCampaign,
    MerchantCampaignBudget,
    MerchantCampaignPlacement,
    MerchantCampaignStatus,
    MerchantPermission,
)
from app.domain.exceptions import MerchantCampaignNotFoundError, MerchantValidationError
from app.domain.interfaces.merchant_repository import (
    MerchantAuditRepository,
    MerchantCampaignRepository,
)
from app.merchant.campaigns import assert_transition, ensure_sponsored_label
from app.merchant.security.permissions import require_membership, require_permission
from app.merchant.security.redaction import MerchantAuditHook, redact_secrets
from app.merchant.security.validation import MAX_TITLE_LENGTH, validate_text_length


class MerchantCampaignService:
    """Draft / pause / resume / cancel sponsored campaigns."""

    def __init__(
        self,
        campaigns: MerchantCampaignRepository,
        audit: MerchantAuditRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._campaigns = campaigns
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._audit_hook = MerchantAuditHook(clock=self._clock, id_factory=self._id_factory)

    def list_campaigns(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantCampaign]:
        require_membership(actor, organization_id)
        return self._campaigns.list_campaigns(
            organization_id=organization_id, status=status, limit=limit
        )

    def create_campaign(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        name: str,
        placements: list[dict[str, Any]] | None = None,
        currency: str = "USD",
        daily_budget: float | None = None,
        total_budget: float | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        targeting_metadata: dict[str, Any] | None = None,
        product_ids: list[str] | None = None,
        placement_types: list[str] | None = None,
    ) -> MerchantCampaign:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.CAMPAIGN_MANAGE)
        if starts_at and ends_at and ends_at < starts_at:
            raise MerchantValidationError("ends_at must be after starts_at.")
        if daily_budget is not None and daily_budget < 0:
            raise MerchantValidationError("daily_budget must be non-negative.")
        if total_budget is not None and total_budget < 0:
            raise MerchantValidationError("total_budget must be non-negative.")

        built_placements = self._build_placements(
            placements=placements,
            product_ids=product_ids,
            placement_types=placement_types,
            targeting_metadata=targeting_metadata,
        )
        stamp = self._clock()
        campaign = MerchantCampaign(
            campaign_id=f"camp-{self._id_factory()}",
            organization_id=organization_id,
            created_by_account_id=actor.account_id,
            name=validate_text_length(
                name, field="name", max_length=MAX_TITLE_LENGTH, required=True
            ),
            status=MerchantCampaignStatus.DRAFT,
            placements=built_placements,
            budget=MerchantCampaignBudget(
                currency=currency.upper(),
                daily_budget=daily_budget,
                total_budget=total_budget,
            ),
            starts_at=starts_at,
            ends_at=ends_at,
            targeting_metadata=dict(targeting_metadata or {}),
            sponsored_label=SPONSORED_LABEL,
            organic_ranking_independent=True,
            created_at=stamp,
            updated_at=stamp,
        )
        ensure_sponsored_label(campaign)
        self._campaigns.save_campaign(campaign)
        self._record(
            actor,
            MerchantAuditAction.CAMPAIGN_CREATED,
            "campaign",
            campaign.campaign_id,
            organization_id=organization_id,
        )
        return campaign

    def update_campaign(
        self,
        actor: MerchantActor,
        organization_id: str,
        campaign_id: str,
        **fields: Any,
    ) -> MerchantCampaign:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.CAMPAIGN_MANAGE)
        campaign = self._get_owned(organization_id, campaign_id)
        if campaign.status not in (
            MerchantCampaignStatus.DRAFT,
            MerchantCampaignStatus.PAUSED,
            MerchantCampaignStatus.SCHEDULED,
            MerchantCampaignStatus.PENDING_REVIEW,
        ):
            raise MerchantValidationError(
                f"Cannot update campaign in status '{campaign.status.value}'."
            )
        placements = campaign.placements
        if "placements" in fields or "product_ids" in fields or "placement_types" in fields:
            placements = self._build_placements(
                placements=fields.get("placements"),
                product_ids=fields.get("product_ids"),
                placement_types=fields.get("placement_types"),
                targeting_metadata=fields.get("targeting_metadata", campaign.targeting_metadata),
            )
        budget = campaign.budget
        if any(k in fields for k in ("currency", "daily_budget", "total_budget")):
            budget = MerchantCampaignBudget(
                currency=str(fields.get("currency", budget.currency)).upper(),
                daily_budget=fields.get("daily_budget", budget.daily_budget),
                total_budget=fields.get("total_budget", budget.total_budget),
            )
        updated = replace(
            campaign,
            name=validate_text_length(
                fields.get("name", campaign.name),
                field="name",
                max_length=MAX_TITLE_LENGTH,
                required=True,
            ),
            placements=placements,
            budget=budget,
            starts_at=fields.get("starts_at", campaign.starts_at),
            ends_at=fields.get("ends_at", campaign.ends_at),
            targeting_metadata=dict(
                fields.get("targeting_metadata", campaign.targeting_metadata) or {}
            ),
            sponsored_label=SPONSORED_LABEL,
            organic_ranking_independent=True,
            updated_at=self._clock(),
        )
        ensure_sponsored_label(updated)
        self._campaigns.save_campaign(updated)
        self._record(
            actor,
            MerchantAuditAction.CAMPAIGN_UPDATED,
            "campaign",
            campaign_id,
            organization_id=organization_id,
        )
        return updated

    def pause_campaign(
        self, actor: MerchantActor, organization_id: str, campaign_id: str
    ) -> MerchantCampaign:
        return self._transition(
            actor,
            organization_id,
            campaign_id,
            MerchantCampaignStatus.PAUSED,
            MerchantAuditAction.CAMPAIGN_PAUSED,
        )

    def resume_campaign(
        self, actor: MerchantActor, organization_id: str, campaign_id: str
    ) -> MerchantCampaign:
        return self._transition(
            actor,
            organization_id,
            campaign_id,
            MerchantCampaignStatus.ACTIVE,
            MerchantAuditAction.CAMPAIGN_RESUMED,
        )

    def cancel_campaign(
        self, actor: MerchantActor, organization_id: str, campaign_id: str
    ) -> MerchantCampaign:
        return self._transition(
            actor,
            organization_id,
            campaign_id,
            MerchantCampaignStatus.CANCELLED,
            MerchantAuditAction.CAMPAIGN_CANCELLED,
        )

    def _transition(
        self,
        actor: MerchantActor,
        organization_id: str,
        campaign_id: str,
        target: MerchantCampaignStatus,
        action: MerchantAuditAction,
    ) -> MerchantCampaign:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.CAMPAIGN_MANAGE)
        campaign = self._get_owned(organization_id, campaign_id)
        assert_transition(campaign.status, target)
        updated = replace(campaign, status=target, updated_at=self._clock())
        ensure_sponsored_label(updated)
        self._campaigns.save_campaign(updated)
        self._record(actor, action, "campaign", campaign_id, organization_id=organization_id)
        return updated

    def _build_placements(
        self,
        *,
        placements: list[dict[str, Any]] | None,
        product_ids: list[str] | None,
        placement_types: list[str] | None,
        targeting_metadata: dict[str, Any] | None,
    ) -> tuple[MerchantCampaignPlacement, ...]:
        if placements:
            built: list[MerchantCampaignPlacement] = []
            for raw in placements:
                ptype = CampaignPlacementType(
                    str(raw.get("placement_type", "sponsored_product")).lower()
                )
                built.append(
                    MerchantCampaignPlacement(
                        placement_id=str(raw.get("placement_id") or f"place-{self._id_factory()}"),
                        placement_type=ptype,
                        product_ids=tuple(raw.get("product_ids") or ()),
                        offer_ids=tuple(raw.get("offer_ids") or ()),
                        targeting_metadata=dict(raw.get("targeting_metadata") or {}),
                        sponsored_label=SPONSORED_LABEL,
                    )
                )
            return tuple(built)

        types = placement_types or ["sponsored_product"]
        products = tuple(product_ids or ())
        return tuple(
            MerchantCampaignPlacement(
                placement_id=f"place-{self._id_factory()}",
                placement_type=CampaignPlacementType(str(t).lower()),
                product_ids=products,
                targeting_metadata=dict(targeting_metadata or {}),
                sponsored_label=SPONSORED_LABEL,
            )
            for t in types
        )

    def _get_owned(self, organization_id: str, campaign_id: str) -> MerchantCampaign:
        campaign = self._campaigns.get_campaign(campaign_id)
        if campaign is None:
            raise MerchantCampaignNotFoundError(campaign_id)
        if campaign.organization_id != organization_id:
            raise MerchantValidationError("Campaign does not belong to this organization.")
        return campaign

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
