"""Research Authorization / Execution Handoff Contract.

Creates a server-authoritative confirmation artifact bound to the exact
approved proposal. Does not search, scrape, call connectors, add products,
reprice, or mutate canonical Recommendation / PiqScore.

Live research execution remains unimplemented and owned by Sprints 31–38.
"""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.research_authorization import (
    AUTHORIZATION_VERSION,
    IDEMPOTENCY_KEY_AUTHORITY,
    AuthorizedResearchHandoff,
    FrozenResearchScope,
    ResearchAuthorization,
    ResearchAuthorizationValidation,
)
from app.domain.entities.research_proposal import ResearchProposal
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import ShoppingAssistantNotFoundError, ShoppingAssistantValidationError
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository

SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0", "1.1", "1.2"})
_CLIENT_SCOPE_KEYS = frozenset(
    {
        "requested_sources",
        "outside_set_product_names",
        "requested_evidence_topics",
        "destination_label",
        "expansion_required",
        "freshness_required",
        "research_scope",
        "scope",
        "evaluated_product_ids",
    }
)


def owner_binding_digest(owner: ConversationOwner) -> str:
    """Opaque owner identity digest. Never expose raw principal identifiers."""

    return _stable_sha256(
        {
            "principal_type": owner.principal_type,
            "principal_id": owner.principal_id,
            "session_id": owner.session_id,
        }
    )


def frozen_scope_from_proposal(proposal: ResearchProposal) -> FrozenResearchScope:
    return FrozenResearchScope(
        reason=proposal.reason,
        evaluated_product_ids=proposal.evaluated_product_ids,
        outside_set_product_names=proposal.outside_set_product_names,
        requested_evidence_topics=proposal.requested_evidence_topics,
        requested_sources=proposal.requested_sources,
        destination_label=proposal.destination_label,
        expansion_required=proposal.expansion_required,
        freshness_required=proposal.freshness_required,
        canonical_update_may_be_required=proposal.canonical_update_may_be_required,
    )


def research_scope_digest(
    *,
    decision_id: str,
    canonical_context_version: int,
    proposal_id: str,
    proposal_version: int,
    scope: FrozenResearchScope,
) -> str:
    return _stable_sha256(
        {
            "decision_id": decision_id,
            "canonical_context_version": canonical_context_version,
            "proposal_id": proposal_id,
            "proposal_version": proposal_version,
            "reason": scope.reason,
            **scope.digest_payload(),
        }
    )


def derive_authorization_idempotency_key(
    *,
    owner: ConversationOwner,
    conversation_id: str,
    decision_id: str,
    canonical_context_version: int,
    proposal_id: str,
    proposal_version: int,
    scope_digest: str,
) -> str:
    """Server-derived execution identity.

    A client confirmation token is never execution identity and is never
    enough to select the current proposal. Authorization-producing
    confirmation must also carry the exact server-authored proposal_id and
    proposal_version. Repeated confirmations of the same bound proposal reuse
    this server key even when the client omits or changes a token.
    """

    material = {
        "kind": "research_authorization_v1",
        "authority": IDEMPOTENCY_KEY_AUTHORITY,
        "owner_binding": owner_binding_digest(owner),
        "conversation_id": conversation_id,
        "decision_id": decision_id,
        "canonical_context_version": canonical_context_version,
        "proposal_id": proposal_id,
        "proposal_version": proposal_version,
        "scope_digest": scope_digest,
    }
    digest = _stable_sha256(material)
    return f"research-auth:{digest}"


def create_research_authorization_from_proposal(
    proposal: ResearchProposal,
    *,
    owner: ConversationOwner,
    conversation_id: str,
    now: datetime,
    id_factory=None,  # noqa: ANN001
    existing: tuple[ResearchAuthorization, ...] = (),
    client_confirmation_token: str | None = None,
    schema_version: str | None = None,
) -> ResearchAuthorization:
    """Create or reuse the authorization for this exact pending/confirmed proposal.

    Does not mark the authorization consumed. Consumption belongs to future
    execution. Approved scope is immutable after creation.
    """

    _require_authorizable_proposal(proposal, conversation_id=conversation_id)
    if schema_version is not None and schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ShoppingAssistantValidationError(
            "Research authorization requires a trusted schema 1.0, 1.1, or 1.2 decision."
        )
    _ = client_confirmation_token  # Validated by caller context; never used as execution identity.
    make_id = id_factory or (lambda: str(uuid4()))
    scope = frozen_scope_from_proposal(proposal)
    digest = research_scope_digest(
        decision_id=proposal.decision_id,
        canonical_context_version=proposal.canonical_context_version,
        proposal_id=proposal.proposal_id,
        proposal_version=proposal.proposal_version,
        scope=scope,
    )
    key = derive_authorization_idempotency_key(
        owner=owner,
        conversation_id=conversation_id,
        decision_id=proposal.decision_id,
        canonical_context_version=proposal.canonical_context_version,
        proposal_id=proposal.proposal_id,
        proposal_version=proposal.proposal_version,
        scope_digest=digest,
    )
    matched = _find_by_idempotency(existing, key)
    if matched is not None:
        return matched
    return ResearchAuthorization(
        authorization_id=str(make_id()),
        authorization_version=AUTHORIZATION_VERSION,
        owner_binding=owner_binding_digest(owner),
        conversation_id=conversation_id,
        decision_id=proposal.decision_id,
        canonical_context_version=proposal.canonical_context_version,
        proposal_id=proposal.proposal_id,
        proposal_version=proposal.proposal_version,
        scope=scope,
        scope_digest=digest,
        proposal_reason=proposal.reason,
        evaluated_product_ids=proposal.evaluated_product_ids,
        idempotency_key=key,
        status="authorized_pending_execution",
        created_at=now,
        updated_at=now,
        execution_available=False,
    )


