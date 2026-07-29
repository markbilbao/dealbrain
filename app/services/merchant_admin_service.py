"""Internal admin review workflows for Merchant Platform — Sprint 21."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.merchant import (
    MerchantActor,
    MerchantAuditAction,
    MerchantOrganization,
    MerchantOrgStatus,
    MerchantProductSubmission,
    MerchantVerificationStatus,
    SubmissionStatus,
)
from app.domain.exceptions import (
    MerchantOrganizationNotFoundError,
    MerchantSubmissionNotFoundError,
    MerchantValidationError,
)
from app.domain.interfaces.merchant_repository import (
    MerchantAuditRepository,
    MerchantAuxiliaryRepository,
    MerchantOrganizationRepository,
    MerchantSubmissionRepository,
)
from app.merchant.security.permissions import require_internal_admin
from app.merchant.security.redaction import MerchantAuditHook, redact_secrets


class MerchantAdminService:
    """INTERNAL_ADMIN workflows: approve/reject, suspend/activate, verification."""

    def __init__(
        self,
        organizations: MerchantOrganizationRepository,
        submissions: MerchantSubmissionRepository,
        auxiliary: MerchantAuxiliaryRepository,
        audit: MerchantAuditRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._organizations = organizations
        self._submissions = submissions
        self._auxiliary = auxiliary
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._audit_hook = MerchantAuditHook(clock=self._clock, id_factory=self._id_factory)

    def list_submissions(
        self,
        actor: MerchantActor,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MerchantProductSubmission]:
        require_internal_admin(actor)
        return self._submissions.list_product_submissions(status=status, limit=limit)

    def approve_submission(
        self,
        actor: MerchantActor,
        submission_id: str,
        *,
        notes: str = "",
    ) -> MerchantProductSubmission:
        require_internal_admin(actor)
        submission = self._require_submission(submission_id)
        if submission.status not in (
            SubmissionStatus.SUBMITTED,
            SubmissionStatus.UNDER_REVIEW,
            SubmissionStatus.NEEDS_CHANGES,
        ):
            raise MerchantValidationError(
                f"Cannot approve submission in status '{submission.status.value}'."
            )
        # Ambiguous matches must not be silently approved as merges.
        if (
            submission.match_result
            and submission.match_result.ambiguity == "ambiguous"
            and not submission.matched_product_id
        ):
            # Allow approval as a new product listing, but keep matched_product_id None.
            notes = (notes + " Approved without merge — ambiguous match.").strip()
        updated = replace(
            submission,
            status=SubmissionStatus.APPROVED,
            review_notes=notes,
            updated_at=self._clock(),
        )
        self._submissions.save_product_submission(updated)
        self._record(
            actor,
            MerchantAuditAction.SUBMISSION_APPROVED,
            "product_submission",
            submission_id,
            organization_id=submission.organization_id,
            metadata={"notes": notes},
        )
        return updated

    def reject_submission(
        self,
        actor: MerchantActor,
        submission_id: str,
        *,
        notes: str = "",
        needs_changes: bool = False,
    ) -> MerchantProductSubmission:
        require_internal_admin(actor)
        submission = self._require_submission(submission_id)
        if submission.status in (
            SubmissionStatus.APPROVED,
            SubmissionStatus.ARCHIVED,
            SubmissionStatus.WITHDRAWN,
        ):
            raise MerchantValidationError(
                f"Cannot reject submission in status '{submission.status.value}'."
            )
        status = SubmissionStatus.NEEDS_CHANGES if needs_changes else SubmissionStatus.REJECTED
        updated = replace(
            submission,
            status=status,
            review_notes=notes or "Rejected by internal admin.",
            updated_at=self._clock(),
        )
        self._submissions.save_product_submission(updated)
        self._record(
            actor,
            MerchantAuditAction.SUBMISSION_REJECTED,
            "product_submission",
            submission_id,
            organization_id=submission.organization_id,
            metadata={"status": status.value, "notes": notes},
        )
        return updated

    def suspend_merchant(
        self, actor: MerchantActor, organization_id: str, *, notes: str = ""
    ) -> MerchantOrganization:
        require_internal_admin(actor)
        org = self._require_org(organization_id)
        if org.status == MerchantOrgStatus.ARCHIVED:
            raise MerchantValidationError("Cannot suspend an archived organization.")
        updated = replace(org, status=MerchantOrgStatus.SUSPENDED, updated_at=self._clock())
        self._organizations.save_organization(updated)
        self._record(
            actor,
            MerchantAuditAction.ORGANIZATION_SUSPENDED,
            "organization",
            organization_id,
            organization_id=organization_id,
            metadata={"notes": notes},
        )
        return updated

    def activate_merchant(
        self, actor: MerchantActor, organization_id: str, *, notes: str = ""
    ) -> MerchantOrganization:
        require_internal_admin(actor)
        org = self._require_org(organization_id)
        if org.status == MerchantOrgStatus.ARCHIVED:
            raise MerchantValidationError("Cannot activate an archived organization.")
        updated = replace(org, status=MerchantOrgStatus.ACTIVE, updated_at=self._clock())
        self._organizations.save_organization(updated)
        self._record(
            actor,
            MerchantAuditAction.ORGANIZATION_ACTIVATED,
            "organization",
            organization_id,
            organization_id=organization_id,
            metadata={"notes": notes},
        )
        return updated

    def update_verification(
        self,
        actor: MerchantActor,
        organization_id: str,
        *,
        status: str,
        notes: str = "",
    ) -> MerchantOrganization:
        require_internal_admin(actor)
        org = self._require_org(organization_id)
        try:
            vstatus = MerchantVerificationStatus(str(status).strip().lower())
        except ValueError as exc:
            raise MerchantValidationError(f"Invalid verification status: {status}") from exc
        stamp = self._clock()
        profile = replace(org.profile, verification_status=vstatus)
        updated = replace(org, profile=profile, updated_at=stamp)
        self._organizations.save_organization(updated)
        existing = self._auxiliary.get_verification(organization_id)
        if existing:
            self._auxiliary.save_verification(
                replace(
                    existing,
                    status=vstatus,
                    updated_at=stamp,
                    reviewed_by=actor.account_id,
                    notes=notes or existing.notes,
                )
            )
        self._record(
            actor,
            MerchantAuditAction.VERIFICATION_UPDATED,
            "organization",
            organization_id,
            organization_id=organization_id,
            metadata={"verification_status": vstatus.value},
        )
        return updated

    def list_match_reviews(self, actor: MerchantActor, *, limit: int = 100):
        require_internal_admin(actor)
        return self._submissions.list_match_reviews(status="open", limit=limit)

    def _require_submission(self, submission_id: str) -> MerchantProductSubmission:
        submission = self._submissions.get_product_submission(submission_id)
        if submission is None:
            raise MerchantSubmissionNotFoundError(submission_id)
        return submission

    def _require_org(self, organization_id: str) -> MerchantOrganization:
        org = self._organizations.get_organization(organization_id)
        if org is None:
            raise MerchantOrganizationNotFoundError(organization_id)
        return org

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
