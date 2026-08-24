"""Durable Sprint 29 conversation repository on ``operational_entities``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.domain.conversation_continuity import (
    require_context_membership,
    require_stable_decision_context,
)
from app.domain.entities.shopping_assistant import (
    ConversationContext,
    ConversationOwner,
    ConversationTurn,
    DecisionContextReference,
    ShoppingIntentType,
)
from app.domain.exceptions import (
    ConversationContextDriftError,
    ConversationOwnershipError,
    ConversationVersionConflictError,
)
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.infrastructure.persistence.errors import (
    PersistenceConflictError,
    PersistenceSchemaError,
)
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import SHOPPING_CONVERSATIONS

DEFAULT_TTL_SECONDS = 30 * 60
MAX_TURNS = 12


class SqlAlchemyConversationRepository(ConversationRepository, SessionBound):
    """Owner-bound durable conversations with row-version compare-and-swap.

    ``OperationalEntityModel.seq`` is used as the per-conversation row version
    for this store only. This preserves the approved zero-DDL architecture.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        session: Session | None = None,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_turns: int = MAX_TURNS,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        SessionBound.__init__(self, session_factory=session_factory, session=session)
        self._ttl_seconds = ttl_seconds
        self._max_turns = max_turns
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def create(
        self,
        *,
        owner: ConversationOwner | None = None,
        decision_context: DecisionContextReference | None = None,
    ) -> ConversationContext:
        now = self._clock()
        return self.save(
            ConversationContext(
                conversation_id=self._id_factory(),
                turns=(),
                expires_at=now + timedelta(seconds=self._ttl_seconds),
                owner=owner,
                decision_context=decision_context,
            )
        )

    def get(self, conversation_id: str) -> ConversationContext | None:
        with self._ops() as ops:
            loaded = ops.get_versioned(
                SHOPPING_CONVERSATIONS,
                conversation_id,
                ConversationContext,
            )
            if loaded is None:
                return None
            context, row_version, _ = loaded
            self._require_version_integrity(context, row_version)
            if self._is_expired(context):
                ops.delete_versioned(
                    SHOPPING_CONVERSATIONS,
                    conversation_id,
                    expected_version=row_version,
                )
                return None
            return context

    def get_for_owner(
        self,
        conversation_id: str,
        owner: ConversationOwner,
    ) -> ConversationContext | None:
        context = self.get(conversation_id)
        if context is None or context.owner is None:
            return None
        if not context.owner.has_same_identity(owner):
            return None
        return context

    def save(
        self,
        context: ConversationContext,
        *,
        expected_version: int | None = None,
    ) -> ConversationContext:
        self._require_active_owner(context.conversation_id, context.owner)
        bounded = replace(context, turns=context.turns[-self._max_turns :])
        require_context_membership(bounded)
        expected = context.persistence_version if expected_version is None else expected_version
        with self._ops() as ops:
            loaded = ops.get_versioned(
                SHOPPING_CONVERSATIONS,
                context.conversation_id,
                ConversationContext,
            )
            if loaded is None:
                if expected != 0:
                    raise ConversationVersionConflictError(context.conversation_id, expected)
                stored = replace(bounded, persistence_version=1)
                try:
                    return ops.insert_versioned(
                        SHOPPING_CONVERSATIONS,
                        context.conversation_id,
                        stored,
                        version=1,
                        owner_id=self._owner_key(stored.owner),
                    )
                except PersistenceConflictError as exc:
                    raise ConversationVersionConflictError(
                        context.conversation_id,
                        expected,
                    ) from exc

            existing, row_version, _ = loaded
            self._require_version_integrity(existing, row_version)
            self._require_unchanged_owner(existing, bounded)
            require_stable_decision_context(existing, bounded)
            return self._compare_and_swap(
                ops,
                bounded,
                expected_version=expected,
            )

    def bind_decision_context(
        self,
        conversation_id: str,
        *,
        owner: ConversationOwner,
        decision_context: DecisionContextReference,
        expected_version: int | None = None,
    ) -> ConversationContext:
        self._require_active_owner(conversation_id, owner)
        existing = self.get(conversation_id)
        if existing is None:
            raise KeyError(f"conversation not found: {conversation_id}")
        if existing.owner is not None and not existing.owner.has_same_identity(owner):
            raise ConversationOwnershipError(conversation_id, "owner identity mismatch")
        if existing.decision_context is not None and existing.decision_context != decision_context:
            raise ConversationContextDriftError(
                conversation_id,
                "bound decision context cannot be replaced without explicit research",
            )
        updated = replace(
            existing,
            owner=owner,
            decision_context=decision_context,
            last_product_ids=decision_context.evaluated_product_ids,
            expires_at=self._clock() + timedelta(seconds=self._ttl_seconds),
        )
        require_context_membership(updated)
        return self._save_known_owner_transition(
            updated,
            expected_version=(
                existing.persistence_version if expected_version is None else expected_version
            ),
        )

    def rebind_owner(
        self,
        conversation_id: str,
        *,
        current_owner: ConversationOwner,
        new_owner: ConversationOwner,
        expected_version: int | None = None,
    ) -> ConversationContext:
        self._require_active_owner(conversation_id, new_owner)
        existing = self.get(conversation_id)
        if existing is None:
            raise KeyError(f"conversation not found: {conversation_id}")
        if existing.owner is None or not existing.owner.has_same_identity(current_owner):
            raise ConversationOwnershipError(conversation_id, "current owner identity mismatch")
        rebound = replace(
            existing,
            owner=new_owner,
            expires_at=self._clock() + timedelta(seconds=self._ttl_seconds),
        )
        return self._save_known_owner_transition(
            rebound,
            expected_version=(
                existing.persistence_version if expected_version is None else expected_version
            ),
        )

    def append_turn(
        self,
        conversation_id: str,
        turn: ConversationTurn,
        *,
        last_intent: str | None = None,
        last_product_ids: tuple[str, ...] = (),
        last_product_names: tuple[str, ...] = (),
        last_category: str | None = None,
        expected_version: int | None = None,
    ) -> ConversationContext:
        existing = self.get(conversation_id)
        now = self._clock()
        if existing is None:
            if expected_version is not None:
                raise ConversationVersionConflictError(conversation_id, expected_version)
            existing = ConversationContext(
                conversation_id=conversation_id or self._id_factory(),
                turns=(),
                expires_at=now + timedelta(seconds=self._ttl_seconds),
            )

        intent_value: ShoppingIntentType | None = None
        if last_intent in {
            "recommendation",
            "comparison",
            "worth_buying",
            "best_offer",
            "complaints",
            "buy_now_or_wait",
            "use_case",
            "seller_trust",
            "general",
        }:
            intent_value = last_intent  # type: ignore[assignment]
        elif existing.last_intent is not None:
            intent_value = existing.last_intent

        updated = replace(
            existing,
            turns=(*(existing.turns), turn)[-self._max_turns :],
            expires_at=now + timedelta(seconds=self._ttl_seconds),
            last_intent=intent_value,
            last_product_ids=last_product_ids or existing.last_product_ids,
            last_product_names=last_product_names or existing.last_product_names,
            last_category=last_category or existing.last_category,
        )
        require_context_membership(updated)
        return self.save(
            updated,
            expected_version=(
                existing.persistence_version if expected_version is None else expected_version
            ),
        )

    def find_bound_for_owner(
        self,
        owner: ConversationOwner,
        decision_id: str,
    ) -> ConversationContext | None:
        owner_key = self._owner_key(owner)
        with self._ops() as ops:
            matches = ops.list(
                SHOPPING_CONVERSATIONS,
                ConversationContext,
                owner_id=owner_key,
                predicate=lambda context: (
                    not self._is_expired(context)
                    and context.decision_context is not None
                    and context.decision_context.decision_id == decision_id
                    and context.owner is not None
                    and context.owner.has_same_identity(owner)
                ),
            )
        if not matches:
            return None
        matches.sort(
            key=lambda item: (
                item.session_refinement.refinement_version
                if item.session_refinement is not None
                else 0,
                item.persistence_version,
            )
        )
        return matches[-1]

    def cleanup_expired(self, *, limit: int = 100) -> int:
        if limit <= 0:
            return 0
        with self._ops() as ops:
            expired = ops.list(
                SHOPPING_CONVERSATIONS,
                ConversationContext,
                limit=limit,
                predicate=self._is_expired,
            )
            removed = 0
            for context in expired:
                if ops.delete_versioned(
                    SHOPPING_CONVERSATIONS,
                    context.conversation_id,
                    expected_version=context.persistence_version,
                ):
                    removed += 1
            return removed

    def _save_known_owner_transition(
        self,
        context: ConversationContext,
        *,
        expected_version: int,
    ) -> ConversationContext:
        with self._ops() as ops:
            return self._compare_and_swap(
                ops,
                context,
                expected_version=expected_version,
            )

    def _compare_and_swap(
        self,
        ops: OperationalStore,
        context: ConversationContext,
        *,
        expected_version: int,
    ) -> ConversationContext:
        next_version = expected_version + 1
        stored = replace(
            context,
            turns=context.turns[-self._max_turns :],
            persistence_version=next_version,
        )
        updated = ops.compare_and_swap(
            SHOPPING_CONVERSATIONS,
            context.conversation_id,
            stored,
            expected_version=expected_version,
            new_version=next_version,
            owner_id=self._owner_key(stored.owner),
        )
        if not updated:
            raise ConversationVersionConflictError(context.conversation_id, expected_version)
        return stored

    def _is_expired(self, context: ConversationContext) -> bool:
        now = self._clock()
        return context.expires_at <= now or (
            context.owner is not None and context.owner.expires_at <= now
        )

    def _require_active_owner(
        self,
        conversation_id: str,
        owner: ConversationOwner | None,
    ) -> None:
        if owner is not None and owner.expires_at <= self._clock():
            raise ConversationOwnershipError(conversation_id, "owner binding is expired")

    @staticmethod
    def _require_unchanged_owner(
        existing: ConversationContext,
        updated: ConversationContext,
    ) -> None:
        if existing.owner is not None and (
            updated.owner is None or not existing.owner.has_same_identity(updated.owner)
        ):
            raise ConversationOwnershipError(
                existing.conversation_id,
                "owner changes require explicit rebind",
            )

    @staticmethod
    def _require_version_integrity(context: ConversationContext, row_version: int) -> None:
        if context.persistence_version != row_version:
            raise PersistenceSchemaError(
                f"conversation {context.conversation_id} payload/row version mismatch"
            )

    @staticmethod
    def _owner_key(owner: ConversationOwner | None) -> str | None:
        if owner is None:
            return None
        material = "\0".join((owner.principal_type, owner.principal_id, owner.session_id)).encode()
        return f"{owner.principal_type}:{sha256(material).hexdigest()}"
