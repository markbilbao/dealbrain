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


def test_conversational_actions_remain_affiliate_neutral() -> None:
    service_files = (
        ROOT / "app/services/answer_from_evidence.py",
        ROOT / "app/services/refine_session_recommendation.py",
        ROOT / "app/services/propose_research.py",
    )
    for path in service_files:
        source = path.read_text(encoding="utf-8")
        assert '"affiliate_influence": False' in source
        assert '"affiliate_influence": True' not in source
        assert "commission_influenced" not in source

    from tests.unit.test_phase_29_4b_refine_session_recommendation import (
        DECISION_ID,
        _owner,
        _service as refine_service,
    )
    from tests.unit.test_phase_29_4c_propose_research import _service as propose_service

    refine, _, _, refine_snapshot = refine_service()
    refined = refine.refine(
        {"query": "Comfort matters more to me now.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=refine_snapshot,
    )
    assert refined.processing["affiliate_influence"] is False

    propose, _, _, propose_snapshot = propose_service()
    proposed = propose.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=propose_snapshot,
    )
    assert proposed.processing["affiliate_influence"] is False
    assert proposed.processing["requires_research_confirmation"] is True