def validate_research_authorization_for_execution(
    authorization: ResearchAuthorization | None,
    *,
    owner: ConversationOwner,
    conversation_id: str,
    decision_id: str,
    canonical_context_version: int,
    proposal: ResearchProposal | None = None,
    expected_scope_digest: str | None = None,
    expected_proposal_id: str | None = None,
    expected_proposal_version: int | None = None,
) -> ResearchAuthorizationValidation:
    """Fail closed if any material binding changed. Does not execute research."""

    if authorization is None:
        return ResearchAuthorizationValidation(valid=False, reason="not_found")
    if authorization.owner_binding != owner_binding_digest(owner):
        raise ShoppingAssistantNotFoundError(authorization.authorization_id)
    if authorization.conversation_id != conversation_id:
        return ResearchAuthorizationValidation(
            valid=False, reason="wrong_conversation", authorization=authorization
        )
    if authorization.decision_id != decision_id:
        return ResearchAuthorizationValidation(
            valid=False, reason="wrong_decision", authorization=authorization
        )
    if authorization.canonical_context_version != canonical_context_version:
        return ResearchAuthorizationValidation(
            valid=False, reason="stale_context_version", authorization=authorization
        )
    if expected_proposal_id and authorization.proposal_id != expected_proposal_id:
        return ResearchAuthorizationValidation(
            valid=False, reason="proposal_id_mismatch", authorization=authorization
        )
    if (
        expected_proposal_version is not None
        and authorization.proposal_version != expected_proposal_version
    ):
        return ResearchAuthorizationValidation(
            valid=False, reason="proposal_version_mismatch", authorization=authorization
        )
    if proposal is not None:
        if proposal.proposal_id != authorization.proposal_id:
            return ResearchAuthorizationValidation(
                valid=False, reason="proposal_id_mismatch", authorization=authorization
            )
        if proposal.proposal_version != authorization.proposal_version:
            return ResearchAuthorizationValidation(
                valid=False, reason="proposal_version_mismatch", authorization=authorization
            )
        current_digest = research_scope_digest(
            decision_id=proposal.decision_id,
            canonical_context_version=proposal.canonical_context_version,
            proposal_id=proposal.proposal_id,
            proposal_version=proposal.proposal_version,
            scope=frozen_scope_from_proposal(proposal),
        )
        if current_digest != authorization.scope_digest:
            return ResearchAuthorizationValidation(
                valid=False, reason="scope_digest_mismatch", authorization=authorization
            )
    if expected_scope_digest and expected_scope_digest != authorization.scope_digest:
        return ResearchAuthorizationValidation(
            valid=False, reason="scope_digest_mismatch", authorization=authorization
        )
    if authorization.status == "cancelled":
        return ResearchAuthorizationValidation(
            valid=False, reason="cancelled", authorization=authorization
        )
    if authorization.status == "invalidated":
        return ResearchAuthorizationValidation(
            valid=False, reason="invalidated", authorization=authorization
        )
    if authorization.status == "consumed":
        return ResearchAuthorizationValidation(
            valid=False, reason="consumed", authorization=authorization
        )
    if authorization.status != "authorized_pending_execution":
        return ResearchAuthorizationValidation(
            valid=False, reason="invalid_status", authorization=authorization
        )
    return ResearchAuthorizationValidation(
        valid=True,
        reason="authorized_pending_execution",
        authorization=authorization,
        execution_available=False,
    )


