"""Strict product-analytics event contract.

Schema name: ``piqsavi.product_analytics.v1``.

Unknown event names and unknown properties are rejected. Forbidden fields are
rejected even when empty. This module does not persist events.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

EVENT_SCHEMA = "piqsavi.product_analytics.v1"

EVENT_NAMES: frozenset[str] = frozenset(
    {
        "decision_started",
        "decision_completed",
        "results_viewed",
        "compare_opened",
        "why_opened",
        "outbound_merchant_click",
        "ask_opened",
        "ask_closed",
        "ask_question_submitted",
        "ask_evidence_answered",
        "insufficient_evidence",
        "recommendation_refinement_attempted",
        "recommendation_refinement_applied",
        "research_proposed",
        "research_confirmed",
        "research_declined",
        "research_started",
        "research_partial",
        "research_completed",
        "research_failed",
        "updated_results_viewed",
        "recommendation_helpful",
        "recommendation_not_helpful",
        "incorrect_information_report",
        "bug_report",
        "support_contact",
        "return_visit",
        "repeat_decision",
        "registration_completed",
        "registration_verified",
        "login_success",
        "login_failure",
        "account_deleted",
        "authentication_transition",
    }
)

# Server-owned identity lifecycle names. The browser cannot submit these.
IDENTITY_LIFECYCLE_EVENT_NAMES: frozenset[str] = frozenset(
    {
        "registration_completed",
        "registration_verified",
        "login_success",
        "login_failure",
        "account_deleted",
        "authentication_transition",
    }
)

# Events the browser can truthfully observe in the current UI.
# ``ask_opened`` / ``ask_closed`` are panel open/close only. Every other name
# stays server-owned, including decision, research, and Ask outcomes.
CLIENT_EVENT_NAMES: frozenset[str] = frozenset(
    {
        "results_viewed",
        "compare_opened",
        "why_opened",
        "outbound_merchant_click",
        "ask_opened",
        "ask_closed",
    }
)
SERVER_EVENT_NAMES: frozenset[str] = EVENT_NAMES - CLIENT_EVENT_NAMES
MERCHANT_ACTION_SURFACES: frozenset[str] = frozenset({"results", "compare", "why"})
CLIENT_EVENT_SEMANTICS: dict[str, dict[str, str | frozenset[str]]] = {
    "results_viewed": {
        "surface": "results",
        "action_type": "view",
        "outcome": "viewed",
    },
    "compare_opened": {
        "surface": "compare",
        "action_type": "open",
        "outcome": "opened",
    },
    "why_opened": {
        "surface": "why",
        "action_type": "open",
        "outcome": "opened",
    },
    "outbound_merchant_click": {
        "surface": MERCHANT_ACTION_SURFACES,
        "action_type": "click",
        "outcome": "clicked",
    },
    "ask_opened": {
        "surface": "ask",
        "action_type": "open",
        "outcome": "opened",
    },
    "ask_closed": {
        "surface": "ask",
        "action_type": "close",
        "outcome": "closed",
    },
}
EXACT_CLIENT_FIELDS: dict[str, frozenset[str]] = {
    "ask_opened": frozenset(
        {"event_name", "event_id", "decision_id", "surface", "action_type", "outcome"}
    ),
    "ask_closed": frozenset(
        {"event_name", "event_id", "decision_id", "surface", "action_type", "outcome"}
    ),
}

# Stored properties. ``event_name`` is required even though callers also pass it
# separately. ``content_digest`` is repository integrity material, not a client field.
STORED_PROPERTY_NAMES: frozenset[str] = frozenset(
    {
        "event_schema",
        "event_name",
        "event_id",
        "occurred_at",
        "anonymous_subject_hash",
        "identity_kind",
        "decision_hash",
        "surface",
        "action_type",
        "turn_number",
        "evidence_count",
        "latency_band",
        "freshness_band",
        "error_code",
        "context_version",
        "selected_market",
        "outcome",
        "consent_state",
        "dedup_key",
        "content_digest",
    }
)

CLIENT_EVENT_FIELDS: frozenset[str] = frozenset(
    {
        "event_name",
        "event_id",
        "surface",
        "action_type",
        "turn_number",
        "evidence_count",
        "latency_band",
        "freshness_band",
        "error_code",
        "outcome",
        "decision_id",
    }
)

SERVER_OWNED_FIELDS: frozenset[str] = frozenset(
    {
        "event_schema",
        "occurred_at",
        "anonymous_subject_hash",
        "identity_kind",
        "decision_hash",
        "selected_market",
        "consent_state",
        "dedup_key",
        "content_digest",
        "context_version",
        "user_id",
        "principal_id",
        "owner_id",
        "subject_hash",
    }
)

FORBIDDEN_ANALYTICS_FIELDS: frozenset[str] = frozenset(
    {
        "question",
        "query",
        "raw_question",
        "product_query",
        "free_text",
        "answer",
        "raw_answer",
        "assistant_answer",
        "message",
        "feedback",
        "feedback_text",
        "comment",
        "email",
        "password",
        "access_token",
        "refresh_token",
        "session_token",
        "token",
        "bearer",
        "authorization",
        "cookie",
        "user_id",
        "principal_id",
        "session_id",
        "guest_session_id",
        "conversation_id",
        "ip",
        "ip_address",
        "client_ip",
        "claim",
        "probe",
        "shopify",
        "shopify_payload",
    }
)

SURFACES: frozenset[str] = frozenset({"results", "compare", "why", "ask", "support", "account"})
ACTION_TYPES: frozenset[str] = frozenset(
    {"view", "open", "close", "submit", "click", "report", "start", "complete"}
)
LATENCY_BANDS: frozenset[str] = frozenset(
    {"under_100ms", "under_300ms", "under_1s", "under_3s", "over_3s"}
)
FRESHNESS_BANDS: frozenset[str] = frozenset({"fresh", "recent", "aging", "stale", "unknown"})
OUTCOMES: frozenset[str] = frozenset(
    {
        "viewed",
        "opened",
        "submitted",
        "clicked",
        "helpful",
        "not_helpful",
        "reported",
        "insufficient_evidence",
        "received",
        "incorrect_price",
        "incorrect_product_fact",
        "outdated_offer",
        "misleading_recommendation_evidence",
        "source_issue",
        "bug",
        "other_feedback",
        "closed",
        "started",
        "completed",
        "answered",
        "attempted",
        "applied",
        "proposed",
        "confirmed",
        "declined",
        "failed",
    }
)
IDENTITY_KINDS: frozenset[str] = frozenset({"guest", "authenticated"})
CONSENT_STATES: frozenset[str] = frozenset({"essential_only", "analytics_allowed"})

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MARKET_RE = re.compile(r"^[A-Z]{2}$")
_HASH_RE = re.compile(r"^[a-f0-9]{64}$")

AnalyticsResultStatus = Literal[
    "recorded",
    "duplicate",
    "suppressed_no_consent",
    "schema_rejected",
    "identity_conflict",
]


@dataclass(frozen=True, slots=True)
class AnalyticsWriteResult:
    """Outcome of one analytics write attempt. Not an application log line."""

    status: AnalyticsResultStatus
    event_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProductAnalyticsEvent:
    """One persisted analytics fact. No raw identity and no free text."""

    event_schema: str
    event_name: str
    event_id: str
    occurred_at: datetime
    anonymous_subject_hash: str
    identity_kind: str
    decision_hash: str | None
    surface: str | None
    action_type: str | None
    turn_number: int | None
    evidence_count: int | None
    latency_band: str | None
    freshness_band: str | None
    error_code: str | None
    context_version: int | None
    selected_market: str | None
    outcome: str | None
    consent_state: str
    dedup_key: str
    content_digest: str


def validate_client_event_payload(payload: Any) -> str | None:
    """Return a rejection reason, or None when the client payload is allowed.

    ``decision_id`` may be present so the server can authorize it. It is not an
    analytics property and must be removed before the event is stored.
    """

    if not isinstance(payload, dict):
        return "payload_not_object"
    for key in payload:
        if not isinstance(key, str):
            return "unknown_property"
        normalized = key.strip().lower()
        if normalized in FORBIDDEN_ANALYTICS_FIELDS or key in FORBIDDEN_ANALYTICS_FIELDS:
            return "forbidden_field"
        if key in SERVER_OWNED_FIELDS:
            return "server_owned_field"
        if key not in CLIENT_EVENT_FIELDS:
            return "unknown_property"
    event_name = payload.get("event_name")
    if not isinstance(event_name, str) or event_name not in EVENT_NAMES:
        return "unknown_event"
    if event_name not in CLIENT_EVENT_NAMES:
        return "server_owned_event"
    event_id = payload.get("event_id")
    if event_id is not None and (not isinstance(event_id, str) or not _UUID_RE.match(event_id)):
        return "invalid_event_id"
    decision_id = payload.get("decision_id")
    if decision_id is not None and (
        not isinstance(decision_id, str) or not _UUID_RE.match(decision_id)
    ):
        return "invalid_decision_reference"
    if _choice(payload, "surface", SURFACES):
        return "invalid_surface"
    if _choice(payload, "action_type", ACTION_TYPES):
        return "invalid_action_type"
    if _choice(payload, "latency_band", LATENCY_BANDS):
        return "invalid_latency_band"
    if _choice(payload, "freshness_band", FRESHNESS_BANDS):
        return "invalid_freshness_band"
    if _choice(payload, "outcome", OUTCOMES):
        return "invalid_outcome"
    error_code = payload.get("error_code")
    if error_code is not None and (
        not isinstance(error_code, str) or not _ERROR_CODE_RE.match(error_code)
    ):
        return "invalid_error_code"
    if _bounded_int(payload, "turn_number", 0, 50):
        return "invalid_turn_number"
    if _bounded_int(payload, "evidence_count", 0, 10_000):
        return "invalid_evidence_count"
    semantics = _client_event_semantics(payload)
    if semantics is not None:
        return semantics
    exact = EXACT_CLIENT_FIELDS.get(event_name) if isinstance(event_name, str) else None
    if exact is not None and any(key not in exact for key in payload):
        return "contradictory_event"
    return None


SERVER_EVENT_INPUT_FIELDS: frozenset[str] = CLIENT_EVENT_FIELDS - {"decision_id"}


def validate_server_event_payload(payload: Any) -> str | None:
    """Validate a trusted server emission.

    Server-only names are allowed. The property allow-list, closed vocabularies,
    and free-text rejection still apply. Raw ``decision_id`` is not an input;
    the caller supplies an already-authorized hash through server context.
    """

    if not isinstance(payload, dict):
        return "payload_not_object"
    for key in payload:
        if not isinstance(key, str):
            return "unknown_property"
        normalized = key.strip().lower()
        if normalized in FORBIDDEN_ANALYTICS_FIELDS or key in FORBIDDEN_ANALYTICS_FIELDS:
            return "forbidden_field"
        if key == "decision_id" or key in SERVER_OWNED_FIELDS:
            return "server_owned_field"
        if key not in SERVER_EVENT_INPUT_FIELDS:
            return "unknown_property"
    event_name = payload.get("event_name")
    if not isinstance(event_name, str) or event_name not in EVENT_NAMES:
        return "unknown_event"
    event_id = payload.get("event_id")
    if event_id is not None and (not isinstance(event_id, str) or not _UUID_RE.match(event_id)):
        return "invalid_event_id"
    if _choice(payload, "surface", SURFACES):
        return "invalid_surface"
    if _choice(payload, "action_type", ACTION_TYPES):
        return "invalid_action_type"
    if _choice(payload, "latency_band", LATENCY_BANDS):
        return "invalid_latency_band"
    if _choice(payload, "freshness_band", FRESHNESS_BANDS):
        return "invalid_freshness_band"
    if _choice(payload, "outcome", OUTCOMES):
        return "invalid_outcome"
    error_code = payload.get("error_code")
    if error_code is not None and (
        not isinstance(error_code, str) or not _ERROR_CODE_RE.match(error_code)
    ):
        return "invalid_error_code"
    if _bounded_int(payload, "turn_number", 0, 50):
        return "invalid_turn_number"
    if _bounded_int(payload, "evidence_count", 0, 10_000):
        return "invalid_evidence_count"
    return None


def _client_event_semantics(payload: dict[str, Any]) -> str | None:
    event_name = payload.get("event_name")
    rule = CLIENT_EVENT_SEMANTICS.get(event_name) if isinstance(event_name, str) else None
    if rule is None:
        return "contradictory_event"
    for key, expected in rule.items():
        actual = payload.get(key)
        if isinstance(expected, frozenset):
            if actual not in expected:
                return "contradictory_event"
        elif actual != expected:
            return "contradictory_event"
    return None


def semantic_digest(event: ProductAnalyticsEvent) -> str:
    """Digest of immutable event contents. Timestamps are not part of identity."""

    material = {
        "event_schema": event.event_schema,
        "event_name": event.event_name,
        "anonymous_subject_hash": event.anonymous_subject_hash,
        "identity_kind": event.identity_kind,
        "decision_hash": event.decision_hash,
        "surface": event.surface,
        "action_type": event.action_type,
        "turn_number": event.turn_number,
        "evidence_count": event.evidence_count,
        "latency_band": event.latency_band,
        "freshness_band": event.freshness_band,
        "error_code": event.error_code,
        "context_version": event.context_version,
        "selected_market": event.selected_market,
        "outcome": event.outcome,
        "consent_state": event.consent_state,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def assert_stored_event_shape(event: ProductAnalyticsEvent) -> None:
    """Fail closed if a built event leaves the allow-list."""

    if event.event_schema != EVENT_SCHEMA:
        raise ValueError("event schema mismatch")
    if event.event_name not in EVENT_NAMES:
        raise ValueError("event name is not allow-listed")
    if event.identity_kind not in IDENTITY_KINDS:
        raise ValueError("identity kind is not allow-listed")
    if event.consent_state not in CONSENT_STATES:
        raise ValueError("consent state is not allow-listed")
    if not _HASH_RE.match(event.anonymous_subject_hash):
        raise ValueError("analytics subject hash is not opaque")
    if event.decision_hash is not None and not _HASH_RE.match(event.decision_hash):
        raise ValueError("decision hash is not opaque")
    if event.selected_market is not None and not _MARKET_RE.match(event.selected_market):
        raise ValueError("selected market is not an ISO country code")
    if event.content_digest != semantic_digest(event):
        raise ValueError("content digest does not match event contents")


def _choice(payload: dict[str, Any], key: str, allowed: frozenset[str]) -> bool:
    value = payload.get(key)
    if value is None:
        return False
    return not isinstance(value, str) or value not in allowed


def _bounded_int(payload: dict[str, Any], key: str, low: int, high: int) -> bool:
    value = payload.get(key)
    if value is None:
        return False
    if isinstance(value, bool) or not isinstance(value, int):
        return True
    return value < low or value > high
