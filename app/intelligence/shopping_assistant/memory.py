"""In-memory conversation repository with expiration / cleanup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.entities.shopping_assistant import (
    ConversationContext,
    ConversationOwner,
    ConversationTurn,
    DecisionContextReference,
    ShoppingIntentType,
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

    def get(self, conversation_id: str) -> ConversationContext | None:
        self.cleanup_expired()
        context = self._store.get(conversation_id)
        if context is None:
            return None
        if context.expires_at <= self._clock():
            self._store.pop(conversation_id, None)
            return None
        return context

    def save(self, context: ConversationContext) -> ConversationContext:
        if len(context.turns) > self._max_turns:
            context = replace(context, turns=context.turns[-self._max_turns :])
        self._store[context.conversation_id] = context
        return context

    def create(
        self,
        *,
        owner: ConversationOwner | None = None,
        decision_context: DecisionContextReference | None = None,
    ) -> ConversationContext:
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
    ) -> ConversationContext:
        existing = self.get(conversation_id)
        if existing is None:
            raise KeyError(f"conversation not found: {conversation_id}")
        return self.save(
            replace(
                existing,
                owner=owner,
                decision_context=decision_context,
                expires_at=self._clock() + timedelta(seconds=self._ttl_seconds),
            )
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
    ) -> ConversationContext:
        existing = self.get(conversation_id)
        now = self._clock()
        if existing is None:
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
        return self.save(updated)

    def cleanup_expired(self) -> int:
        now = self._clock()
        expired = [key for key, value in self._store.items() if value.expires_at <= now]
        for key in expired:
            del self._store[key]
        return len(expired)
