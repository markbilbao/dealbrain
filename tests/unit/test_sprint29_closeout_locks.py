"""Sprint 29 closeout locks: PiqScore heights, affiliate honesty, no live research."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
CONSUMER_JS = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
ACCOUNT_JS = (ROOT / "app/static/consumer/js/account.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/consumer/css/piqsavi.css").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_affiliate_disclosure_and_no_live_research_claims(client: AsyncClient) -> None:
    results = await client.get("/results/headphones-standard")
    support = await client.get("/support")
    assert "commission" in results.text.lower() or "affiliate" in results.text.lower()
    assert "live merchant research" not in results.text.lower()
    assert "research executed" not in results.text.lower()
    assert "Sprint 38" not in support.text
    assert "answer_from_evidence" not in CONSUMER_JS
    assert "refine_session_recommendation" not in CONSUMER_JS
    assert "propose_research" not in CONSUMER_JS
    assert "DealBrain" not in CONSUMER_JS
    assert "DealBrain" not in ACCOUNT_JS
    assert "DealBrain" not in CSS


def test_ask_height_tokens_remain_locked() -> None:
    assert CSS.count("--ask-h: 80px;") == 1
    assert CSS.count("--ask-h: 72px;") == 1
