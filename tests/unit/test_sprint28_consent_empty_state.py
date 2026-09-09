"""Sprint 28 post-merge: consent empty-state is shown once on a zero-record fetch."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from app.consumer.account_pages import render_account_settings_page
from app.privacy.consent_audit import CONSUMER_EMPTY_NOTE
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_JS = (ROOT / "app/static/consumer/js/account.js").read_text(encoding="utf-8")
ACCOUNT_HTML = render_account_settings_page()


def _load_consent_audit_source(source: str = ACCOUNT_JS) -> str:
    start = source.index("async function loadConsentAudit")
    end = source.index("\nbindIdentityToken", start)
    return source[start:end]


def _empty_record_branch(fn: str) -> str:
    start = fn.index("if (!records.length)")
    brace = fn.index("{", start)
    depth = 0
    for index, char in enumerate(fn[brace:], start=brace):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return fn[start : index + 1]
    raise AssertionError("unterminated empty-record branch")


class _ConsentSurface(HTMLParser):
    """Account consent widgets: status live region plus static empty-state."""

    def __init__(self) -> None:
        super().__init__()
        self.status_text = ""
        self.unpublished_text = ""
        self.unpublished_hidden = True
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = {key for key, _value in attrs}
        if "data-consent-status" in names:
            self._capture = "status"
            self.status_text = ""
            return
        if "data-consent-unpublished" in names:
            self._capture = "unpublished"
            self.unpublished_text = ""
            self.unpublished_hidden = "hidden" in names
            return

    def handle_data(self, data: str) -> None:
        if self._capture == "status":
            self.status_text += data
        elif self._capture == "unpublished":
            self.unpublished_text += data

    def handle_endtag(self, tag: str) -> None:
        self._capture = None

    def visible_empty_notes(self) -> list[str]:
        copies: list[str] = []
        if self.status_text.strip() == CONSUMER_EMPTY_NOTE:
            copies.append("status")
        if not self.unpublished_hidden and self.unpublished_text.strip() == CONSUMER_EMPTY_NOTE:
            copies.append("unpublished")
        return copies


def _consent_surface(html: str = ACCOUNT_HTML) -> _ConsentSurface:
    parser = _ConsentSurface()
    parser.feed(html)
    return parser


def test_account_markup_has_one_hidden_empty_state_and_empty_status() -> None:
    html = ACCOUNT_HTML
    assert html.count(CONSUMER_EMPTY_NOTE) == 1
    surface = _consent_surface(html)
    assert surface.unpublished_text.strip() == CONSUMER_EMPTY_NOTE
    assert surface.unpublished_hidden is True
    assert surface.status_text.strip() == ""
    assert surface.visible_empty_notes() == []
    fn = _load_consent_audit_source()
    assert 'setStatus("Loading policy acknowledgements…", "consent")' in fn
    assert "Could not load policy acknowledgements." in fn


def test_successful_zero_record_response_renders_empty_state_once() -> None:
    fn = _load_consent_audit_source()
    empty_branch = _empty_record_branch(fn)
    assert CONSUMER_EMPTY_NOTE not in ACCOUNT_JS
    assert CONSUMER_EMPTY_NOTE not in fn
    assert f'setStatus("{CONSUMER_EMPTY_NOTE}"' not in fn
    assert "unpublished.hidden = false" in empty_branch
    assert 'setStatus("", "consent")' in empty_branch
    assert empty_branch.count("setStatus(") == 1
    assert "return;" in empty_branch

    surface = _consent_surface()
    # Successful zero-record path: clear the loading status, show the static note.
    surface.status_text = ""
    surface.unpublished_hidden = False
    visible = surface.visible_empty_notes()
    assert visible == ["unpublished"]
    assert ACCOUNT_HTML.count(CONSUMER_EMPTY_NOTE) == 1


def test_consent_status_still_reports_errors_and_record_counts() -> None:
    fn = _load_consent_audit_source()
    empty_branch = _empty_record_branch(fn)
    assert 'setStatus("Loading policy acknowledgements…", "consent")' in fn
    assert "Could not load policy acknowledgements." in fn
    assert "unpublished.hidden = true" in fn
    assert "unpublished.hidden = true" not in empty_branch
    assert "policy-acceptance record(s) for this account." in fn
    status_calls = re.findall(r'setStatus\((.*?),\s*"consent"\)', fn, flags=re.DOTALL)
    assert any(call.strip() == '""' for call in status_calls)
    assert all(CONSUMER_EMPTY_NOTE not in call for call in status_calls)


def test_account_js_does_not_duplicate_empty_note_into_status() -> None:
    assert ACCOUNT_JS.count('qs("[data-consent-unpublished]")') == 1
    assert ACCOUNT_JS.count('setStatus("", "consent")') == 1
    assert "/api/v1/auth/account/consents" in ACCOUNT_JS


@pytest.mark.asyncio
async def test_account_page_serves_single_empty_state_copy(client: AsyncClient) -> None:
    page = await client.get("/account")
    assert page.status_code == 200
    assert page.text.count(CONSUMER_EMPTY_NOTE) == 1
    assert "data-consent-unpublished hidden" in page.text
    assert "data-consent-status" in page.text
    assert 'id="consents"' in page.text
