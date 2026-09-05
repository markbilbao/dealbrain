"""Legal publication gate for consumer Terms and Privacy documents.

Production has no published policy versions. Counsel drafts under ``docs/legal/``
are never public HTML.
"""

from app.legal.publication import (
    COUNSEL_DRAFT_CONTENT_MARKERS,
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
    "POLICY_PRIVACY",
    "POLICY_TERMS",
    "LegalPublicationCatalog",
    "PolicyVersion",
    "catalog_from_settings",
    "published_policy",
    "unpublished_catalog",
]
