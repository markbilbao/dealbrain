"""Feedback report contract. Not an analytics event payload."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

FEEDBACK_CATEGORIES: frozenset[str] = frozenset(
    {
        "recommendation_helpful",
        "recommendation_not_helpful",
        "incorrect_price",
        "incorrect_product_fact",
        "outdated_offer",
        "misleading_recommendation_evidence",
        "source_issue",
        "bug",
        "other_feedback",
    }
)

MESSAGE_OPTIONAL_CATEGORIES: frozenset[str] = frozenset(
    {
        "recommendation_helpful",
        "recommendation_not_helpful",
    }
)

ANALYTICS_EVENT_FOR_CATEGORY: dict[str, str] = {
    "recommendation_helpful": "recommendation_helpful",
    "recommendation_not_helpful": "recommendation_not_helpful",
    "incorrect_price": "incorrect_information_report",
    "incorrect_product_fact": "incorrect_information_report",
    "outdated_offer": "incorrect_information_report",
    "misleading_recommendation_evidence": "incorrect_information_report",
    "source_issue": "incorrect_information_report",
    "bug": "bug_report",
}

REPORT_SURFACES: frozenset[str] = frozenset(
    {"results", "compare", "why", "ask", "support", "account"}
)
MAX_REPORT_MESSAGE_LENGTH = 2000
REPORT_STATUS_RECEIVED = "received"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_PRODUCT_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SECRET_RE = re.compile(
    r"(?i)bearer\s+|access_token|refresh_token|session_token|piqsavi_access_token"
)


class FeedbackRejected(Exception):
    """Closed feedback validation failure. ``code`` is not the user's message."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FeedbackConflict(Exception):
    """The same submission id was reused with different contents."""


@dataclass(frozen=True, slots=True)
class FeedbackCommand:
    category: str
    message: str
    decision_id: str | None
    product_id: str | None
    source_surface: str | None
    context_version: int | None
    client_submission_id: str | None


@dataclass(frozen=True, slots=True)
class FeedbackReport:
    report_id: str
    category: str
    created_at: datetime
    owner_digest: str | None
    decision_id: str | None
    product_id: str | None
    context_version: int | None
    message: str
    status: str
    source_surface: str | None
    client_submission_id: str | None
    content_digest: str


def parse_feedback_command(payload: Any) -> FeedbackCommand:
    """Validate a feedback body. Does not authorize a decision or product."""

    if not isinstance(payload, dict):
        raise FeedbackRejected("payload_not_object")
    allowed = {
        "category",
        "message",
        "decision_id",
        "product_id",
        "surface",
        "context_version",
        "client_submission_id",
    }
    if any(key not in allowed for key in payload):
        raise FeedbackRejected("unknown_field")
    category = payload.get("category")
    if not isinstance(category, str) or category not in FEEDBACK_CATEGORIES:
        raise FeedbackRejected("invalid_category")
    message = payload.get("message", "")
    if message is None:
        message = ""
    if not isinstance(message, str):
        raise FeedbackRejected("invalid_message")
    message = message.strip()
    if len(message) > MAX_REPORT_MESSAGE_LENGTH:
        raise FeedbackRejected("message_too_long")
    if category not in MESSAGE_OPTIONAL_CATEGORIES and not message:
        raise FeedbackRejected("message_required")
    if "<" in message or ">" in message:
        raise FeedbackRejected("html_not_allowed")
    if _SECRET_RE.search(message):
        raise FeedbackRejected("secret_not_allowed")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in message):
        raise FeedbackRejected("invalid_message")
    decision_id = _optional_uuid(payload.get("decision_id"), "invalid_decision_reference")
    product_id = payload.get("product_id")
    if product_id is not None and (
        not isinstance(product_id, str) or not _PRODUCT_RE.match(product_id)
    ):
        raise FeedbackRejected("invalid_product")
    surface = payload.get("surface")
    if surface is not None and (not isinstance(surface, str) or surface not in REPORT_SURFACES):
        raise FeedbackRejected("invalid_surface")
    context_version = payload.get("context_version")
    if context_version is not None and (
        isinstance(context_version, bool)
        or not isinstance(context_version, int)
        or context_version < 1
        or context_version > 100_000
    ):
        raise FeedbackRejected("invalid_context_version")
    submission = _optional_uuid(payload.get("client_submission_id"), "invalid_submission_id")
    if product_id and not decision_id:
        raise FeedbackRejected("product_not_in_decision")
    return FeedbackCommand(
        category=category,
        message=message,
        decision_id=decision_id,
        product_id=product_id if isinstance(product_id, str) else None,
        source_surface=surface if isinstance(surface, str) else None,
        context_version=context_version if isinstance(context_version, int) else None,
        client_submission_id=submission,
    )


def feedback_content_digest(report: FeedbackReport) -> str:
    material = {
        "category": report.category,
        "message": report.message,
        "decision_id": report.decision_id,
        "product_id": report.product_id,
        "context_version": report.context_version,
        "source_surface": report.source_surface,
        "owner_digest": report.owner_digest,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _optional_uuid(value: Any, code: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not _UUID_RE.match(value):
        raise FeedbackRejected(code)
    return value.lower()
