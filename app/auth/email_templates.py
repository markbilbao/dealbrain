"""Minimal PiqSavi transactional email copy for identity flows."""

from __future__ import annotations

from app.auth.email import EmailMessage
from app.core.public_brand import PUBLIC_BRAND

PASSWORD_RESET_SUBJECT = f"{PUBLIC_BRAND} password reset"
EMAIL_VERIFICATION_SUBJECT = f"Verify your {PUBLIC_BRAND} email"
EMAIL_CHANGE_SUBJECT = f"Confirm your new {PUBLIC_BRAND} email"
EMAIL_CHANGE_NOTICE_SUBJECT = f"Your {PUBLIC_BRAND} account email was changed"

RESET_PATH = "/reset-password"
VERIFY_PATH = "/verify-email"
EMAIL_CHANGE_PATH = "/confirm-email-change"


def build_password_reset_message(
    *,
    to_address: str,
    action_url: str | None,
    expires_hours: int = 1,
) -> EmailMessage:
    purpose = f"You requested a password reset for your {PUBLIC_BRAND} account."
    expiry = f"This link expires in {expires_hours} hour."
    if expires_hours != 1:
        expiry = f"This link expires in {expires_hours} hours."
    if action_url:
        body_text = (
            f"{purpose}\n\n"
            f"Reset your password using this secure link:\n{action_url}\n\n"
            f"{expiry}\n\n"
            "If you did not request this, you can ignore this email.\n"
        )
        body_html = (
            f"<p>{purpose}</p>"
            f'<p><a href="{action_url}">Reset your {PUBLIC_BRAND} password</a></p>'
            f"<p>{expiry}</p>"
            "<p>If you did not request this, you can ignore this email.</p>"
        )
    else:
        body_text = (
            f"{purpose}\n\n"
            f"{expiry}\n\n"
            "Use the PiqSavi password-reset flow to continue. "
            "If you did not request this, you can ignore this email.\n"
        )
        body_html = (
            f"<p>{purpose}</p>"
            f"<p>{expiry}</p>"
            "<p>Use the PiqSavi password-reset flow to continue. "
            "If you did not request this, you can ignore this email.</p>"
        )
    return EmailMessage(
        to_address=to_address,
        subject=PASSWORD_RESET_SUBJECT,
        body_text=body_text,
        body_html=body_html,
        template_id="password_reset",
    )


def build_email_verification_message(
    *,
    to_address: str,
    action_url: str | None,
    expires_hours: int = 24,
) -> EmailMessage:
    purpose = f"Confirm this email address for your {PUBLIC_BRAND} account."
    expiry = f"This link expires in {expires_hours} hours."
    if action_url:
        body_text = (
            f"{purpose}\n\n"
            f"Verify your email using this secure link:\n{action_url}\n\n"
            f"{expiry}\n\n"
            "If you did not create a PiqSavi account, you can ignore this email.\n"
        )
        body_html = (
            f"<p>{purpose}</p>"
            f'<p><a href="{action_url}">Verify your {PUBLIC_BRAND} email</a></p>'
            f"<p>{expiry}</p>"
            "<p>If you did not create a PiqSavi account, you can ignore this email.</p>"
        )
    else:
        body_text = (
            f"{purpose}\n\n"
            f"{expiry}\n\n"
            "Use the PiqSavi email-verification flow to continue. "
            "If you did not create a PiqSavi account, you can ignore this email.\n"
        )
        body_html = (
            f"<p>{purpose}</p>"
            f"<p>{expiry}</p>"
            "<p>Use the PiqSavi email-verification flow to continue. "
            "If you did not create a PiqSavi account, you can ignore this email.</p>"
        )
    return EmailMessage(
        to_address=to_address,
        subject=EMAIL_VERIFICATION_SUBJECT,
        body_text=body_text,
        body_html=body_html,
        template_id="email_verification",
    )


def build_email_change_message(
    *,
    to_address: str,
    action_url: str | None,
    expires_hours: int = 24,
) -> EmailMessage:
    purpose = f"Confirm this new email address for your {PUBLIC_BRAND} account."
    expiry = f"This link expires in {expires_hours} hours."
    if action_url:
        body_text = (
            f"{purpose}\n\n"
            f"Confirm your email change using this secure link:\n{action_url}\n\n"
            f"{expiry}\n\n"
            "If you did not request this change, you can ignore this email.\n"
        )
        body_html = (
            f"<p>{purpose}</p>"
            f'<p><a href="{action_url}">Confirm your new {PUBLIC_BRAND} email</a></p>'
            f"<p>{expiry}</p>"
            "<p>If you did not request this change, you can ignore this email.</p>"
        )
    else:
        body_text = (
            f"{purpose}\n\n"
            f"{expiry}\n\n"
            "Use the PiqSavi email-change flow to continue. "
            "If you did not request this change, you can ignore this email.\n"
        )
        body_html = (
            f"<p>{purpose}</p>"
            f"<p>{expiry}</p>"
            "<p>Use the PiqSavi email-change flow to continue. "
            "If you did not request this change, you can ignore this email.</p>"
        )
    return EmailMessage(
        to_address=to_address,
        subject=EMAIL_CHANGE_SUBJECT,
        body_text=body_text,
        body_html=body_html,
        template_id="email_change",
    )


def build_email_changed_notice(*, to_address: str) -> EmailMessage:
    body_text = (
        f"Your {PUBLIC_BRAND} account email was changed.\n\n"
        "If you did not make this change, contact PiqSavi support immediately.\n"
    )
    body_html = (
        f"<p>Your {PUBLIC_BRAND} account email was changed.</p>"
        "<p>If you did not make this change, contact PiqSavi support immediately.</p>"
    )
    return EmailMessage(
        to_address=to_address,
        subject=EMAIL_CHANGE_NOTICE_SUBJECT,
        body_text=body_text,
        body_html=body_html,
        template_id="email_change_notice",
    )
