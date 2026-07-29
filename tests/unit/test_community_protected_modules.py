"""Guard: Sprint 14 must not modify protected prior-sprint modules."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_shopping_assistant_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

# Inherit Sprint 13 protected digests; Community Intelligence must compose, not rewrite.
PROTECTED_DIGESTS = dict(PRIOR)

# Additional Shopping Assistant modules that Sprint 14 must not rewrite in place
# (integration is via DI / optional community_service collaborator only).
EXTRA_DIGESTS = {
    "app/intelligence/shopping_assistant/orchestrator.py": (
        "b32f9834239607aa14d82b562e770c8232d8e4fd3ccc52b614f337a343c5e439"
    ),
    "app/intelligence/shopping_assistant/deterministic.py": (
        "ca1c3ef26ab58dcb38598dde7300a85d216991836e49a5d684c386cb91f89602"
    ),
    "app/intelligence/shopping_assistant/evidence.py": (
        "53f0c2ee146df345af8bd44b1a57b2b3d4e33085bf0bfec989fd036f94083e87"
    ),
    "app/infrastructure/ai/shopping_providers/base.py": (
        "dbf7258a6d23fb839dfb414878e028e43103633295a3c73f78c3e5ea773e3b0a"
    ),
}

PROTECTED_DIGESTS.update(EXTRA_DIGESTS)


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_community_module_is_independent() -> None:
    service = ROOT / "app/services/community_intelligence_service.py"
    assert service.is_file()
    text = service.read_text(encoding="utf-8")
    assert "CommunityIntelligenceService" in text
    assert "OpenAICommunityProvider" not in text
    assert "ClaudeCommunityProvider" not in text
    assert "GeminiCommunityProvider" not in text
    assert "import openai" not in text.lower()
    assert "import anthropic" not in text.lower()
    assert "requests.get" not in text
    assert "httpx" not in text

    # Prior services must not hard-depend on CommunityIntelligenceService.
    for relative in (
        "app/services/review_summary_service.py",
        "app/services/watchlist_service.py",
        "app/intelligence/dealscore/engine.py",
        "app/intelligence/recommendation/engine.py",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert "CommunityIntelligenceService" not in content


def test_community_connectors_have_no_scraping_assumptions() -> None:
    for relative in (
        "app/infrastructure/community/reddit.py",
        "app/infrastructure/community/youtube.py",
        "app/infrastructure/community/amazon_qa.py",
        "app/infrastructure/community/discord.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "beautifulsoup" not in lowered
        assert "selenium" not in lowered
        assert "scrapy" not in lowered
        assert "puppeteer" not in lowered
