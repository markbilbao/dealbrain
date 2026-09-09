"""Approved public PiqSavi contact identities for privacy/support surfaces.

Do not invent additional public legal addresses. ``legal@piqsavi.com`` remains a
planned brand-policy address and is not claimed as a provisioned live mailbox.
"""

from __future__ import annotations

from app.core.public_brand import PUBLIC_PRIVACY_EMAIL, PUBLIC_SUPPORT_EMAIL


def support_contact_email() -> str:
    return PUBLIC_SUPPORT_EMAIL


def privacy_contact_email() -> str:
    return PUBLIC_PRIVACY_EMAIL


def public_contact_snapshot() -> dict[str, str]:
    return {
        "support_contact": support_contact_email(),
        "privacy_contact": privacy_contact_email(),
    }
