"""Idempotency for one ordinary shopping-assistant submission.

``POST /api/v1/shopping-assistant/query`` can append a conversation turn,
write recommendation history, create or replace a research proposal, persist
a session refinement, and then emit Ask analytics. Conversation compare-and-swap
does not cover that whole POST. A retry is identified by the client
``Idempotency-Key`` header, scoped to the verified request authority, and
bound to a digest of the mutation-relevant payload.

The raw key, owner cookie, bearer token, email, password, and client IP are
not stored. Staging and production use the shared PostgreSQL table. Development
and tests may use the in-memory store. There is no silent fallback to memory.

No approved retention period for this ledger exists in
``docs/privacy/ENGINEERING_RETENTION.md``. The beta default keeps a completed
or indeterminate row for 24 hours (``SUBMISSION_RETENTION_SECONDS``). A
processing row is not a lease: retention cleanup does not delete it, and an
expired processing horizon seals the row to indeterminate without running the
submission again.

``service.query`` is the mutation boundary. An exception from that call is
indeterminate, because the method can write before it raises and a crash can
leave those writes behind. The claim is released only when execution never
started.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from app.consumer.location import DeliveryContext
from app.core.config import Settings, settings
from app.domain.entities.shopping_assistant import ConversationOwner
from app.launch.client_ip import client_host_for_rate_limit
from app.launch.rate_limit_backend import resolve_rate_limit_backend
from app.launch.rate_limit_keys import opaque_subject_key
from app.market.selection import SelectedShoppingMarket
from starlette.requests import Request

HEADER_NAME = "Idempotency-Key"
DETAIL_REQUIRED = "Idempotency-Key is required."
DETAIL_INVALID = "Idempotency-Key is invalid."
DETAIL_CONFLICT = "Idempotency-Key does not match the original request."
DETAIL_IN_PROGRESS = "Request already in progress."
DETAIL_INDETERMINATE = "Request outcome is indeterminate."
DETAIL_UNAVAILABLE = "Shopping assistant submission store is unavailable."

# Beta default. No approved shopping-submission retention period was found.
SUBMISSION_RETENTION_SECONDS = 24 * 60 * 60
# Fail-closed seal horizon. This does not authorize a second execution.
PROCESSING_HORIZON_SECONDS = 15 * 60
MAX_RESPONSE_CHARS = 262_144
_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")

Outcome = Literal["execute", "replay", "in_progress", "conflict", "indeterminate"]
State = Literal["processing", "completed", "indeterminate"]


class ShoppingSubmissionUnavailable(Exception):
    """The replay ledger could not be evaluated. Callers must not execute."""


class SubmissionIdentityError(Exception):
    """The Idempotency-Key header is missing or malformed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class SubmissionClaim:
    """Result of an atomic claim. ``response_json`` is set only for a replay."""

    outcome: Outcome
    response_json: str | None = None


@dataclass(frozen=True, slots=True)
class SubmissionRecord:
    """One durable row. Identity material is already opaque."""

    scope: str
    key_hash: str
    fingerprint: str
    state: State
    response_body: str | None
    http_status: int | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class SubmissionApplyResult:
    """Public outcome of one gated submission."""

    outcome: Literal["completed", "replay", "in_progress", "conflict", "indeterminate"]
    response_json: str | None
    fresh: bool


class ShoppingSubmissionStore(Protocol):
    """Atomic replay ledger. ``claim`` must have a single winner."""

    def claim(
        self,
        *,
        scope: str,
        key_hash: str,
        fingerprint: str,
        now: datetime,
    ) -> SubmissionClaim: ...

    def complete(
        self,
        *,
        scope: str,
        key_hash: str,
        fingerprint: str,
        response_json: str,
        now: datetime,
    ) -> bool: ...

    def fail_closed(
        self,
        *,
        scope: str,
        key_hash: str,
        now: datetime,
    ) -> None: ...

    def release_unentered(
        self,
        *,
        scope: str,
        key_hash: str,
    ) -> bool: ...

    def cleanup(self, now: datetime) -> int: ...

    def seal_stale_processing(self, now: datetime) -> int: ...

    def read(self, *, scope: str, key_hash: str) -> SubmissionRecord | None: ...


def parse_submission_key(raw: str | None) -> str:
    """Accept one bounded key. Do not invent a key when the header is absent."""

    if raw is None or not raw.strip():
        raise SubmissionIdentityError(DETAIL_REQUIRED)
    key = raw.strip()
    if "," in raw or not _KEY_RE.fullmatch(key):
        raise SubmissionIdentityError(DETAIL_INVALID)
    return key


