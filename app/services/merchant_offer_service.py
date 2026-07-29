"""Merchant offer submission service — Sprint 21."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.merchant import (
    MerchantActor,
    MerchantAuditAction,
    MerchantOfferSubmission,
    MerchantPermission,
    MerchantSourceMode,
    SubmissionStatus,
)
from app.domain.exceptions import MerchantSubmissionNotFoundError, MerchantValidationError
from app.domain.interfaces.merchant_repository import (
    MerchantAuditRepository,
    MerchantSubmissionRepository,
)
from app.merchant.security.permissions import require_membership, require_permission
from app.merchant.security.redaction import MerchantAuditHook, redact_secrets
from app.merchant.security.validation import (
    MAX_TITLE_LENGTH,
    validate_safe_url,
    validate_text_length,
)


class MerchantOfferService:
    """Offer submit/update/deactivate with merchant provenance."""

    def __init__(
        self,
        submissions: MerchantSubmissionRepository,
        audit: MerchantAuditRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._submissions = submissions
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._audit_hook = MerchantAuditHook(clock=self._clock, id_factory=self._id_factory)

    def list_offers(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantOfferSubmission]:
        require_membership(actor, organization_id)
        return self._submissions.list_offer_submissions(
            organization_id=organization_id, status=status, limit=limit
        )

    def get_offer(
        self, actor: MerchantActor, organization_id: str, offer_id: str
    ) -> MerchantOfferSubmission:
        require_membership(actor, organization_id)
        offer = self._require(offer_id)
        if offer.organization_id != organization_id:
            raise MerchantValidationError("Offer does not belong to this organization.")
        return offer

    def create_offer(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        title: str,
        currency: str,
        price: float,
        sale_price: float | None = None,
        shipping_cost: float = 0.0,
        inventory_quantity: int | None = None,
        availability: str = "in_stock",
        marketplace_url: str | None = None,
        warranty: str | None = None,
        seller_details: str | None = None,
        product_submission_id: str | None = None,
        matched_product_id: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> MerchantOfferSubmission:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.OFFER_SUBMIT)
        self._validate_pricing(price, sale_price, shipping_cost, inventory_quantity)
        stamp = self._clock()
        offer = MerchantOfferSubmission(
            offer_id=f"osub-{self._id_factory()}",
            organization_id=organization_id,
            submitted_by_account_id=actor.account_id,
            status=SubmissionStatus.SUBMITTED,
            title=validate_text_length(
                title, field="title", max_length=MAX_TITLE_LENGTH, required=True
            ),
            currency=validate_text_length(
                currency, field="currency", max_length=8, required=True
            ).upper(),
            price=float(price),
            sale_price=float(sale_price) if sale_price is not None else None,
            shipping_cost=float(shipping_cost),
            inventory_quantity=inventory_quantity,
            availability=availability,
            marketplace_url=validate_safe_url(marketplace_url),
            warranty=warranty,
            seller_details=seller_details,
            product_submission_id=product_submission_id,
            matched_product_id=matched_product_id,
            raw_payload=redact_secrets(raw_payload or {}),
            source_mode=MerchantSourceMode.MERCHANT_SUBMITTED,
            created_at=stamp,
            updated_at=stamp,
        )
        self._submissions.save_offer_submission(offer)
        self._record(
            actor,
            MerchantAuditAction.OFFER_SUBMITTED,
            "offer_submission",
            offer.offer_id,
            organization_id=organization_id,
        )
        return offer

    def update_offer(
        self,
        actor: MerchantActor,
        organization_id: str,
        offer_id: str,
        **fields: Any,
    ) -> MerchantOfferSubmission:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.OFFER_SUBMIT)
        offer = self.get_offer(actor, organization_id, offer_id)
        if not offer.is_active or offer.status == SubmissionStatus.ARCHIVED:
            raise MerchantValidationError("Cannot update an inactive or archived offer.")
        price = float(fields.get("price", offer.price))
        sale_price = fields.get("sale_price", offer.sale_price)
        shipping_cost = float(fields.get("shipping_cost", offer.shipping_cost))
        inventory_quantity = fields.get("inventory_quantity", offer.inventory_quantity)
        self._validate_pricing(price, sale_price, shipping_cost, inventory_quantity)
        marketplace_url = fields.get("marketplace_url", offer.marketplace_url)
        updated = replace(
            offer,
            title=validate_text_length(
                fields.get("title", offer.title),
                field="title",
                max_length=MAX_TITLE_LENGTH,
                required=True,
            ),
            currency=str(fields.get("currency", offer.currency)).upper(),
            price=price,
            sale_price=float(sale_price) if sale_price is not None else None,
            shipping_cost=shipping_cost,
            inventory_quantity=inventory_quantity,
            availability=fields.get("availability", offer.availability),
            marketplace_url=validate_safe_url(marketplace_url) if marketplace_url else None,
            warranty=fields.get("warranty", offer.warranty),
            seller_details=fields.get("seller_details", offer.seller_details),
            raw_payload=redact_secrets(fields.get("raw_payload", offer.raw_payload) or {}),
            updated_at=self._clock(),
        )
        self._submissions.save_offer_submission(updated)
        self._record(
            actor,
            MerchantAuditAction.OFFER_UPDATED,
            "offer_submission",
            offer_id,
            organization_id=organization_id,
        )
        return updated

    def deactivate_offer(
        self, actor: MerchantActor, organization_id: str, offer_id: str
    ) -> MerchantOfferSubmission:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.OFFER_SUBMIT)
        offer = self.get_offer(actor, organization_id, offer_id)
        updated = replace(
            offer,
            is_active=False,
            status=SubmissionStatus.ARCHIVED,
            updated_at=self._clock(),
        )
        self._submissions.save_offer_submission(updated)
        self._record(
            actor,
            MerchantAuditAction.OFFER_DEACTIVATED,
            "offer_submission",
            offer_id,
            organization_id=organization_id,
        )
        return updated

    def _validate_pricing(
        self,
        price: float,
        sale_price: float | None,
        shipping_cost: float,
        inventory_quantity: int | None,
    ) -> None:
        if price < 0:
            raise MerchantValidationError("price must be non-negative.")
        if sale_price is not None and sale_price < 0:
            raise MerchantValidationError("sale_price must be non-negative.")
        if shipping_cost < 0:
            raise MerchantValidationError("shipping_cost must be non-negative.")
        if inventory_quantity is not None and inventory_quantity < 0:
            raise MerchantValidationError("inventory_quantity must be non-negative.")

    def _require(self, offer_id: str) -> MerchantOfferSubmission:
        offer = self._submissions.get_offer_submission(offer_id)
        if offer is None:
            raise MerchantSubmissionNotFoundError(offer_id, resource_type="offer_submission")
        return offer

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
