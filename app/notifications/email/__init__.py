"""Simulated email notification provider and renderer — Sprint 19."""

from app.notifications.email.provider import (
    SIMULATED_EMAIL_MARKER,
    EmailMessage,
    EmailNotificationProvider,
    EmailSendResult,
    MockEmailNotificationProvider,
)
from app.notifications.email.renderer import (
    render_html,
    render_plain_text,
    render_subject_and_body,
    render_template,
)

__all__ = [
    "SIMULATED_EMAIL_MARKER",
    "EmailMessage",
    "EmailNotificationProvider",
    "EmailSendResult",
    "MockEmailNotificationProvider",
    "render_html",
    "render_plain_text",
    "render_subject_and_body",
    "render_template",
]
