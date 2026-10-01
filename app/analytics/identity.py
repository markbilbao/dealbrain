"""Opaque analytics identity. Raw owner identifiers are not analytics keys."""

from __future__ import annotations

import hashlib
import re
import secrets

from app.domain.entities.shopping_assistant import ConversationOwner

_SUBJECT_RE = re.compile(r"^[a-f0-9]{32}$")
_DECISION_PREFIX = "piqsavi.decision_analytics.v1:"
_SUBJECT_PREFIX = "piqsavi.analytics_subject.v1:"


def new_analytics_subject_id() -> str:
    """Random opaque browser subject. Call only after analytics opt-in."""

    return secrets.token_hex(16)


def is_analytics_subject_id(value: str | None) -> bool:
    return bool(value and _SUBJECT_RE.match(value))


def anonymous_subject_hash(subject_id: str) -> str:
    """One-way hash of the opt-in subject cookie. The raw id is not stored."""

    if not is_analytics_subject_id(subject_id):
        raise ValueError("analytics subject id is not opaque")
    return hashlib.sha256(f"{_SUBJECT_PREFIX}{subject_id}".encode()).hexdigest()


def decision_hash(decision_id: str) -> str:
    """One-way hash of a server-validated decision id."""

    return hashlib.sha256(f"{_DECISION_PREFIX}{decision_id}".encode()).hexdigest()


def identity_kind_for_owner(owner: ConversationOwner | None) -> str:
    """Guest unless the request has an authorized account principal.

    The raw principal id and session id are not returned.
    """

    if owner is not None and owner.principal_type == "account":
        return "authenticated"
    return "guest"
