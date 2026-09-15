"""Early Access signup confirmation / receipt email.

This is a receipt that the interest registration already succeeded. It is
not email verification, double opt-in, account activation, or marketing.
"""

from __future__ import annotations

import html
import re

from app.auth.email import EmailMessage
from app.core.public_brand import PUBLIC_BRAND, PUBLIC_TAGLINE

CONFIRMATION_SUBJECT = f"You're on the {PUBLIC_BRAND} Early Access list"
CONFIRMATION_TEMPLATE_ID = "early_access_confirmation"

_BODY_AFTER_GREETING = (
    f"You're officially on the {PUBLIC_BRAND} Early Access list.\n"
    "\n"
    f"We'll let you know when Early Access opens. You may also be invited "
    f"to try {PUBLIC_BRAND} before the wider launch.\n"
    "\n"
    f"{PUBLIC_BRAND} helps you compare buying opportunities, understand the "
    "trade-offs, and make a more informed choice.\n"
    "\n"
    f"{PUBLIC_BRAND} — {PUBLIC_TAGLINE}\n"
    "Buy Smarter.\n"
)

# First token must contain a letter and must not look like an email, URL, or
# numeric handle. Awkward / empty derivations fall back to "Hi there,".
_UNSAFE_NAME_CHARS = re.compile(r"[@/\\<>]")


def greeting_first_name(full_name: str) -> str | None:
    """Return the first usable word from ``full_name``, or ``None``."""
    for token in (full_name or "").split():
        cleaned = token.strip(".,;:!?\"'`()[]{}")
        if not cleaned:
            continue
        if any(ch.isdigit() for ch in cleaned):
            continue
        if _UNSAFE_NAME_CHARS.search(cleaned):
            continue
        if any(ch.isalpha() for ch in cleaned):
            return cleaned
    return None


def build_early_access_confirmation_message(
    *,
    to_address: str,
    full_name: str,
) -> EmailMessage:
    """Build the confirmation receipt for a persisted Early Access signup."""
    first_name = greeting_first_name(full_name)
    greeting = f"Hi {first_name}," if first_name else "Hi there,"
    body_text = f"{greeting}\n\n{_BODY_AFTER_GREETING}"
    safe_greeting = html.escape(greeting)
    body_html = (
        f"<p>{safe_greeting}</p>"
        f"<p>You're officially on the {PUBLIC_BRAND} Early Access list.</p>"
        f"<p>We'll let you know when Early Access opens. You may also be "
        f"invited to try {PUBLIC_BRAND} before the wider launch.</p>"
        f"<p>{PUBLIC_BRAND} helps you compare buying opportunities, understand "
        "the trade-offs, and make a more informed choice.</p>"
        f"<p>{PUBLIC_BRAND} — {PUBLIC_TAGLINE}<br/>Buy Smarter.</p>"
    )
    return EmailMessage(
        to_address=to_address,
        subject=CONFIRMATION_SUBJECT,
        body_text=body_text,
        body_html=body_html,
        template_id=CONFIRMATION_TEMPLATE_ID,
    )