def submission_key_hash(key: str) -> str:
    """SHA-256 of the client key. The raw key is not stored."""

    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def aware_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def epoch_ms(now: datetime) -> int:
    return int(aware_utc(now).timestamp() * 1000)


def from_epoch_ms(millis: int) -> datetime:
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=millis)


def _blank_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _canonical_number(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def request_fingerprint(
    payload: dict[str, object],
    *,
    scope: str,
    location: DeliveryContext | None,
    selected_market: SelectedShoppingMarket | None,
) -> str:
    """Digest the mutation-relevant input. Body user and profile ids are omitted.

    Those fields are not request authority and do not change processing when
    they disagree with the verified account. Conversation, decision, proposal,
    and market values do change which row the POST mutates, so they are part
    of the digest. The digest is not the raw question.
    """

    delivery = location or DeliveryContext()
    market = selected_market.country_code if selected_market is not None else None
    document = {
        "authority_scope": scope,
        "budget_max": _canonical_number(payload.get("budget_max")),
        "budget_min": _canonical_number(payload.get("budget_min")),
        "category": _blank_none(payload.get("category")),
        "confirmation_token": _blank_none(payload.get("confirmation_token")),
        "context_version": _canonical_number(payload.get("context_version")),
        "conversation_id": _blank_none(payload.get("conversation_id")),
        "currency": _blank_none(payload.get("currency")),
        "decision_id": _blank_none(payload.get("decision_id")),
        "delivery": {
            "city": delivery.city,
            "postal_code": delivery.postal_code,
            "skipped": bool(delivery.skipped),
            "source": delivery.source,
        },
        "mode": payload.get("mode"),
        "products": _string_list(payload.get("products")),
        "proposal_id": _blank_none(payload.get("proposal_id")),
        "proposal_version": _canonical_number(payload.get("proposal_version")),
        "query": str(payload.get("query") or "").strip(),
        "selected_market": market,
        "surface": payload.get("surface"),
        "use_cases": _string_list(payload.get("use_cases")),
    }
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _anonymous_host(request: Request) -> str:
    from app.core.config import settings as app_settings

    peer = request.client.host if request.client is not None else None
    forwarded = request.headers.get("x-forwarded-for") or ""
    return client_host_for_rate_limit(
        peer=peer,
        forwarded_for=forwarded,
        trusted_proxy_cidrs=list(app_settings.trusted_proxy_cidrs),
    )


def submission_authority_scope(
    owner: ConversationOwner | None,
    request: Request,
    *,
    secret: bytes | None = None,
) -> str:
    """HMAC scope for the strongest verified subject.

    Account and guest scopes use the verified owner. Anonymous Ask, which the
    merged contract still allows for a non-decision question, uses an HMAC of
    the trusted client host. The host is not stored. Body identity fields are
    not read.
    """

    try:
        if isinstance(owner, ConversationOwner) and owner.principal_type == "account":
            principal = owner.principal_id.strip()
            if principal:
                return opaque_subject_key("ask-acct", principal, secret=secret)
        if isinstance(owner, ConversationOwner) and owner.principal_type == "guest":
            principal = owner.principal_id.strip()
            session_id = owner.session_id.strip()
            if principal and session_id:
                material = principal + "\n" + session_id
                return opaque_subject_key("ask-guest", material, secret=secret)
        return opaque_subject_key("ask-anon", _anonymous_host(request), secret=secret)
    except Exception as exc:
        raise ShoppingSubmissionUnavailable(DETAIL_UNAVAILABLE) from exc


def _require_opaque_parts(*, scope: str, key_hash: str, fingerprint: str) -> None:
    if (
        not scope
        or len(scope) > 128
        or "@" in scope
        or any(character.isspace() for character in scope)
        or not _HEX_64.fullmatch(key_hash)
        or not _HEX_64.fullmatch(fingerprint)
    ):
        raise ShoppingSubmissionUnavailable(DETAIL_UNAVAILABLE)


def _interpret(record: SubmissionRecord, fingerprint: str, now: datetime) -> SubmissionClaim:
    if record.fingerprint != fingerprint:
        return SubmissionClaim("conflict")
    current = epoch_ms(now)
    if record.state == "completed" and epoch_ms(record.expires_at) > current:
        if record.response_body:
            return SubmissionClaim("replay", response_json=record.response_body)
        return SubmissionClaim("indeterminate")
    if record.state == "processing":
        return SubmissionClaim("in_progress")
    if record.state == "indeterminate" and epoch_ms(record.expires_at) > current:
        return SubmissionClaim("indeterminate")
    return SubmissionClaim("indeterminate")


class InMemoryShoppingSubmissionStore:
    """Process-local ledger for development and unit tests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[tuple[str, str], SubmissionRecord] = {}

    def claim(
        self,
        *,
        scope: str,
        key_hash: str,
        fingerprint: str,
        now: datetime,
    ) -> SubmissionClaim:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint=fingerprint)
        current = aware_utc(now)
        with self._lock:
            self._seal_unlocked(current)
            self._purge_unlocked(current)
            existing = self._rows.get((scope, key_hash))
            if existing is None:
                self._rows[(scope, key_hash)] = _processing_record(
                    scope=scope,
                    key_hash=key_hash,
                    fingerprint=fingerprint,
                    now=current,
                )
                return SubmissionClaim("execute")
            if existing.state != "processing" and epoch_ms(existing.expires_at) <= epoch_ms(
                current
            ):
                self._rows.pop((scope, key_hash), None)
                self._rows[(scope, key_hash)] = _processing_record(
                    scope=scope,
                    key_hash=key_hash,
                    fingerprint=fingerprint,
                    now=current,
                )
                return SubmissionClaim("execute")
            return _interpret(existing, fingerprint, current)

    def complete(
        self,
        *,
        scope: str,
        key_hash: str,
        fingerprint: str,
        response_json: str,
        now: datetime,
    ) -> bool:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint=fingerprint)
        if len(response_json) > MAX_RESPONSE_CHARS:
            self.fail_closed(scope=scope, key_hash=key_hash, now=now)
            return False
        current = aware_utc(now)
        with self._lock:
            existing = self._rows.get((scope, key_hash))
            if (
                existing is None
                or existing.state != "processing"
                or existing.fingerprint != fingerprint
            ):
                return False
            self._rows[(scope, key_hash)] = SubmissionRecord(
                scope=scope,
                key_hash=key_hash,
                fingerprint=fingerprint,
                state="completed",
                response_body=response_json,
                http_status=200,
                created_at=existing.created_at,
                updated_at=current,
                expires_at=current + timedelta(seconds=SUBMISSION_RETENTION_SECONDS),
            )
            return True

    def fail_closed(self, *, scope: str, key_hash: str, now: datetime) -> None:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint="0" * 64)
        current = aware_utc(now)
        with self._lock:
            existing = self._rows.get((scope, key_hash))
            if existing is None or existing.state != "processing":
                return
            self._rows[(scope, key_hash)] = SubmissionRecord(
                scope=scope,
                key_hash=key_hash,
                fingerprint=existing.fingerprint,
                state="indeterminate",
                response_body=None,
                http_status=None,
                created_at=existing.created_at,
                updated_at=current,
                expires_at=current + timedelta(seconds=SUBMISSION_RETENTION_SECONDS),
            )

    def release_unentered(self, *, scope: str, key_hash: str) -> bool:
        """Drop a processing claim that has not entered ``service.query``."""

        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint="0" * 64)
        with self._lock:
            existing = self._rows.get((scope, key_hash))
            if existing is None or existing.state != "processing":
                return False
            del self._rows[(scope, key_hash)]
            return True

    def cleanup(self, now: datetime) -> int:
        """Delete expired completed and indeterminate rows. Keep processing rows."""

        current = aware_utc(now)
        with self._lock:
            return self._purge_unlocked(current)

    def seal_stale_processing(self, now: datetime) -> int:
        """Mark an abandoned processing row indeterminate. Do not re-execute it."""

        current = aware_utc(now)
        with self._lock:
            return self._seal_unlocked(current)

    def read(self, *, scope: str, key_hash: str) -> SubmissionRecord | None:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint="0" * 64)
        with self._lock:
            return self._rows.get((scope, key_hash))

    def _purge_unlocked(self, now: datetime) -> int:
        current = epoch_ms(now)
        expired = [
            key
            for key, row in self._rows.items()
            if row.state != "processing" and epoch_ms(row.expires_at) <= current
        ]
        for key in expired:
            del self._rows[key]
        return len(expired)

    def _seal_unlocked(self, now: datetime) -> int:
        current = epoch_ms(now)
        sealed = 0
        for key, row in list(self._rows.items()):
            if row.state != "processing" or epoch_ms(row.expires_at) > current:
                continue
            self._rows[key] = SubmissionRecord(
                scope=row.scope,
                key_hash=row.key_hash,
                fingerprint=row.fingerprint,
                state="indeterminate",
                response_body=None,
                http_status=None,
                created_at=row.created_at,
                updated_at=now,
                expires_at=now + timedelta(seconds=SUBMISSION_RETENTION_SECONDS),
            )
            sealed += 1
        return sealed


def _processing_record(
    *,
    scope: str,
    key_hash: str,
    fingerprint: str,
    now: datetime,
) -> SubmissionRecord:
    return SubmissionRecord(
        scope=scope,
        key_hash=key_hash,
        fingerprint=fingerprint,
        state="processing",
        response_body=None,
        http_status=None,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(seconds=PROCESSING_HORIZON_SECONDS),
    )


class ShoppingSubmissionLedger:
    """Policy facade over a store. The store supplies the atomic claim."""

    def __init__(self, store: ShoppingSubmissionStore) -> None:
        self._store = store

    @property
    def store(self) -> ShoppingSubmissionStore:
        return self._store

    def begin(
        self,
        *,
        scope: str,
        key: str,
        fingerprint: str,
        now: datetime,
    ) -> SubmissionClaim:
        return self._store.claim(
            scope=scope,
            key_hash=submission_key_hash(key),
            fingerprint=fingerprint,
            now=now,
        )

    def complete(
        self,
        *,
        scope: str,
        key: str,
        fingerprint: str,
        response_json: str,
        now: datetime,
    ) -> bool:
        return self._store.complete(
            scope=scope,
            key_hash=submission_key_hash(key),
            fingerprint=fingerprint,
            response_json=response_json,
            now=now,
        )

    def fail_closed(self, *, scope: str, key: str, now: datetime) -> None:
        self._store.fail_closed(scope=scope, key_hash=submission_key_hash(key), now=now)

    def release_unentered(self, *, scope: str, key: str) -> bool:
        return self._store.release_unentered(scope=scope, key_hash=submission_key_hash(key))

    def cleanup(self, now: datetime) -> int:
        return self._store.cleanup(now)

    def read(self, *, scope: str, key: str) -> SubmissionRecord | None:
        return self._store.read(scope=scope, key_hash=submission_key_hash(key))


def apply_shopping_submission(
    ledger: ShoppingSubmissionLedger,
    *,
    scope: str,
    key: str,
    fingerprint: str,
    execute: Callable[[], str],
    now: datetime,
) -> SubmissionApplyResult:
    """Run ``execute`` only for the atomic winner.

    ``execute`` is the mutation boundary. It must call ``service.query`` and
    return the public response JSON. Any exception from ``execute`` is sealed
    as indeterminate and re-raised. The processing claim is not released,
    because ``service.query`` may already have written.
    """

    claim = ledger.begin(scope=scope, key=key, fingerprint=fingerprint, now=now)
    if claim.outcome == "replay":
        return SubmissionApplyResult("replay", claim.response_json, fresh=False)
    if claim.outcome == "in_progress":
        return SubmissionApplyResult("in_progress", None, fresh=False)
    if claim.outcome == "conflict":
        return SubmissionApplyResult("conflict", None, fresh=False)
    if claim.outcome == "indeterminate":
        return SubmissionApplyResult("indeterminate", None, fresh=False)
    try:
        response_json = execute()
    except Exception:
        with suppress(ShoppingSubmissionUnavailable):
            ledger.fail_closed(scope=scope, key=key, now=now)
        raise
    try:
        stored = ledger.complete(
            scope=scope,
            key=key,
            fingerprint=fingerprint,
            response_json=response_json,
            now=now,
        )
    except ShoppingSubmissionUnavailable:
        stored = False
    if not stored:
        with suppress(ShoppingSubmissionUnavailable):
            ledger.fail_closed(scope=scope, key=key, now=now)
    return SubmissionApplyResult("completed", response_json, fresh=True)


def build_shopping_submission_store(cfg: Settings | None = None) -> ShoppingSubmissionStore:
    """Select the ledger backend. Staging and production cannot use memory."""

    cfg = cfg or settings
    backend = resolve_rate_limit_backend(cfg)
    if backend == "memory":
        return InMemoryShoppingSubmissionStore()
    from app.infrastructure.database.shopping_submission_store import (
        SqlShoppingSubmissionStore,
    )

    return SqlShoppingSubmissionStore()


def build_shopping_submission_ledger(cfg: Settings | None = None) -> ShoppingSubmissionLedger:
    return ShoppingSubmissionLedger(build_shopping_submission_store(cfg))
