"""Sprint 29 Phase 29.1 conversation-domain contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.shopping_assistant import (
    ConversationContext,
    ConversationOwner,
    ConversationTurn,
    DecisionContextReference,
)
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository

NOW = datetime(2030, 1, 1, tzinfo=UTC)
PIQSCORE_DIGEST = "a" * 64
RECOMMENDATION_DIGEST = "b" * 64


def _owner() -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id="guest-contract-29",
        session_id="session-contract-29",
        expires_at=datetime(2030, 1, 1, 0, 30, tzinfo=UTC),
    )


def _decision_context() -> DecisionContextReference:
    return DecisionContextReference(
        decision_id="00000000-0000-4000-8000-000000000029",
        context_version=1,
        evaluated_product_ids=(
            "apple-iphone-17-pro-max",
            "samsung-galaxy-s25-ultra-512gb",
        ),
        canonical_piqscore_snapshot_sha256=PIQSCORE_DIGEST,
        recommendation_snapshot_sha256=RECOMMENDATION_DIGEST,
        evidence_ids=("fixture-battery-iphone", "fixture-battery-samsung"),
    )


def _turn(number: int) -> ConversationTurn:
    return ConversationTurn(
        role="user",
        intent="comparison",
        product_ids=(
            "apple-iphone-17-pro-max",
            "samsung-galaxy-s25-ultra-512gb",
        ),
        product_names=("iPhone 17 Pro Max", "Samsung Galaxy S25 Ultra 512GB"),
        query=f"Follow-up {number}",
        created_at=NOW,
        turn_id=f"00000000-0000-4000-8000-{number:012d}",
        decision_id="00000000-0000-4000-8000-000000000029",
        context_version=1,
        action="answer_from_evidence",
    )


def test_existing_conversation_architecture_is_extended() -> None:
    """CC-01-01: extend the established entity and repository port in place."""

    repository: ConversationRepository = InMemoryConversationRepository(
        ttl_seconds=600,
        clock=lambda: NOW,
        id_factory=lambda: "conversation-contract-29",
    )
    existing = repository.create()
    context = repository.bind_decision_context(
        existing.conversation_id,
        owner=_owner(),
        decision_context=_decision_context(),
    )

    assert isinstance(context, ConversationContext)
    assert context.conversation_id == "conversation-contract-29"
    assert context.owner == _owner()
    assert context.decision_context == _decision_context()
    assert context.to_dict()["decision_context"]["evaluated_product_ids"] == [
        "apple-iphone-17-pro-max",
        "samsung-galaxy-s25-ultra-512gb",
    ]


def test_active_session_retains_bounded_turn_history() -> None:
    """CC-01-16: retain recent turns without losing the decision binding."""

    repository = InMemoryConversationRepository(
        ttl_seconds=600,
        max_turns=2,
        clock=lambda: NOW,
        id_factory=lambda: "conversation-contract-29",
    )
    created = repository.create(owner=_owner(), decision_context=_decision_context())

    for number in range(1, 4):
        context = repository.append_turn(created.conversation_id, _turn(number))

    assert [turn.query for turn in context.turns] == ["Follow-up 2", "Follow-up 3"]
    assert context.owner == _owner()
    assert context.decision_context == _decision_context()


def test_legacy_conversation_shape_remains_compatible() -> None:
    context = ConversationContext(
        conversation_id="legacy-conversation",
        turns=(),
        expires_at=NOW,
    )
    turn = ConversationTurn(
        role="user",
        intent="general",
        product_ids=(),
        product_names=(),
        query="Legacy follow-up",
        created_at=NOW,
    )

    assert context.owner is None
    assert context.decision_context is None
    assert turn.turn_id is None
    assert turn.action is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("context_version", 0),
        ("evaluated_product_ids", ("duplicate", "duplicate")),
        ("canonical_piqscore_snapshot_sha256", "not-a-sha256"),
    ],
)
def test_decision_context_reference_rejects_invalid_contract_values(
    field: str, value: object
) -> None:
    values: dict[str, object] = {
        "decision_id": "00000000-0000-4000-8000-000000000029",
        "context_version": 1,
        "evaluated_product_ids": ("product-a", "product-b"),
        "canonical_piqscore_snapshot_sha256": PIQSCORE_DIGEST,
        "recommendation_snapshot_sha256": RECOMMENDATION_DIGEST,
        "evidence_ids": ("evidence-a",),
    }
    values[field] = value

    with pytest.raises(ValueError):
        DecisionContextReference(**values)  # type: ignore[arg-type]


def test_repository_rejects_unbounded_configuration() -> None:
    with pytest.raises(ValueError, match="max_turns"):
        InMemoryConversationRepository(max_turns=0)
