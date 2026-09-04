"""Server-owned legal policy-version catalog and publication gate.

Fail closed: a policy is public or enforceable only when a version is
``published``, has a non-empty version id, and approved public HTML can be
loaded. Counsel drafts under ``docs/legal/`` are never treated as published
product documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PolicyType = Literal["terms", "privacy", "affiliate_disclosure", "cookie_notice"]
PublicationStatus = Literal["draft", "approved", "published"]

POLICY_TERMS: PolicyType = "terms"
POLICY_PRIVACY: PolicyType = "privacy"
PUBLIC_POLICY_TYPES: tuple[PolicyType, ...] = (POLICY_TERMS, POLICY_PRIVACY)
PUBLIC_PATHS: dict[PolicyType, str] = {
    POLICY_TERMS: "/terms",
    POLICY_PRIVACY: "/privacy",
}

COUNSEL_DRAFT_CONTENT_MARKERS: tuple[str, ...] = (
    "DRAFT — COUNSEL REVIEW REQUIRED",
    "Not for publication",
    "Not evidence of legal approval",
)
_BLOCKED_PATH_FRAGMENTS: tuple[str, ...] = (
    "docs/legal",
    "_counsel_draft",
)


@dataclass(frozen=True, slots=True)
class PolicyVersion:
    """Typed, server-owned policy version.

    Production catalog stays empty until counsel-approved documents exist.
    ``draft`` and ``approved`` rows are never served or enforced.
    """

    policy_type: PolicyType
    version_id: str
    publication_status: PublicationStatus = "draft"
    acceptance_required: bool = False
    published_at: str | None = None
    effective_at: str | None = None
    html_path: str = ""
    public_path: str = ""

    @property
    def published_version_id(self) -> str:
        return self.version_id

    def is_active_published(self) -> bool:
        return self.publication_status == "published" and bool(self.version_id.strip())


def published_policy(
    *,
    policy_type: PolicyType,
    version_id: str,
    html_path: str,
    public_path: str | None = None,
    acceptance_required: bool = True,
    published_at: str | None = None,
    effective_at: str | None = None,
) -> PolicyVersion:
    """Construct a published version for tests or future approved catalogs."""
    return PolicyVersion(
        policy_type=policy_type,
        version_id=version_id,
        publication_status="published",
        acceptance_required=acceptance_required,
        published_at=published_at,
        effective_at=effective_at,
        html_path=html_path,
        public_path=public_path or PUBLIC_PATHS.get(policy_type, ""),
    )


class LegalPublicationCatalog:
    """Immutable catalog of policy versions.

    The production catalog is empty until EXT-20 / EXT-21 publication occurs.
    Tests construct a *separate* catalog instance; they must not mutate a
    process-global production catalog.
    """

    def __init__(self, versions: tuple[PolicyVersion, ...] = ()) -> None:
        by_type: dict[PolicyType, PolicyVersion] = {}
        for version in versions:
            if version.policy_type in by_type:
                raise ValueError(f"duplicate policy type: {version.policy_type}")
            by_type[version.policy_type] = version
        self._versions = by_type

    def current(self, policy_type: PolicyType) -> PolicyVersion | None:
        """Return the configured row for a type, including unpublished drafts."""
        return self._versions.get(policy_type)

    def published(self, policy_type: PolicyType) -> PolicyVersion | None:
        """Return the active published version only when it is actually servable."""
        version = self._versions.get(policy_type)
        if version is None or not version.is_active_published():
            return None
        if load_approved_public_html(version.html_path) is None:
            return None
        return version

    def is_published(self, policy_type: PolicyType) -> bool:
        return self.published(policy_type) is not None

    def published_version_id(self, policy_type: PolicyType) -> str | None:
        version = self.published(policy_type)
        return version.version_id if version is not None else None

    def requires_acceptance(self, policy_type: PolicyType) -> bool:
        version = self.published(policy_type)
        return bool(version is not None and version.acceptance_required)

    def configured_versions(self) -> tuple[PolicyVersion, ...]:
        """Raw configured rows, including unusable misconfigurations.

        Public routes and consent enforcement use :meth:`published`, not this.
        """
        return tuple(self._versions.values())


def unpublished_catalog() -> LegalPublicationCatalog:
    """Production-shaped empty catalog. No published Terms or Privacy."""
    return LegalPublicationCatalog(())


def catalog_from_settings(settings: object) -> LegalPublicationCatalog:
    """Build a catalog from Settings. Empty version ids stay unpublished."""
    versions: list[PolicyVersion] = []
    terms_version = str(getattr(settings, "legal_terms_published_version_id", "") or "").strip()
    privacy_version = str(getattr(settings, "legal_privacy_published_version_id", "") or "").strip()
    terms_html = str(getattr(settings, "legal_terms_public_html_path", "") or "").strip()
    privacy_html = str(getattr(settings, "legal_privacy_public_html_path", "") or "").strip()
    if terms_version:
        versions.append(
            published_policy(
                policy_type=POLICY_TERMS,
                version_id=terms_version,
                html_path=terms_html,
            )
        )
    if privacy_version:
        versions.append(
            published_policy(
                policy_type=POLICY_PRIVACY,
                version_id=privacy_version,
                html_path=privacy_html,
            )
        )
    return LegalPublicationCatalog(tuple(versions))


def load_approved_public_html(html_path: str) -> str | None:
    """Load public HTML or return None (fail closed).

    Counsel drafts are rejected by path and by content markers so they cannot
    become public HTML through configuration mistakes.
    """
    cleaned = (html_path or "").strip()
    if not cleaned:
        return None
    path = Path(cleaned)
    if not path.is_file():
        return None
    normalized = path.resolve().as_posix().lower()
    if any(fragment in normalized for fragment in _BLOCKED_PATH_FRAGMENTS):
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if looks_like_counsel_draft(content):
        return None
    return content


def looks_like_counsel_draft(content: str) -> bool:
    return any(marker in content for marker in COUNSEL_DRAFT_CONTENT_MARKERS)