def get_authorized_research_handoff(
    authorization: ResearchAuthorization | None,
    *,
    owner: ConversationOwner,
    conversation_id: str,
    decision_id: str,
    canonical_context_version: int,
    proposal: ResearchProposal | None = None,
    expected_scope_digest: str | None = None,
) -> AuthorizedResearchHandoff | None:
    """Return the bounded execution packet only when the authorization is valid.

    Does not consume the authorization. Does not start research. The packet
    always reports execution_available=False in this phase.
    """

    result = validate_research_authorization_for_execution(
        authorization,
        owner=owner,
        conversation_id=conversation_id,
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        proposal=proposal,
        expected_scope_digest=expected_scope_digest,
    )
    if not result.valid or result.authorization is None:
        return None
    auth = result.authorization
    return AuthorizedResearchHandoff(
        authorization_id=auth.authorization_id,
        authorization_version=auth.authorization_version,
        conversation_id=auth.conversation_id,
        decision_id=auth.decision_id,
        canonical_context_version=auth.canonical_context_version,
        proposal_id=auth.proposal_id,
        proposal_version=auth.proposal_version,
        scope=auth.scope,
        scope_digest=auth.scope_digest,
        idempotency_key=auth.idempotency_key,
        status=auth.status,
        execution_available=False,
    )


def load_research_authorization_for_owner(
    conversations: ConversationRepository,
    *,
    authorization_id: str,
    owner: ConversationOwner,
    conversation_id: str,
) -> ResearchAuthorization:
    """Owner-bound lookup. Wrong owner and unknown id both look like not found."""

    context = conversations.get_for_owner(conversation_id, owner)
    if context is None:
        raise ShoppingAssistantNotFoundError(conversation_id)
    found = next(
        (
            item
            for item in context.research_authorizations
            if item.authorization_id == authorization_id
        ),
        None,
    )
    if found is None or found.owner_binding != owner_binding_digest(owner):
        raise ShoppingAssistantNotFoundError(authorization_id)
    return found


def cancel_research_authorization(
    authorization: ResearchAuthorization,
    *,
    now: datetime,
) -> ResearchAuthorization:
    """Cancel an unconsumed authorization. Does not execute and does not resurrect."""

    if authorization.status == "consumed":
        return authorization
    if authorization.status == "cancelled":
        return authorization
    return replace(authorization, status="cancelled", updated_at=now, execution_available=False)


def invalidate_research_authorization(
    authorization: ResearchAuthorization,
    *,
    now: datetime,
) -> ResearchAuthorization:
    """Invalidate an unconsumed authorization after a material replacement."""

    if authorization.status in {"consumed", "cancelled", "invalidated"}:
        return authorization
    return replace(authorization, status="invalidated", updated_at=now, execution_available=False)


def mark_research_authorization_consumed(
    authorization: ResearchAuthorization,
    *,
    now: datetime,
) -> ResearchAuthorization:
    """Single-logical-execution helper for future Sprints 31–38.

    Ask confirmation must not call this. Repeated worker retries of the same
    logical run should keep using ``authorization.idempotency_key``.
    """

    if authorization.status != "authorized_pending_execution":
        raise ShoppingAssistantValidationError(
            "Only an authorized_pending_execution authorization can be consumed."
        )
    return replace(authorization, status="consumed", updated_at=now, execution_available=False)


def upsert_authorization(
    existing: tuple[ResearchAuthorization, ...],
    authorization: ResearchAuthorization,
) -> tuple[ResearchAuthorization, ...]:
    replaced = False
    updated: list[ResearchAuthorization] = []
    for item in existing:
        if item.authorization_id == authorization.authorization_id:
            updated.append(authorization)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(authorization)
    return tuple(updated)


def current_unconsumed_authorization(
    existing: tuple[ResearchAuthorization, ...],
) -> ResearchAuthorization | None:
    pending = [item for item in existing if item.status == "authorized_pending_execution"]
    return pending[-1] if pending else None


def ignore_client_scope_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    """Client-supplied scope never widens or replaces the server-authored proposal."""

    return {key: value for key, value in payload.items() if key not in _CLIENT_SCOPE_KEYS}


def _require_authorizable_proposal(
    proposal: ResearchProposal,
    *,
    conversation_id: str,
) -> None:
    if proposal.status in {"cancelled", "replaced"}:
        raise ShoppingAssistantValidationError(
            "A cancelled or replaced research proposal cannot be authorized."
        )
    if proposal.status not in {
        "pending_confirmation",
        "research_confirmation_received_but_execution_unavailable",
    }:
        raise ShoppingAssistantValidationError(
            "Only an explicit confirmation of the active proposal can be authorized."
        )
    if not proposal.proposal_id or not proposal.decision_id:
        raise ShoppingAssistantValidationError(
            "Research authorization requires a trusted proposal identity."
        )
    if proposal.conversation_id and proposal.conversation_id != conversation_id:
        raise ShoppingAssistantValidationError(
            "Research authorization is bound to the owning conversation."
        )
    if not proposal.scope_text.strip() or not proposal.reason:
        raise ShoppingAssistantValidationError(
            "Research authorization cannot be created without a trusted frozen scope."
        )


def _find_by_idempotency(
    existing: tuple[ResearchAuthorization, ...],
    key: str,
) -> ResearchAuthorization | None:
    matches = [item for item in existing if item.idempotency_key == key]
    return matches[-1] if matches else None


def _stable_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
