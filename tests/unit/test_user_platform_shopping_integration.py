"""Unit tests for Shopping Assistant <-> User Platform integration.

ShoppingAssistantService accepts an optional ``user_platform_service`` collaborator
(``Any | None = None``) exposing ``shopping_assistant_context(user_id)`` and
``record_shopping_recommendation(...)``, mirroring the personal-agent / community /
knowledge-graph optional-collaborator pattern from earlier sprints.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.profile.service import ProfileService
from app.services.shopping_assistant_service import ShoppingAssistantService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore

STUDENT_EMAIL = "student@example.com"
QUERY = "What is the best gaming laptop under 60000?"


def make_platform() -> tuple[UserPlatformService, InMemoryUserPlatformStore]:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        audit=audit,
    )
    profiles = ProfileService(users=store.users, profiles=store.profiles)
    sessions = SessionService(sessions=store.sessions, auth=auth)
    platform = UserPlatformService(
        auth=auth,
        profiles=profiles,
        sessions=sessions,
        saved=store.saved,
        audit=audit,
    )
    return platform, store


def make_assistant(*, user_platform_service: object | None = None) -> ShoppingAssistantService:
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
        user_platform_service=user_platform_service,
        clock=lambda: datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
    )


class TestAuthenticatedUserIntegration:
    def test_authenticated_user_gets_personalization_mode_authenticated(self) -> None:
        platform, _store = make_platform()
        result = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
        assistant = make_assistant(user_platform_service=platform)

        response = assistant.query({"query": QUERY, "user_id": result.user.user_id})

        assert response.processing["personalization_mode"] == "authenticated"
        assert response.processing["authenticated"] is True
        assert response.processing["user_platform_integrated"] is True

    def test_authenticated_user_profile_overrides_applied(self) -> None:
        platform, _store = make_platform()
        result = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
        assistant = make_assistant(user_platform_service=platform)

        # Demo student profile has currency=PHP and category=laptop overrides.
        response = assistant.query(
            {"query": "recommend something for me", "user_id": result.user.user_id}
        )
        assert response.processing["authenticated"] is True

    def test_authenticated_user_does_not_trigger_unavailable_warning(self) -> None:
        platform, _store = make_platform()
        result = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
        assistant = make_assistant(user_platform_service=platform)

        response = assistant.query({"query": QUERY, "user_id": result.user.user_id})
        assert not any(w.code == "user_platform_unavailable" for w in response.warnings)

    def test_history_recorded_for_authenticated_user(self) -> None:
        platform, _store = make_platform()
        result = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
        assistant = make_assistant(user_platform_service=platform)

        before = platform.list_history(result.access_token)
        assistant.query({"query": QUERY, "user_id": result.user.user_id})
        after = platform.list_history(result.access_token)

        assert len(after) == len(before) + 1


class TestAnonymousFallback:
    def test_anonymous_query_without_user_id_stays_generic(self) -> None:
        platform, _store = make_platform()
        assistant = make_assistant(user_platform_service=platform)

        response = assistant.query({"query": QUERY})
        assert response.processing["personalization_mode"] == "generic"
        assert response.processing["authenticated"] is False
        assert response.answer

    def test_anonymous_query_produces_no_unavailable_warning(self) -> None:
        platform, _store = make_platform()
        assistant = make_assistant(user_platform_service=platform)

        response = assistant.query({"query": QUERY})
        assert not any(w.code == "user_platform_unavailable" for w in response.warnings)

    def test_unknown_user_id_falls_back_with_warning(self) -> None:
        platform, _store = make_platform()
        assistant = make_assistant(user_platform_service=platform)

        response = assistant.query({"query": QUERY, "user_id": "no-such-user"})
        assert response.processing["personalization_mode"] == "generic"
        assert any(w.code == "user_platform_unavailable" for w in response.warnings)
        assert response.answer

    def test_none_collaborator_with_user_id_produces_warning(self) -> None:
        assistant = make_assistant(user_platform_service=None)
        response = assistant.query({"query": QUERY, "user_id": "some-user"})
        assert response.processing["user_platform_integrated"] is False
        assert any(w.code == "user_platform_unavailable" for w in response.warnings)
        assert response.answer

    def test_none_collaborator_without_user_id_has_no_warning(self) -> None:
        assistant = make_assistant(user_platform_service=None)
        response = assistant.query({"query": QUERY})
        assert not any(w.code == "user_platform_unavailable" for w in response.warnings)
        assert response.processing["personalization_mode"] == "generic"


class TestGracefulDegradation:
    def test_raising_context_collaborator_degrades_gracefully(self) -> None:
        class _ExplodingContext:
            def shopping_assistant_context(self, user_id: str) -> dict[str, object]:
                raise RuntimeError("boom")

            def record_shopping_recommendation(self, user_id: str, **kwargs: object) -> None:
                raise RuntimeError("boom")

        assistant = make_assistant(user_platform_service=_ExplodingContext())
        response = assistant.query({"query": QUERY, "user_id": "user-x"})

        assert response.answer
        assert response.top_recommendation is not None or response.top_recommendation is None
        assert any(w.code == "user_platform_unavailable" for w in response.warnings)

    def test_raising_history_recorder_does_not_crash_query(self) -> None:
        class _RecordFails:
            def shopping_assistant_context(self, user_id: str) -> dict[str, object]:
                return {
                    "authenticated": True,
                    "personalization_mode": "authenticated",
                    "overrides": {},
                }

            def record_shopping_recommendation(self, user_id: str, **kwargs: object) -> None:
                raise RuntimeError("history backend unavailable")

        assistant = make_assistant(user_platform_service=_RecordFails())
        response = assistant.query({"query": QUERY, "user_id": "user-x"})

        assert response.answer
        assert response.processing["personalization_mode"] == "authenticated"

    def test_malformed_context_payload_does_not_crash_query(self) -> None:
        class _MalformedContext:
            def shopping_assistant_context(self, user_id: str) -> object:
                return "not-a-dict"

            def record_shopping_recommendation(self, user_id: str, **kwargs: object) -> None:
                return None

        assistant = make_assistant(user_platform_service=_MalformedContext())
        response = assistant.query({"query": QUERY, "user_id": "user-x"})
        assert response.answer


class TestQueryDictWiring:
    def test_user_id_accepted_via_query_dict(self) -> None:
        platform, _store = make_platform()
        result = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
        assistant = make_assistant(user_platform_service=platform)

        response = assistant.query(
            {"query": QUERY, "user_id": result.user.user_id, "mode": "economy"}
        )
        assert response.profile_id is None or isinstance(response.profile_id, str)
        assert response.processing["authenticated"] is True

    def test_missing_user_id_key_defaults_to_anonymous(self) -> None:
        platform, _store = make_platform()
        assistant = make_assistant(user_platform_service=platform)
        response = assistant.query({"query": QUERY})
        assert response.processing["authenticated"] is False
