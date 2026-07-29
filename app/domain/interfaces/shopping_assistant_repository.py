"""Ports for AI Shopping Assistant conversation and explanation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities.shopping_assistant import (
    ConversationContext,
    ConversationTurn,
    ShoppingAssistantResponse,
)


class ConversationRepository(ABC):
    """Persist minimum safe structured conversation context for a session."""

    @abstractmethod
    def get(self, conversation_id: str) -> ConversationContext | None:
        """Return a non-expired conversation, or None."""

    @abstractmethod
    def save(self, context: ConversationContext) -> ConversationContext:
        """Upsert conversation context."""

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
    ) -> ConversationContext:
        """Append a turn and refresh expiration."""

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove expired conversations; return count removed."""


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
