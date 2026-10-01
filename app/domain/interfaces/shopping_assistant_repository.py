"""Ports for AI Shopping Assistant conversation and explanation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.entities.shopping_assistant import (
    ConversationContext,
    ConversationOwner,
    ConversationTurn,
    DecisionContextReference,
    ShoppingAssistantResponse,
)


class ConversationRepository(ABC):
    """Persist minimum safe structured conversation context for a session."""

    @abstractmethod
    def create(
        self,
        *,
        owner: ConversationOwner | None = None,
        decision_context: DecisionContextReference | None = None,
    ) -> ConversationContext:
        """Create a conversation, optionally bound to an owned decision snapshot."""

    @abstractmethod
    def get(self, conversation_id: str) -> ConversationContext | None:
        """Return a non-expired conversation, or None."""

    @abstractmethod
    def get_for_owner(
        self,
        conversation_id: str,
        owner: ConversationOwner,
    ) -> ConversationContext | None:
        """Return an active conversation only when its owner identity matches."""

    @abstractmethod
    def save(
        self,
        context: ConversationContext,
        *,
        expected_version: int | None = None,
    ) -> ConversationContext:
        """Create or compare-and-swap a conversation context."""

    @abstractmethod
    def bind_decision_context(
        self,
        conversation_id: str,
        *,
        owner: ConversationOwner,
        decision_context: DecisionContextReference,
        expected_version: int | None = None,
    ) -> ConversationContext:
        """Bind an existing conversation to one owned canonical decision snapshot."""

    @abstractmethod
    def advance_verified_research_context(
        self,
        conversation_id: str,
        *,
        owner: ConversationOwner,
        decision_context: DecisionContextReference,
        expected_version: int | None = None,
    ) -> ConversationContext:
        """Move one bound decision to the next repository-verified context version.

        The owner, decision id, evaluated set, PiqScore digest, and
        Recommendation digest stay put. Prior turns stay on the conversation.
        """

    @abstractmethod
    def rebind_owner(
        self,
        conversation_id: str,
        *,
        current_owner: ConversationOwner,
        new_owner: ConversationOwner,
        expected_version: int | None = None,
    ) -> ConversationContext:
        """Explicitly transfer an active conversation between owner identities."""

    @abstractmethod
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
        """Append a turn and refresh expiration."""

    @abstractmethod
    def cleanup_expired(self, *, limit: int = 100) -> int:
        """Remove at most ``limit`` expired conversations; return count removed."""

    @abstractmethod
    def find_bound_for_owner(
        self,
        owner: ConversationOwner,
        decision_id: str,
    ) -> ConversationContext | None:
        """Return the latest active conversation bound to this owner and decision."""

    @abstractmethod
    def consume_research_authorization(
        self,
        conversation_id: str,
        *,
        owner: ConversationOwner,
        authorization_id: str,
        authorization_version: int,
        decision_id: str,
        canonical_context_version: int,
        proposal_id: str,
        proposal_version: int,
        scope_digest: str,
        idempotency_key: str,
        expected_version: int,
        now: datetime,
    ) -> ConversationContext:
        """Consume one exact pending authorization and compare-and-swap the row.

        Owner binding, conversation membership, stable decision context, and
        ``persistence_version`` compare-and-swap stay in ``save``. This does
        not consume a different authorization and does not increment
        ``authorization_version``.
        """


class ShoppingExplanationProvider(ABC):
    """Provider-neutral port for narrative explanation over structured evidence.

    Deterministic numeric ranking must already be complete before calling this
    port. Providers must not invent prices, ratings, or marketplace facts.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider identifier (e.g. deterministic, openai)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model identifier (or deterministic-mock-v1)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can serve a request under current config."""

    @abstractmethod
    def explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return explanation fields: answer, reason snippets, status, etc."""


class ShoppingAssistantResponder(ABC):
    """Legacy-compatible responder port used by deterministic fallback."""

    @abstractmethod
    def respond(self, payload: dict[str, Any]) -> ShoppingAssistantResponse:
        """Build a full assistant response from a structured payload."""
