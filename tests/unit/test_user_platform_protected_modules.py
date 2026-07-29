"""Guard: Sprint 17 (User Platform) must not modify prior-sprint modules."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_personal_agent_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

# Inherit all digests protected by Sprint 16 (which itself inherits Sprint 15/14/13...),
# so DealScore, recommendation engine, and shopping assistant orchestrator modules are
# transitively protected here as well.
PROTECTED_DIGESTS = dict(PRIOR)

# Personal AI Shopping Agent core modules that Sprint 17 must not rewrite in place
# (User Platform integrates via a read-only / optional collaborator only).
EXTRA_DIGESTS = {
    "app/services/personal_agent_service.py": (
        "70321e401c850b78de0e1a60a828fab6252aa2b5bbf5efedb48be96b94c72ffa"
    ),
    "app/intelligence/personal/preference_engine.py": (
        "e1694b6dac72fbb055bf2ba391f5fb053c0a122bfaa00ba22f36b1af155cabad"
    ),
    "app/intelligence/personal/scoring_engine.py": (
        "ead6cd13daa9e0e20f61a5607f8e2df64c8ba909d72dce11c9bf8f4f08347518"
    ),
    "app/intelligence/personal/fixtures.py": (
        "c21a4266edbe76a5edb076597f4f8469c9b15d129744bf7ad94ba37eaa133b1c"
    ),
}

PROTECTED_DIGESTS.update(EXTRA_DIGESTS)


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_user_platform_service_exists_and_is_independent() -> None:
    service_path = ROOT / "app/services/user_platform_service.py"
    assert service_path.is_file()
    text = service_path.read_text(encoding="utf-8")
    assert "UserPlatformService" in text

    lowered = text.lower()
    assert "import stripe" not in lowered
    assert "import paypal" not in lowered
    assert "import openai" not in lowered
    assert "import anthropic" not in lowered
    assert "from stripe" not in lowered
    assert "from paypal" not in lowered
    assert "from openai" not in lowered
    assert "from anthropic" not in lowered


def test_user_platform_domain_modules_have_no_payment_or_ai_vendor_dependency() -> None:
    for relative in (
        "app/auth/service.py",
        "app/auth/password.py",
        "app/auth/security.py",
        "app/auth/email.py",
        "app/profile/service.py",
        "app/session/service.py",
        "app/user/memory.py",
        "app/user/fixtures.py",
        "app/user/adapters.py",
    ):
        lowered = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "stripe" not in lowered, f"{relative} references stripe"
        assert "paypal" not in lowered, f"{relative} references paypal"
        assert "import openai" not in lowered, f"{relative} imports openai"
        assert "import anthropic" not in lowered, f"{relative} imports anthropic"


def test_prior_engines_do_not_hard_depend_on_user_platform_service() -> None:
    for relative in (
        "app/services/review_summary_service.py",
        "app/services/watchlist_service.py",
        "app/services/community_intelligence_service.py",
        "app/services/knowledge_graph_service.py",
        "app/services/personal_agent_service.py",
        "app/intelligence/dealscore/engine.py",
        "app/intelligence/recommendation/engine.py",
        "app/intelligence/personal/preference_engine.py",
        "app/intelligence/personal/scoring_engine.py",
        "app/intelligence/shopping_assistant/orchestrator.py",
        "app/intelligence/shopping_assistant/deterministic.py",
        "app/intelligence/shopping_assistant/evidence.py",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert "UserPlatformService" not in content
        assert "AuthService" not in content


def test_shopping_assistant_service_integrates_via_optional_collaborator() -> None:
    text = (ROOT / "app/services/shopping_assistant_service.py").read_text(encoding="utf-8")
    assert "user_platform_service" in text
    assert "user_platform_unavailable" in text or "authenticated" in text
