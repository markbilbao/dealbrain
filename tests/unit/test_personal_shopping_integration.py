"""Unit tests for Personal Agent <-> Shopping Assistant integration."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.shopping_assistant import ConversationOwner
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.services.personal_agent_service import PersonalAgentService
from app.services.shopping_assistant_service import ShoppingAssistantService


def _account(user_id: str) -> ConversationOwner:
    return ConversationOwner(
        principal_type="account",
        principal_id=user_id,
        session_id=f"session-{user_id}",
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )


class _BoundPlatform:
    """Test double: personalization is bound to one verified account user."""

    def __init__(self, bindings: dict[str, str]) -> None:
        self._bindings = bindings

    def shopping_assistant_context(self, user_id: str) -> dict[str, object]:
        profile_id = self._bindings.get(user_id)
        if not profile_id:
            return {"authenticated": False, "personalization_mode": "anonymous"}
        return {
            "authenticated": True,
            "personalization_mode": "authenticated",
            "user_id": user_id,
            "display_name": user_id,
            "personal_profile_id": profile_id,
            "overrides": {"profile_id": profile_id},
            "uses_personal_ai": True,
            "uses_user_profile": True,
        }

    def record_shopping_recommendation(self, user_id: str, **kwargs: object) -> None:
        return None


def make_assistant(
    *,
    personal_agent_service=None,
    user_platform_service=None,
) -> ShoppingAssistantService:
    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
        allow_client_mode=True,
        primary_provider="openai",
        secondary_provider="anthropic",
    )
    return ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=60),
        personal_agent_service=personal_agent_service,
        user_platform_service=user_platform_service,
        clock=lambda: datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
    )


class TestPersonalAvailableIntegration:
    def test_profile_id_returns_personal_recommendation(self) -> None:
        personal = PersonalAgentService()
        assistant = make_assistant(
            personal_agent_service=personal,
            user_platform_service=_BoundPlatform({"user-gamer": "profile-gaming-enthusiast"}),
        )
        result = assistant.query(
            {
                "query": "What is the best gaming laptop under 60000?",
                "profile_id": "profile-gaming-enthusiast",
            },
            owner=_account("user-gamer"),
        )
        assert result.processing["personal_agent_integrated"] is True
        assert result.processing["personalization_mode"] == "personal"
        assert result.personal_recommendation is not None
        assert result.personal_recommendation["profile_id"] == "profile-gaming-enthusiast"
        personal_evidence = [
            item for item in result.evidence if item.source_id == "personal_agent"
        ]
        assert personal_evidence

    def test_without_profile_id_stays_generic(self) -> None:
        personal = PersonalAgentService()
        assistant = make_assistant(personal_agent_service=personal)
        result = assistant.query({"query": "What is the best gaming laptop under 60000?"})
        assert result.processing["personalization_mode"] == "generic"
        assert result.personal_recommendation is None

    def test_profile_switch_changes_personal_payload(self) -> None:
        personal = PersonalAgentService()
        assistant = make_assistant(
            personal_agent_service=personal,
            user_platform_service=_BoundPlatform(
                {
                    "user-gaming": "profile-gaming-enthusiast",
                    "user-apple": "profile-apple-fan",
                }
            ),
        )
        gaming = assistant.query(
            {
                "query": "Recommend a laptop for my needs",
                "profile_id": "profile-gaming-enthusiast",
            },
            owner=_account("user-gaming"),
        )
        apple = assistant.query(
            {
                "query": "Recommend a laptop for my needs",
                "profile_id": "profile-apple-fan",
            },
            owner=_account("user-apple"),
        )
        assert gaming.personal_recommendation is not None
        assert apple.personal_recommendation is not None
        assert (
            gaming.personal_recommendation["profile_id"]
            != apple.personal_recommendation["profile_id"]
        )


class TestPersonalUnavailableFallback:
    def test_none_collaborator_with_profile_warns(self) -> None:
        assistant = make_assistant(
            personal_agent_service=None,
            user_platform_service=_BoundPlatform({"user-gamer": "profile-gaming-enthusiast"}),
        )
        result = assistant.query(
            {
                "query": "Best gaming laptop under 60000",
                "profile_id": "profile-gaming-enthusiast",
            },
            owner=_account("user-gamer"),
        )
        assert any(w.code == "personal_profile_unavailable" for w in result.warnings)
        assert result.processing["personalization_mode"] == "authenticated"
        assert result.answer

    def test_raising_collaborator_degrades_gracefully(self) -> None:
        class _ExplodingPersonal:
            def shopping_assistant_overrides(self, profile_id):
                raise RuntimeError("boom")

            def shopping_assistant_evidence(self, product_ids, profile_id=None):
                raise RuntimeError("boom")

            def shopping_assistant_personalize(self, *, profile_id, product_ids):
                raise RuntimeError("boom")

        assistant = make_assistant(
            personal_agent_service=_ExplodingPersonal(),
            user_platform_service=_BoundPlatform({"user-gamer": "profile-gaming-enthusiast"}),
        )
        result = assistant.query(
            {
                "query": "Best gaming laptop under 60000",
                "profile_id": "profile-gaming-enthusiast",
            },
            owner=_account("user-gamer"),
        )
        assert result.answer
        assert result.top_recommendation is not None
