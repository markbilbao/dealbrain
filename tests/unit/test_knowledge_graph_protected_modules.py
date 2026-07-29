"""Guard: Sprint 15 (Knowledge Graph) must not modify protected prior-sprint modules."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_community_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

# Inherit all digests protected by Sprint 14 (which itself inherits Sprint 13).
PROTECTED_DIGESTS = dict(PRIOR)

# Community Intelligence core modules that Sprint 15 must not rewrite in place
# (Knowledge Graph integrates via a read-only adapter / optional collaborator only).
EXTRA_DIGESTS = {
    "app/services/community_intelligence_service.py": (
        "e5f0dab5c815c2dad4b868bea4bbcc817a63fed55b74093cea3944978f4b7f5d"
    ),
    "app/intelligence/community/orchestrator.py": (
        "a4a4c196bfd274f1f41a365b05a515cc941056d4debdcc52917cb9e21fa2da17"
    ),
    "app/intelligence/community/collector.py": (
        "0ed5ef1fc8a9939f612f4a5946a1d13bdc37125c639cfa04c174961eac069769"
    ),
    "app/intelligence/community/fixtures.py": (
        "76849da63cabc03bc6501200f1fe666df63ea428c16f53812b9c77904b491d07"
    ),
    "app/intelligence/community/trust.py": (
        "68829279d0d467f73101b1c5b7be122ebc4963dff2829cd567f6c1cdf6306239"
    ),
    "app/intelligence/community/deterministic.py": (
        "2cf9396783cb62dcf0fe6b0bc3f88a1f540c004a1200b3e9c7cb3e35240043e6"
    ),
    "app/api/v1/endpoints/community.py": (
        "311c397b966b0a1c78ece6cd20c736adbcf37f5e689687a5c2fd97675f41ef1a"
    ),
    "app/domain/entities/community_intelligence.py": (
        "c0f0de577e6a270bdd656a1e40acae13d0ae64e402bba74f35f817f0c6e8d59b"
    ),
    "app/domain/interfaces/community_intelligence_repository.py": (
        "75caf24fb1c3dfe5911b4f6d0176a5a5c4d14f7cd934c7d1620bf2566fb3e89e"
    ),
}

PROTECTED_DIGESTS.update(EXTRA_DIGESTS)


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_knowledge_graph_service_exists_and_is_independent() -> None:
    service_path = ROOT / "app/services/knowledge_graph_service.py"
    assert service_path.is_file()
    text = service_path.read_text(encoding="utf-8")
    assert "KnowledgeGraphService" in text

    lowered = text.lower()
    assert "import neo4j" not in lowered
    assert "import neptune" not in lowered
    assert "import arangodb" not in lowered
    assert "import openai" not in lowered
    assert "from neo4j" not in lowered
    assert "from neptune" not in lowered
    assert "from arangodb" not in lowered
    assert "from openai" not in lowered
    assert "gremlin" not in lowered
    assert "cypher" not in lowered


def test_knowledge_graph_modules_have_no_external_graph_db_dependency() -> None:
    kg_dir = ROOT / "app/intelligence/knowledge_graph"
    for path in sorted(kg_dir.rglob("*.py")):
        lowered = path.read_text(encoding="utf-8").lower()
        assert "neo4j" not in lowered, f"{path} references neo4j"
        assert "neptune" not in lowered, f"{path} references neptune"
        assert "arangodb" not in lowered, f"{path} references arangodb"
        assert "import openai" not in lowered, f"{path} imports openai"
        assert "import anthropic" not in lowered, f"{path} imports anthropic"


def test_prior_services_do_not_hard_depend_on_knowledge_graph_service() -> None:
    for relative in (
        "app/services/review_summary_service.py",
        "app/services/watchlist_service.py",
        "app/services/community_intelligence_service.py",
        "app/intelligence/dealscore/engine.py",
        "app/intelligence/recommendation/engine.py",
        "app/intelligence/shopping_assistant/orchestrator.py",
        "app/intelligence/shopping_assistant/deterministic.py",
        "app/intelligence/shopping_assistant/evidence.py",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert "KnowledgeGraphService" not in content
        assert "KnowledgeGraphEngine" not in content


def test_shopping_assistant_service_integrates_via_optional_collaborator() -> None:
    text = (ROOT / "app/services/shopping_assistant_service.py").read_text(encoding="utf-8")
    assert "knowledge_graph_service" in text
    assert "graph_unavailable" in text
