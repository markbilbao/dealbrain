"""Merchant product submission service — Sprint 21.

Submissions pass through validation, normalization, and Sprint 18 matching.
Never bypass Marketplace Data provenance — source_mode is MERCHANT_SUBMITTED.
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
    MerchantMatchReview,
    MerchantPermission,
    MerchantProductSubmission,
    MerchantSourceMode,
    SubmissionStatus,
)
from app.domain.exceptions import MerchantSubmissionNotFoundError, MerchantValidationError
from app.domain.interfaces.merchant_repository import (
    MerchantAuditRepository,
    MerchantSubmissionRepository,
)
from app.merchant.matching import MerchantProductMatcher
from app.merchant.security.permissions import require_membership, require_permission
from app.merchant.security.redaction import MerchantAuditHook, redact_secrets
from app.merchant.security.validation import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    validate_image_urls,
    validate_text_length,
)


class MerchantProductService:
    """Product submission CRUD, submit/withdraw, matching, and validation."""

    def __init__(
        self,
        submissions: MerchantSubmissionRepository,
        audit: MerchantAuditRepository,
        matcher: MerchantProductMatcher | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._submissions = submissions
        self._audit = audit
        self._matcher = matcher or MerchantProductMatcher()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._audit_hook = MerchantAuditHook(clock=self._clock, id_factory=self._id_factory)

    def list_products(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantProductSubmission]:
        require_membership(actor, organization_id)
        return self._submissions.list_product_submissions(
            organization_id=organization_id, status=status, limit=limit
        )

    def get_product(
        self, actor: MerchantActor, organization_id: str, submission_id: str
    ) -> MerchantProductSubmission:
        require_membership(actor, organization_id)
        submission = self._require(submission_id)
        if submission.organization_id != organization_id:
            raise MerchantValidationError("Submission does not belong to this organization.")
        return submission

    def create_product(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        title: str,
        brand: str | None = None,
        model: str | None = None,
        category: str | None = None,
        description: str = "",
        sku: str | None = None,
        upc: str | None = None,
        ean: str | None = None,
        gtin: str | None = None,
        merchant_product_id: str | None = None,
        image_urls: list[str] | None = None,
        identifiers: dict[str, str] | None = None,
        warranty: str | None = None,
        seller_info: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> MerchantProductSubmission:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.PRODUCT_SUBMIT)
        stamp = self._clock()
        cleaned_title = validate_text_length(
            title, field="title", max_length=MAX_TITLE_LENGTH, required=True
        )
        images = validate_image_urls(image_urls)
        errors = self._validate_fields(
            title=cleaned_title, brand=brand, upc=upc, ean=ean, gtin=gtin
        )
        submission = MerchantProductSubmission(
            submission_id=f"psub-{self._id_factory()}",
            organization_id=organization_id,
            submitted_by_account_id=actor.account_id,
            status=SubmissionStatus.DRAFT,
            title=cleaned_title,
            brand=brand.strip() if brand else None,
            model=model.strip() if model else None,
            category=category.strip() if category else None,
            description=validate_text_length(
                description, field="description", max_length=MAX_DESCRIPTION_LENGTH
            ),
            sku=sku.strip() if sku else None,
            upc=upc.strip() if upc else None,
            ean=ean.strip() if ean else None,
            gtin=gtin.strip() if gtin else None,
            merchant_product_id=merchant_product_id.strip() if merchant_product_id else None,
            image_urls=images,
            identifiers=dict(identifiers or {}),
            warranty=warranty,
            seller_info=seller_info,
            raw_payload=redact_secrets(raw_payload or {}),
            validation_errors=tuple(errors),
            source_mode=MerchantSourceMode.MERCHANT_SUBMITTED,
            created_at=stamp,
            updated_at=stamp,
        )
        self._submissions.save_product_submission(submission)
        self._record(
            actor,
            MerchantAuditAction.PRODUCT_UPDATED,
            "product_submission",
            submission.submission_id,
            organization_id=organization_id,
            metadata={"status": "draft"},
        )
        return submission

    def update_product(
        self,
        actor: MerchantActor,
        organization_id: str,
        submission_id: str,
        **fields: Any,
    ) -> MerchantProductSubmission:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.PRODUCT_SUBMIT)
        submission = self.get_product(actor, organization_id, submission_id)
        if submission.status not in (
            SubmissionStatus.DRAFT,
            SubmissionStatus.NEEDS_CHANGES,
            SubmissionStatus.REJECTED,
        ):
            raise MerchantValidationError(
                "Only draft, needs_changes, or rejected submissions can be updated."
            )
        title = fields.get("title", submission.title)
        cleaned_title = validate_text_length(
            title, field="title", max_length=MAX_TITLE_LENGTH, required=True
        )
        image_urls = fields.get("image_urls")
        images = (
            validate_image_urls(image_urls) if image_urls is not None else submission.image_urls
        )
        brand = fields.get("brand", submission.brand)
        upc = fields.get("upc", submission.upc)
        ean = fields.get("ean", submission.ean)
        gtin = fields.get("gtin", submission.gtin)
        errors = self._validate_fields(
            title=cleaned_title, brand=brand, upc=upc, ean=ean, gtin=gtin
        )
        updated = replace(
            submission,
            title=cleaned_title,
            brand=brand.strip() if isinstance(brand, str) and brand else brand,
            model=fields.get("model", submission.model),
            category=fields.get("category", submission.category),
            description=validate_text_length(
                fields.get("description", submission.description),
                field="description",
                max_length=MAX_DESCRIPTION_LENGTH,
            ),
            sku=fields.get("sku", submission.sku),
            upc=upc,
            ean=ean,
            gtin=gtin,
            merchant_product_id=fields.get("merchant_product_id", submission.merchant_product_id),
            image_urls=images,
            identifiers=fields.get("identifiers", submission.identifiers),
            warranty=fields.get("warranty", submission.warranty),
            seller_info=fields.get("seller_info", submission.seller_info),
            raw_payload=redact_secrets(fields.get("raw_payload", submission.raw_payload) or {}),
            validation_errors=tuple(errors),
            updated_at=self._clock(),
        )
        self._submissions.save_product_submission(updated)
        return updated

    def submit_product(
        self, actor: MerchantActor, organization_id: str, submission_id: str
    ) -> MerchantProductSubmission:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.PRODUCT_SUBMIT)
        submission = self.get_product(actor, organization_id, submission_id)
        if submission.status not in (
            SubmissionStatus.DRAFT,
            SubmissionStatus.NEEDS_CHANGES,
        ):
            raise MerchantValidationError(
                "Only draft or needs_changes submissions can be submitted."
            )
        if submission.validation_errors:
            raise MerchantValidationError(
                "Fix validation errors before submitting: "
                + "; ".join(submission.validation_errors)
            )
        match_result = self._matcher.match(
            brand=submission.brand,
            model=submission.model,
            title=submission.title,
            sku=submission.sku,
            upc=submission.upc,
            ean=submission.ean,
            gtin=submission.gtin,
            merchant_product_id=submission.merchant_product_id,
        )
        stamp = self._clock()
        updated = replace(
            submission,
            status=SubmissionStatus.SUBMITTED,
            match_result=match_result,
            matched_product_id=match_result.matched_product_id,
            updated_at=stamp,
        )
        self._submissions.save_product_submission(updated)
        if match_result.review_required or match_result.ambiguity == "ambiguous":
            review = MerchantMatchReview(
                review_id=f"mrev-{self._id_factory()}",
                organization_id=organization_id,
                submission_id=submission_id,
                ambiguity=match_result.ambiguity,
                confidence=match_result.confidence,
                candidate_ids=match_result.candidate_ids,
                created_at=stamp,
            )
            self._submissions.save_match_review(review)
            self._record(
                actor,
                MerchantAuditAction.MATCH_REVIEW_CREATED,
                "match_review",
                review.review_id,
                organization_id=organization_id,
                metadata={"ambiguity": match_result.ambiguity},
            )
        self._record(
            actor,
            MerchantAuditAction.PRODUCT_SUBMITTED,
            "product_submission",
            submission_id,
            organization_id=organization_id,
            metadata={
                "match_confidence": match_result.confidence,
                "ambiguity": match_result.ambiguity,
            },
        )
        return updated

    def withdraw_product(
        self, actor: MerchantActor, organization_id: str, submission_id: str
    ) -> MerchantProductSubmission:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.PRODUCT_SUBMIT)
        submission = self.get_product(actor, organization_id, submission_id)
        if submission.status in (
            SubmissionStatus.APPROVED,
            SubmissionStatus.ARCHIVED,
            SubmissionStatus.WITHDRAWN,
        ):
            raise MerchantValidationError(
                f"Cannot withdraw a submission in status '{submission.status.value}'."
            )
        updated = replace(submission, status=SubmissionStatus.WITHDRAWN, updated_at=self._clock())
        self._submissions.save_product_submission(updated)
        self._record(
            actor,
            MerchantAuditAction.PRODUCT_WITHDRAWN,
            "product_submission",
            submission_id,
            organization_id=organization_id,
        )
        return updated

    def _validate_fields(
        self,
        *,
        title: str,
        brand: str | None,
        upc: str | None,
        ean: str | None,
        gtin: str | None,
    ) -> list[str]:
        errors: list[str] = []
        if len(title) < 3:
            errors.append("title must be at least 3 characters")
        for label, value in (("upc", upc), ("ean", ean), ("gtin", gtin)):
            if value and not str(value).replace(" ", "").isdigit():
                errors.append(f"{label} must be numeric")
        if brand is not None and not str(brand).strip():
            errors.append("brand cannot be blank when provided")
        return errors

    def _require(self, submission_id: str) -> MerchantProductSubmission:
        submission = self._submissions.get_product_submission(submission_id)
        if submission is None:
            raise MerchantSubmissionNotFoundError(submission_id, resource_type="product_submission")
        return submission

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
