"""Merchant promotion management — Sprint 21.

Promotions never automatically increase DealScore.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.merchant import (
    MerchantActor,
    MerchantAuditAction,
    MerchantPermission,
    MerchantPromotion,
    PromotionStatus,
    PromotionType,
)
from app.domain.exceptions import MerchantPromotionNotFoundError, MerchantValidationError
from app.domain.interfaces.merchant_repository import (
    MerchantAuditRepository,
    MerchantPromotionRepository,
)
from app.merchant.security.permissions import require_membership, require_permission
from app.merchant.security.redaction import MerchantAuditHook, redact_secrets
from app.merchant.security.validation import MAX_TITLE_LENGTH, validate_text_length


class MerchantPromotionService:
    """Promotion create/update/pause lifecycle."""

    def __init__(
        self,
        promotions: MerchantPromotionRepository,
        audit: MerchantAuditRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._promotions = promotions
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._audit_hook = MerchantAuditHook(clock=self._clock, id_factory=self._id_factory)

    def list_promotions(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantPromotion]:
        require_membership(actor, organization_id)
        return self._promotions.list_promotions(
            organization_id=organization_id, status=status, limit=limit
        )

    def create_promotion(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        promotion_type: str,
        title: str,
        description: str = "",
        coupon_code: str | None = None,
        sale_price: float | None = None,
        currency: str = "USD",
        terms: str = "",
        product_ids: list[str] | None = None,
        offer_ids: list[str] | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        cashback_description: str | None = None,
        status: str = "draft",
    ) -> MerchantPromotion:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.PROMOTION_MANAGE)
        ptype = self._parse_type(promotion_type)
        pstatus = self._parse_status(status)
        if starts_at and ends_at and ends_at < starts_at:
            raise MerchantValidationError("ends_at must be after starts_at.")
        if sale_price is not None and sale_price < 0:
            raise MerchantValidationError("sale_price must be non-negative.")
        stamp = self._clock()
        promotion = MerchantPromotion(
            promotion_id=f"promo-{self._id_factory()}",
            organization_id=organization_id,
            created_by_account_id=actor.account_id,
            promotion_type=ptype,
            status=pstatus,
            title=validate_text_length(
                title, field="title", max_length=MAX_TITLE_LENGTH, required=True
            ),
            description=description,
            coupon_code=coupon_code,
            sale_price=sale_price,
            currency=currency.upper(),
            terms=terms,
            product_ids=tuple(product_ids or ()),
            offer_ids=tuple(offer_ids or ()),
            starts_at=starts_at,
            ends_at=ends_at,
            cashback_description=cashback_description,
            dealscore_independent=True,
            created_at=stamp,
            updated_at=stamp,
        )
        self._promotions.save_promotion(promotion)
        self._record(
            actor,
            MerchantAuditAction.PROMOTION_CREATED,
            "promotion",
            promotion.promotion_id,
            organization_id=organization_id,
        )
        return promotion

    def update_promotion(
        self,
        actor: MerchantActor,
        organization_id: str,
        promotion_id: str,
        **fields: Any,
    ) -> MerchantPromotion:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.PROMOTION_MANAGE)
        promotion = self._get_owned(actor, organization_id, promotion_id)
        if promotion.status == PromotionStatus.CANCELLED:
            raise MerchantValidationError("Cannot update a cancelled promotion.")
        updated = replace(
            promotion,
            title=validate_text_length(
                fields.get("title", promotion.title),
                field="title",
                max_length=MAX_TITLE_LENGTH,
                required=True,
            ),
            description=fields.get("description", promotion.description),
            coupon_code=fields.get("coupon_code", promotion.coupon_code),
            sale_price=fields.get("sale_price", promotion.sale_price),
            currency=str(fields.get("currency", promotion.currency)).upper(),
            terms=fields.get("terms", promotion.terms),
            product_ids=tuple(fields.get("product_ids", promotion.product_ids)),
            offer_ids=tuple(fields.get("offer_ids", promotion.offer_ids)),
            starts_at=fields.get("starts_at", promotion.starts_at),
            ends_at=fields.get("ends_at", promotion.ends_at),
            cashback_description=fields.get("cashback_description", promotion.cashback_description),
            dealscore_independent=True,
            updated_at=self._clock(),
        )
        self._promotions.save_promotion(updated)
        self._record(
            actor,
            MerchantAuditAction.PROMOTION_UPDATED,
            "promotion",
            promotion_id,
            organization_id=organization_id,
        )
        return updated

    def pause_promotion(
        self, actor: MerchantActor, organization_id: str, promotion_id: str
    ) -> MerchantPromotion:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.PROMOTION_MANAGE)
        promotion = self._get_owned(actor, organization_id, promotion_id)
        if promotion.status not in (PromotionStatus.ACTIVE, PromotionStatus.SCHEDULED):
            raise MerchantValidationError("Only active or scheduled promotions can be paused.")
        updated = replace(promotion, status=PromotionStatus.PAUSED, updated_at=self._clock())
        self._promotions.save_promotion(updated)
        self._record(
            actor,
            MerchantAuditAction.PROMOTION_PAUSED,
            "promotion",
            promotion_id,
            organization_id=organization_id,
        )
        return updated

    def _get_owned(
        self, actor: MerchantActor, organization_id: str, promotion_id: str
    ) -> MerchantPromotion:
        del actor  # membership already checked by caller
        promotion = self._promotions.get_promotion(promotion_id)
        if promotion is None:
            raise MerchantPromotionNotFoundError(promotion_id)
        if promotion.organization_id != organization_id:
            raise MerchantValidationError("Promotion does not belong to this organization.")
        return promotion

    def _parse_type(self, value: str) -> PromotionType:
        try:
            return PromotionType(str(value).strip().lower())
        except ValueError as exc:
            raise MerchantValidationError(f"Invalid promotion type: {value}") from exc

    def _parse_status(self, value: str) -> PromotionStatus:
        try:
            return PromotionStatus(str(value).strip().lower())
        except ValueError as exc:
            raise MerchantValidationError(f"Invalid promotion status: {value}") from exc

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
