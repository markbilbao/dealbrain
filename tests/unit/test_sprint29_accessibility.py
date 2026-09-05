"""Sprint 29 consumer accessibility contract for Ask, dialogs, and insertion height."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / "app/static/consumer/css/piqsavi.css").read_text(encoding="utf-8")
JS = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_conversation_surfaces_meet_accessibility_contract(client: AsyncClient) -> None:
    page = await client.get("/results/headphones-standard")
    assert 'role="dialog"' in page.text
    assert 'aria-modal="true"' in page.text
    assert 'aria-live="polite"' in page.text
    assert 'aria-label="Close conversation"' in page.text
    assert 'class="skip-link"' in page.text
    assert "Escape" in JS
    assert "focusableIn" in JS
    assert "visualViewport" in JS
    assert "askRestoreFocus" in JS
    assert "safe-area-inset-bottom" in CSS
    assert "prefers-reduced-motion" in CSS


def test_ask_insertion_heights_match_manifest() -> None:
    assert "--ask-h: 80px;" in CSS
    assert "--ask-h: 72px;" in CSS
    assert "min-height: var(--ask-h)" in CSS
    desktop_index = CSS.index("--ask-h: 80px;")
    mobile_index = CSS.index("--ask-h: 72px;")
    assert desktop_index < mobile_index
    assert "@media (max-width: 980px)" in CSS
    assert CSS.index("@media (max-width: 980px)") < mobile_index
