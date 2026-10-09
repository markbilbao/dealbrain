"""Sprint 40.1: non-decision assistant body fields are lookup hints, not authority."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.consumer.guest_continuity import account_owner_from_session
from app.domain.entities.shopping_assistant import ConversationOwner, ConversationTurn
from app.domain.entities.user_platform import AuthResult
from app.domain.exceptions import (
    DecisionSnapshotOwnershipError,
    ShoppingAssistantNotFoundError,
)
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.profile.service import ProfileService
from app.services.personal_agent_service import PersonalAgentService
from app.services.shopping_assistant_service import ShoppingAssistantService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore

from tests.unit.test_phase_29_4a_answer_from_evidence import (
    START,
    _owner,
    _snapshot,
)

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
COMPARE = "Compare iPhone 17 Pro Max and Samsung Galaxy S25 Ultra for camera and battery"
FOLLOW_UP = "Which one has the better battery?"
GAMING = "What is the best gaming laptop under 60000?"
STUDENT_EMAIL = "student@example.com"
CREATOR_EMAIL = "creator@example.com"


def _guest(principal_id: str) -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id=principal_id,
        session_id=f"session-{principal_id}",
        expires_at=NOW + timedelta(hours=2),
    )


def _account(user_id: str) -> ConversationOwner:
    return ConversationOwner(
        principal_type="account",
        principal_id=user_id,
        session_id=f"session-{user_id}",
        expires_at=NOW + timedelta(hours=2),
    )


def _verified_owner(result: AuthResult) -> ConversationOwner:
    return account_owner_from_session(
        user_id=result.user.user_id,
        session_id=result.session.session_id,
        expires_at=result.session.expires_at,
    )


def _conversations() -> InMemoryConversationRepository:
    return InMemoryConversationRepository(ttl_seconds=600, clock=lambda: NOW)


def _service(
    *,
    conversations: InMemoryConversationRepository | None = None,
    user_platform_service: object | None = None,
    personal_agent_service: object | None = None,
    snapshots: InMemoryDecisionSnapshotRepository | None = None,
    clock=None,
) -> ShoppingAssistantService:
    current = clock or (lambda: NOW)
    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
    )
    return ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=(
            conversations
            if conversations is not None
            else InMemoryConversationRepository(ttl_seconds=600, clock=current)
        ),
        snapshot_repository=snapshots,
        user_platform_service=user_platform_service,
        personal_agent_service=personal_agent_service,
        clock=current,
    )


def _platform() -> tuple[UserPlatformService, InMemoryUserPlatformStore]:
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


def _watch_identity(platform: UserPlatformService) -> tuple[list[str], list[str], list[dict]]:
    loaded: list[str] = []
    written: list[str] = []
    contexts: list[dict] = []
    original_context = platform.shopping_assistant_context
    original_record = platform.record_shopping_recommendation

    def context(user_id: str | None) -> dict:
        loaded.append(str(user_id))
        value = dict(original_context(user_id) or {})
        contexts.append(value)
        return value

    def record(user_id: str | None, **kwargs: object) -> None:
        written.append(str(user_id))
        original_record(user_id, **kwargs)

    platform.shopping_assistant_context = context  # type: ignore[method-assign]
    platform.record_shopping_recommendation = record  # type: ignore[method-assign]
    return loaded, written, contexts


def _record_priors(service: ShoppingAssistantService) -> list[tuple]:
    seen: list[tuple] = []
    original = service._intent_service.parse

    def parse(query: str, **kwargs: object):
        prior = kwargs.get("prior_products") or ()
        seen.append(tuple(prior))  # type: ignore[arg-type]
        return original(query, **kwargs)  # type: ignore[arg-type]

    service._intent_service.parse = parse  # type: ignore[method-assign]
    return seen


def test_foreign_conversation_id_cannot_read_or_append_prior_turns() -> None:
    conversations = _conversations()
    service = _service(conversations=conversations)
    victim = _guest("guest-victim")
    attacker = _guest("guest-attacker")
    priors = _record_priors(service)
    first = service.query({"query": COMPARE}, owner=victim)
    assert first.conversation_id
    stored = conversations.get_for_owner(first.conversation_id, victim)
    assert stored is not None
    before_turns = len(stored.turns)
    before_products = stored.last_product_ids
    assert before_turns == 1
    assert before_products

    attack = service.query(
        {"query": FOLLOW_UP, "conversation_id": first.conversation_id},
        owner=attacker,
    )
    after = conversations.get_for_owner(first.conversation_id, victim)
    assert after is not None
    assert len(after.turns) == before_turns
    assert after.last_product_ids == before_products
    assert after.turns[-1].query == COMPARE
    assert attack.conversation_id != first.conversation_id
    assert priors[-1] == ()
    attacker_row = conversations.get_for_owner(attack.conversation_id, attacker)
    assert attacker_row is not None
    assert attacker_row.owner is not None
    assert attacker_row.owner.has_same_identity(attacker)


def test_verified_owner_continues_own_non_decision_conversation() -> None:
    conversations = _conversations()
    service = _service(conversations=conversations)
    owner = _account("user-owner")
    priors = _record_priors(service)
    first = service.query({"query": COMPARE}, owner=owner)
    second = service.query(
        {"query": FOLLOW_UP, "conversation_id": first.conversation_id},
        owner=owner,
    )
    assert second.conversation_id == first.conversation_id
    assert second.intent == "comparison"
    assert priors[-1]
    stored = conversations.get_for_owner(first.conversation_id, owner)
    assert stored is not None
    assert len(stored.turns) == 2
    assert stored.turns[-1].query == FOLLOW_UP


def test_guest_continues_only_a_conversation_owned_by_that_guest() -> None:
    conversations = _conversations()
    service = _service(conversations=conversations)
    guest = _guest("guest-owner")
    other = _guest("guest-other")
    first = service.query({"query": COMPARE}, owner=guest)
    continued = service.query(
        {"query": FOLLOW_UP, "conversation_id": first.conversation_id},
        owner=guest,
    )
    assert continued.conversation_id == first.conversation_id
    stolen = service.query(
        {
            "query": FOLLOW_UP,
            "conversation_id": first.conversation_id,
            "user_id": "user-student",
        },
        owner=other,
    )
    assert stolen.conversation_id != first.conversation_id
    stored = conversations.get_for_owner(first.conversation_id, guest)
    assert stored is not None
    assert len(stored.turns) == 2
    assert conversations.get_for_owner(first.conversation_id, other) is None


def test_ownerless_and_unknown_client_ids_do_not_adopt_the_row() -> None:
    conversations = _conversations()
    service = _service(conversations=conversations)
    guest = _guest("guest-safe")
    ownerless = conversations.create()
    conversations.append_turn(
        ownerless.conversation_id,
        ConversationTurn(
            role="user",
            intent="comparison",
            product_ids=("victim-product",),
            product_names=("Victim Secret Phone",),
            query="ownerless-secret-turn",
            created_at=NOW,
        ),
        last_intent="comparison",
        last_product_ids=("victim-product",),
        last_product_names=("Victim Secret Phone",),
    )
    priors = _record_priors(service)
    rejected = service.query(
        {"query": FOLLOW_UP, "conversation_id": ownerless.conversation_id},
        owner=guest,
    )
    untouched = conversations.get(ownerless.conversation_id)
    assert untouched is not None
    assert untouched.owner is None
    assert len(untouched.turns) == 1
    assert untouched.turns[0].query == "ownerless-secret-turn"
    assert untouched.last_product_names == ("Victim Secret Phone",)
    assert rejected.conversation_id != ownerless.conversation_id
    assert priors[-1] == ()
    opened = conversations.get_for_owner(rejected.conversation_id, guest)
    assert opened is not None
    assert opened.owner is not None
    assert opened.owner.has_same_identity(guest)

    missing = "client-chosen-conversation"
    fresh = service.query(
        {"query": GAMING, "conversation_id": missing},
        owner=guest,
    )
    assert fresh.conversation_id != missing
    assert conversations.get(missing) is None
    created = conversations.get_for_owner(fresh.conversation_id, guest)
    assert created is not None
    assert created.owner is not None
    assert created.owner.has_same_identity(guest)

    anonymous = service.query(
        {"query": GAMING, "conversation_id": ownerless.conversation_id},
    )
    assert anonymous.conversation_id != ownerless.conversation_id
    assert len(conversations.get(ownerless.conversation_id).turns) == 1  # type: ignore[union-attr]
    anon_row = conversations.get(anonymous.conversation_id)
    assert anon_row is not None
    assert anon_row.owner is None


def test_body_user_id_cannot_load_or_record_another_account() -> None:
    platform, _store = _platform()
    student = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
    creator = platform.login(email=CREATOR_EMAIL, password=DEMO_PASSWORD)
    loaded, written, contexts = _watch_identity(platform)
    service = _service(user_platform_service=platform, clock=lambda: datetime.now(UTC))
    creator_before = platform.list_history(creator.access_token)
    attack_query = "recommend something private for the other account"

    ignored = service.query(
        {
            "query": attack_query,
            "user_id": creator.user.user_id,
            "profile_id": "profile-content-creator",
        }
    )
    assert ignored.processing["authenticated"] is False
    assert ignored.processing["personalization_mode"] == "generic"
    assert creator.user.user_id not in loaded
    assert creator.user.user_id not in written
    assert platform.list_history(creator.access_token) == creator_before
    assert "Demo Creator" not in str(ignored.to_dict())
    assert "Content Creator" not in str(ignored.to_dict())

    student_before = platform.list_history(student.access_token)
    crossed = service.query(
        {
            "query": attack_query,
            "user_id": creator.user.user_id,
            "profile_id": "profile-content-creator",
        },
        owner=_verified_owner(student),
    )
    assert loaded == [student.user.user_id]
    assert written == [student.user.user_id]
    assert contexts[0]["display_name"] == "Demo Student"
    assert contexts[0]["display_name"] != "Demo Creator"
    assert "profile-content-creator" not in str(contexts[0])
    assert platform.list_history(creator.access_token) == creator_before
    assert len(platform.list_history(student.access_token)) == len(student_before) + 1
    assert crossed.processing["authenticated"] is True
    assert "Demo Creator" not in str(crossed.to_dict())
    assert all(item.query != attack_query for item in platform.list_history(creator.access_token))


def test_body_profile_id_personalizes_only_when_bound_to_verified_account() -> None:
    platform, _store = _platform()
    student = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
    personal = PersonalAgentService()
    service = _service(
        user_platform_service=platform,
        personal_agent_service=personal,
        # Guest bindings in this file expire two hours after NOW. The service
        # clock has to stay on that same instant once wall clock passes it.
        clock=lambda: NOW,
    )

    guest_result = service.query(
        {"query": GAMING, "profile_id": "profile-gaming-enthusiast"},
        owner=_guest("guest-unbound"),
    )
    assert guest_result.personal_recommendation is None
    assert guest_result.processing["personalization_mode"] == "generic"
    assert "Gaming Enthusiast" not in str(guest_result.to_dict())

    foreign = service.query(
        {"query": GAMING, "profile_id": "profile-content-creator", "user_id": "user-creator"},
        owner=_verified_owner(student),
    )
    assert foreign.personal_recommendation is not None
    assert foreign.personal_recommendation["profile_id"] == "profile-budget-student"
    assert foreign.profile_id == "profile-budget-student"
    assert "Content Creator" not in str(foreign.to_dict())

    bound = service.query(
        {"query": GAMING, "profile_id": "profile-budget-student"},
        owner=_verified_owner(student),
    )
    assert bound.personal_recommendation is not None
    assert bound.personal_recommendation["profile_id"] == "profile-budget-student"
    assert bound.processing["personalization_mode"] == "personal"


def test_decision_bound_foreign_owner_still_fails_closed() -> None:
    snapshots = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    conversations = InMemoryConversationRepository(clock=lambda: START, ttl_seconds=3600)
    owner_a = _owner("guest-a")
    owner_b = _owner("guest-b")
    snapshot = _snapshot(owner=owner_a)
    snapshots.add(snapshot)
    foreign_conversation = conversations.create(owner=owner_b)
    service = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=lambda: START,
    )

    with pytest.raises((ShoppingAssistantNotFoundError, DecisionSnapshotOwnershipError)):
        service.query(
            {
                "query": "Which one has better battery?",
                "decision_id": snapshot.decision_id,
                "conversation_id": foreign_conversation.conversation_id,
                "user_id": "user-student",
                "profile_id": "profile-budget-student",
            },
            owner=owner_b,
        )
    with pytest.raises((ShoppingAssistantNotFoundError, DecisionSnapshotOwnershipError)):
        service.query(
            {"query": "Which one has better battery?", "decision_id": snapshot.decision_id},
            owner=owner_b,
        )

    stored = conversations.get_for_owner(foreign_conversation.conversation_id, owner_b)
    assert stored is not None
    assert stored.turns == ()
    assert conversations.get(foreign_conversation.conversation_id) is stored


def test_implementation_record_does_not_close_sprint_40() -> None:
    root = Path(__file__).resolve().parents[2]
    record = (
        root / "docs/roadmap/evidence/SPRINT_40_1_BODY_IDENTITY_IMPLEMENTATION_2026-10-09.md"
    ).read_text(encoding="utf-8")
    audit = (
        root / "docs/roadmap/evidence/SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md"
    ).read_text(encoding="utf-8")
    sprint = (root / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md").read_text(
        encoding="utf-8"
    )
    assert "It is not implemented in this change." in audit
    assert "**Status:** Planned" in sprint
    assert "Implemented. Not PROVEN." in record
    assert "Not ENGINEERING COMPLETE" in record
    assert "in-process rate limits only" in record
    assert "CSRF not enforced" in record
    assert "CSP `'unsafe-inline'`" in record
    assert "Dependabot/CodeQL/Trivy/pip-audit" in record
    assert "URL validation / SSRF" in record
    assert "Class C count remains 19" in record
    assert "selected next engineering slice remains NONE" in record
    assert "Sprint 41 stays UNSTARTED" in record
    assert "09757717971ad01077cefbaf806caddf10b8624d" in record
