"""Safe template rendering for notification templates — Sprint 19.

Uses a minimal ``{{field}}`` placeholder syntax resolved via regex
substitution against a plain mapping of known values. Deliberately avoids
``str.format``/``eval``/``exec`` and never grants templates attribute or
index access into arbitrary Python objects — only whitelisted top-level
context keys are ever substituted. HTML output is escaped with
``html.escape`` to prevent injection when a rendered body is displayed as
HTML (e.g. in a digest email preview).
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from typing import Any

from app.domain.entities.notifications import NotificationTemplate

_PLACEHOLDER_RE = re.compile(r"\{\{\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def render_template(
    template: str,
    context: Mapping[str, Any],
    *,
    escape_html: bool = False,
) -> str:
    """Substitute ``{{name}}`` placeholders in ``template`` from ``context``.

    Unknown placeholders resolve to an empty string rather than raising, so a
    stored template referencing a field a caller forgot to supply degrades
    gracefully instead of failing notification delivery. When
    ``escape_html`` is True, substituted values are passed through
    :func:`html.escape` (the literal template text around placeholders is
    never escaped, since it is authored content, not user input).
    """

    def _replace(match: re.Match[str]) -> str:
        text = _stringify(context.get(match.group("name")))
        return html.escape(text) if escape_html else text

    return _PLACEHOLDER_RE.sub(_replace, template)


def render_subject_and_body(
    template: NotificationTemplate,
    context: Mapping[str, Any],
    *,
    escape_html: bool = False,
) -> tuple[str, str]:
    """Render both ``subject_template`` and ``body_template`` for ``template``."""
    subject = render_template(template.subject_template, context, escape_html=escape_html)
    body = render_template(template.body_template, context, escape_html=escape_html)
    return subject, body


def render_plain_text(template_text: str, context: Mapping[str, Any]) -> str:
    """Render a plain-text (non-HTML) notification body — no escaping applied."""
    return render_template(template_text, context, escape_html=False)


def render_html(template_text: str, context: Mapping[str, Any]) -> str:
    """Render an HTML notification body with all substituted values escaped."""
    return render_template(template_text, context, escape_html=True)
