"""In-memory conversation repository with expiration / cleanup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import uuid4

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

DEFAULT_TTL_SECONDS = 30 * 60
MAX_TURNS = 12


class InMemoryConversationRepository(ConversationRepository):
    """Process-scoped conversation store (no secrets / prompts retained)."""

    def __init__(
        self,
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
        self._ttl_seconds = ttl_seconds
        self._max_turns = max_turns
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._store: dict[str, ConversationContext] = {}
        self._lock = RLock()

    def get(self, conversation_id: str) -> ConversationContext | None:
        with self._lock:
            context = self._store.get(conversation_id)
            if context is None:
                return None
            if self._is_expired(context):
                self._store.pop(conversation_id, None)
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
        with self._lock:
            self._require_active_owner(context.conversation_id, context.owner)
            existing = self._store.get(context.conversation_id)
            if existing is not None and self._is_expired(existing):
                self._store.pop(context.conversation_id, None)
                existing = None
            require_stable_decision_context(existing, context)
            expected = context.persistence_version if expected_version is None else expected_version
            if existing is None:
                if expected != 0:
                    raise ConversationVersionConflictError(context.conversation_id, expected)
                next_version = 1
            else:
                if expected != existing.persistence_version:
                    raise ConversationVersionConflictError(context.conversation_id, expected)
                if existing.owner is not None and (
                    context.owner is None or not existing.owner.has_same_identity(context.owner)
                ):
                    raise ConversationOwnershipError(
                        context.conversation_id,
                        "owner changes require explicit rebind",
                    )
                next_version = existing.persistence_version + 1
            stored = replace(
                context,
                turns=context.turns[-self._max_turns :],
                persistence_version=next_version,
            )
            self._store[context.conversation_id] = stored
            return stored

    def create(
        self,
        *,
        owner: ConversationOwner | None = None,
        decision_context: DecisionContextReference | None = None,
    ) -> ConversationContext:
        with self._lock:
            now = self._clock()
            context = ConversationContext(
                conversation_id=self._id_factory(),
                turns=(),
                expires_at=now + timedelta(seconds=self._ttl_seconds),
                owner=owner,
                decision_context=decision_context,
            )
            return self.save(context)

    def bind_decision_context(
        self,
        conversation_id: str,
        *,
        owner: ConversationOwner,
        decision_context: DecisionContextReference,
        expected_version: int | None = None,
    ) -> ConversationContext:
        with self._lock:
            self._require_active_owner(conversation_id, owner)
            existing = self.get(conversation_id)
            if existing is None:
                raise KeyError(f"conversation not found: {conversation_id}")
            if existing.owner is not None and not existing.owner.has_same_identity(owner):
                raise ConversationOwnershipError(conversation_id, "owner identity mismatch")
            if (
                existing.decision_context is not None
                and existing.decision_context != decision_context
            ):
                raise ConversationContextDriftError(
                    conversation_id,
                    "bound decision context cannot be replaced without explicit research",
                )
            return self.save(
                replace(
                    existing,
                    owner=owner,
                    decision_context=decision_context,
                    last_product_ids=decision_context.evaluated_product_ids,
                    expires_at=self._clock() + timedelta(seconds=self._ttl_seconds),
                ),
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
        with self._lock:
            self._require_active_owner(conversation_id, new_owner)
            existing = self.get(conversation_id)
            if existing is None:
                raise KeyError(f"conversation not found: {conversation_id}")
            if existing.owner is None or not existing.owner.has_same_identity(current_owner):
                raise ConversationOwnershipError(conversation_id, "current owner identity mismatch")
            expected = (
                existing.persistence_version if expected_version is None else expected_version
            )
            if expected != existing.persistence_version:
                raise ConversationVersionConflictError(conversation_id, expected)
            rebound = replace(
                existing,
                owner=new_owner,
                expires_at=self._clock() + timedelta(seconds=self._ttl_seconds),
                persistence_version=existing.persistence_version + 1,
            )
            self._store[conversation_id] = rebound
            return rebound

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
        with self._lock:
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

            turns = (*(existing.turns), turn)[-self._max_turns :]
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
                turns=turns,
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

    def cleanup_expired(self, *, limit: int = 100) -> int:
        with self._lock:
            if limit <= 0:
                return 0
            expired = [key for key, value in self._store.items() if self._is_expired(value)][:limit]
            for key in expired:
                del self._store[key]
            return len(expired)

    def find_bound_for_owner(
        self,
        owner: ConversationOwner,
        decision_id: str,
    ) -> ConversationContext | None:
        with self._lock:
            matches: list[ConversationContext] = []
            for context in self._store.values():
                if self._is_expired(context):
                    continue
                if context.owner is None or not context.owner.has_same_identity(owner):
                    continue
                if context.decision_context is None:
                    continue
                if context.decision_context.decision_id != decision_id:
                    continue
                matches.append(context)
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
