"""Guard: Sprint 16 (Personal Agent) must not modify protected prior-sprint modules."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_knowledge_graph_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

# Inherit all digests protected by Sprint 15 (which inherits 13–14).
PROTECTED_DIGESTS = dict(PRIOR)

# Knowledge Graph core modules that Sprint 16 must not rewrite in place
# (Personal Agent integrates via optional collaborator only).
EXTRA_DIGESTS = {
    "app/services/knowledge_graph_service.py": (
        "be93fc63d0f61013df13b599cf771f6748d0470751a3865146d54ab9a5f961dc"
    ),
    "app/intelligence/knowledge_graph/engine.py": (
        "f6edf85c17e1bdbbb55cc279b0ffeca55ae5e59739390a1a6dbf9610e439420d"
    ),
    "app/intelligence/knowledge_graph/fixtures.py": (
        "79a9cf0bff582e133db804ed42f55536b1e6f08b942e192cead5e0e86e4eaf17"
    ),
    "app/intelligence/knowledge_graph/aggregator.py": (
        "e40e7860798856fa4e26ccb22501a6b84df1b0d4fe288ca7b0c16668339677b2"
    ),
    "app/api/v1/endpoints/graph.py": (
        "c727f60ded6dc4fa56edef0ef59f3f09535de3c1b09da099c97c47c643fee783"
    ),
    "app/domain/entities/knowledge_graph.py": (
        "7679e76d7f4ef0e9ff7996002f68fa746b68cfa0b262111e8b93ae1dfc089064"
    ),
    "app/intelligence/dealscore/engine.py": PRIOR[
        "app/intelligence/dealscore/engine.py"
    ],
    "app/intelligence/recommendation/engine.py": PRIOR[
        "app/intelligence/recommendation/engine.py"
    ],
    "app/intelligence/shopping_assistant/orchestrator.py": PRIOR[
        "app/intelligence/shopping_assistant/orchestrator.py"
    ],
    "app/intelligence/shopping_assistant/deterministic.py": PRIOR[
        "app/intelligence/shopping_assistant/deterministic.py"
    ],
    "app/intelligence/shopping_assistant/evidence.py": PRIOR[
        "app/intelligence/shopping_assistant/evidence.py"
    ],
}

PROTECTED_DIGESTS.update(EXTRA_DIGESTS)


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_personal_agent_service_exists_and_is_independent() -> None:
    service_path = ROOT / "app/services/personal_agent_service.py"
    assert service_path.is_file()
    text = service_path.read_text(encoding="utf-8")
    assert "PersonalAgentService" in text
    lowered = text.lower()
    assert "import openai" not in lowered
    assert "import anthropic" not in lowered
    assert "stripe" not in lowered
    assert "paypal" not in lowered


def test_personal_modules_have_no_auth_or_payment_dependency() -> None:
    personal_dir = ROOT / "app/intelligence/personal"
    for path in sorted(personal_dir.rglob("*.py")):
        lowered = path.read_text(encoding="utf-8").lower()
        assert "import openai" not in lowered, f"{path} imports openai"
        assert "import anthropic" not in lowered, f"{path} imports anthropic"
        assert "stripe" not in lowered, f"{path} references stripe"
        assert "oauth" not in lowered, f"{path} references oauth"


def test_prior_engines_do_not_hard_depend_on_personal_agent() -> None:
    for relative in (
        "app/intelligence/dealscore/engine.py",
        "app/intelligence/recommendation/engine.py",
        "app/intelligence/shopping_assistant/orchestrator.py",
        "app/intelligence/shopping_assistant/deterministic.py",
        "app/intelligence/shopping_assistant/evidence.py",
        "app/services/knowledge_graph_service.py",
        "app/services/community_intelligence_service.py",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert "PersonalAgentService" not in content
        assert "PersonalDealScore" not in content
        assert "from app.intelligence.personal" not in content
        assert "from app.services.personal_agent_service" not in content


def test_shopping_assistant_service_integrates_via_optional_collaborator() -> None:
    text = (ROOT / "app/services/shopping_assistant_service.py").read_text(encoding="utf-8")
    assert "personal_agent_service" in text
    assert "personal_profile_unavailable" in text
