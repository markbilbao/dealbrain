"""Legal publication gate for consumer Terms and Privacy documents.

Counsel drafts and working drafts under ``docs/legal/`` are never public HTML.
Empty version ids stay unpublished.
"""

from app.legal.publication import (
    COUNSEL_DRAFT_CONTENT_MARKERS,
    OWNER_AUTHORIZED_PRIVACY_VERSION_ID,
    OWNER_AUTHORIZED_TERMS_VERSION_ID,
    POLICY_PRIVACY,
    POLICY_TERMS,
    LegalPublicationCatalog,
    PolicyVersion,
    catalog_from_settings,
    published_policy,
    unpublished_catalog,
)

__all__ = [
    "COUNSEL_DRAFT_CONTENT_MARKERS",
    "OWNER_AUTHORIZED_PRIVACY_VERSION_ID",
    "OWNER_AUTHORIZED_TERMS_VERSION_ID",
    "POLICY_PRIVACY",
    "POLICY_TERMS",
    "LegalPublicationCatalog",
    "PolicyVersion",
    "catalog_from_settings",
    "published_policy",
    "unpublished_catalog",
]
