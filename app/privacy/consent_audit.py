"""Truthful consent / publication inspection for operators and the account owner.

Works when a published policy exists and remains empty when it does not.
Does not fabricate acceptance records, publication dates, or counsel approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.auth.security import AuditLogger
from app.domain.interfaces.user_platform_repository import ConsentRepository
from app.legal.publication import (
    POLICY_PRIVACY,
    POLICY_TERMS,
    LegalPublicationCatalog,
    unpublished_catalog,
)
from app.privacy.contacts import public_contact_snapshot
from app.privacy.eligibility import eligibility_snapshot
from app.privacy.tracking import tracking_snapshot

UNPUBLISHED_NOTE = (
    "No published Terms or Privacy version exists. Consent records stay empty "
    "and must not be fabricated."
)
OWNER_SCOPED_NOTE = "Records are scoped to the authenticated or operator-supplied user_id only."
NOT_DSAR_NOTE = "This inspection is engineering audit visibility, not a complete legal DSAR."


def publication_status_payload(
    catalog: LegalPublicationCatalog | None = None,
) -> dict[str, Any]:
    """Non-PII publication readiness. Safe for unauthenticated clients."""
    active = catalog or unpublished_catalog()
    terms = active.published(POLICY_TERMS)
    privacy = active.published(POLICY_PRIVACY)
    payload: dict[str, Any] = {
        "terms_published": terms is not None,
        "privacy_published": privacy is not None,
        "terms_version_id": terms.version_id if terms is not None else None,
        "privacy_version_id": privacy.version_id if privacy is not None else None,
        "terms_acceptance_required": active.requires_acceptance(POLICY_TERMS),
        "privacy_acceptance_required": active.requires_acceptance(POLICY_PRIVACY),
        "cookie_notice_published": False,
        "counsel_drafts_are_not_public": True,
        **public_contact_snapshot(),
        **eligibility_snapshot(),
        **tracking_snapshot(),
    }
    return payload


@dataclass(frozen=True, slots=True)
class ConsentAuditSnapshot:
    """Owner-scoped consent inspection. Empty when no published policy exists."""

    user_id: str
    terms_published: bool
    privacy_published: bool
    terms_version_id: str | None
    privacy_version_id: str | None
    records: tuple[dict[str, Any], ...]
    policy_accepted_events: tuple[dict[str, Any], ...]
    unpublished: bool
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "terms_published": self.terms_published,
            "privacy_published": self.privacy_published,
            "terms_version_id": self.terms_version_id,
            "privacy_version_id": self.privacy_version_id,
            "records": list(self.records),
            "policy_accepted_events": list(self.policy_accepted_events),
            "unpublished": self.unpublished,
            "notes": list(self.notes),
        }


def inspect_consent(
    *,
    user_id: str,
    catalog: LegalPublicationCatalog | None = None,
    consents: ConsentRepository | None = None,
    audit: AuditLogger | None = None,
) -> ConsentAuditSnapshot:
    """Build a truthful snapshot for one user. Does not invent records."""
    if not (user_id or "").strip():
        raise ValueError("user_id is required")
    active = catalog or unpublished_catalog()
    terms = active.published(POLICY_TERMS)
    privacy = active.published(POLICY_PRIVACY)
    unpublished = terms is None and privacy is None
    records: list[dict[str, Any]] = []
    if consents is not None:
        records = [record.to_dict() for record in consents.list_for_user(user_id)]
    events: list[dict[str, Any]] = []
    if audit is not None:
        events = [
            event.to_dict()
            for event in audit.recent(user_id=user_id, limit=100)
            if event.event_type == "policy_accepted" and event.user_id == user_id
        ]
    notes = [OWNER_SCOPED_NOTE, NOT_DSAR_NOTE]
    if unpublished:
        notes.insert(0, UNPUBLISHED_NOTE)
    return ConsentAuditSnapshot(
        user_id=user_id,
        terms_published=terms is not None,
        privacy_published=privacy is not None,
        terms_version_id=terms.version_id if terms is not None else None,
        privacy_version_id=privacy.version_id if privacy is not None else None,
        records=tuple(records),
        policy_accepted_events=tuple(events),
        unpublished=unpublished,
        notes=tuple(notes),
    )
