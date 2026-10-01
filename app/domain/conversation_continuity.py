"""Shared invariants for conversations bound to canonical decision snapshots."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import ConversationContext
from app.domain.exceptions import ConversationContextDriftError


def require_stable_decision_context(
    existing: ConversationContext | None,
    updated: ConversationContext,
) -> None:
    """Reject replacement of an already-bound canonical decision reference."""

    if (
        existing is not None
        and existing.decision_context is not None
        and updated.decision_context != existing.decision_context
    ):
        raise ConversationContextDriftError(
            updated.conversation_id,
            "bound decision identity, version, evaluated set, or digests changed",
        )
    require_context_membership(updated)


def require_verified_research_context_advance(
    existing: ConversationContext,
    updated: ConversationContext,
) -> None:
    """Allow one repository-verified newer version of the same decision.

    Generic saves still use :func:`require_stable_decision_context`. This check
    is only for a successful research integration. It keeps the owner, decision,
    evaluated set, PiqScore digest, and Recommendation digest, and moves the
    reference forward by exactly one server-assigned version.
    """

    previous = existing.decision_context
    nxt = updated.decision_context
    if previous is None or nxt is None:
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance requires an existing bound decision",
        )
    if existing.owner is None or updated.owner is None:
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance requires an owner",
        )
    if not existing.owner.has_same_identity(updated.owner):
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance cannot change the conversation owner",
        )
    if previous.decision_id != nxt.decision_id:
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance cannot change the decision",
        )
    if nxt.context_version != previous.context_version + 1:
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance must move to the next context version",
        )
    if previous.evaluated_product_ids != nxt.evaluated_product_ids:
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance cannot change the evaluated product set",
        )
    if previous.canonical_piqscore_snapshot_sha256 != nxt.canonical_piqscore_snapshot_sha256:
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance cannot change the canonical PiqScore digest",
        )
    if previous.recommendation_snapshot_sha256 != nxt.recommendation_snapshot_sha256:
        raise ConversationContextDriftError(
            updated.conversation_id,
            "research advance cannot change the Recommendation digest",
        )
    require_context_membership(updated)


def require_context_membership(context: ConversationContext) -> None:
    """Ensure structured turn state never escapes the bound evaluated set.

    Turns recorded against an earlier context version of the same decision
    remain valid after a research advance. A turn cannot name another decision
    or a version newer than the bound snapshot.
    """

    reference = context.decision_context
    if reference is None:
        return
    allowed_products = set(reference.evaluated_product_ids)
    unexpected_last_products = set(context.last_product_ids) - allowed_products
    if unexpected_last_products:
        raise ConversationContextDriftError(
            context.conversation_id,
            "last product state contains a product outside the canonical evaluated set",
        )
    for turn in context.turns:
        if turn.decision_id not in {None, reference.decision_id}:
            raise ConversationContextDriftError(
                context.conversation_id,
                "turn decision_id does not match the canonical decision",
            )
        version = turn.context_version
        if version is not None and (version < 1 or version > reference.context_version):
            raise ConversationContextDriftError(
                context.conversation_id,
                "turn context_version does not match the canonical decision",
            )
        if set(turn.product_ids) - allowed_products:
            raise ConversationContextDriftError(
                context.conversation_id,
                "turn contains a product outside the canonical evaluated set",
            )
