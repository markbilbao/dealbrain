"""Production paths that would make a reviewed Medium reachable again."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
ALEMBIC = ROOT / "alembic"
HELPER = APP / "security" / "base64url.py"
OPERATIONAL = [
    ROOT / "Dockerfile",
    ROOT / "docker-compose.yml",
    *sorted((ROOT / "infra" / "compose").glob("*.yml")),
    *sorted((ROOT / ".github" / "workflows").glob("*.yml")),
    *sorted((ROOT / "scripts").rglob("*.py")),
    *sorted((ROOT / "scripts").rglob("*.sh")),
]


def _python_sources(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_production_code_does_not_call_the_vulnerable_decoders() -> None:
    helper = _text(HELPER)
    assert "urlsafe_b64decode" not in helper
    assert "validate=True" in helper
    offenders: list[str] = []
    for path in _python_sources(APP) + _python_sources(ALEMBIC):
        if path == HELPER:
            continue
        text = _text(path)
        if "urlsafe_b64decode" in text or re.search(r"(?<![\w])b64decode\(", text):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_production_code_does_not_reach_imap_pop_or_cookie_js() -> None:
    offenders: list[str] = []
    for path in _python_sources(APP) + _python_sources(ALEMBIC):
        text = _text(path)
        if any(
            token in text
            for token in (
                "imaplib",
                "poplib",
                "js_output",
                "Morsel.js_output",
                "BaseCookie.js_output",
            )
        ):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_running_application_does_not_create_a_temporary_directory() -> None:
    offenders: list[str] = []
    for path in _python_sources(APP) + _python_sources(ALEMBIC):
        if "TemporaryDirectory" in _text(path):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_operational_entrypoints_do_not_invoke_busybox_wget() -> None:
    offenders: list[str] = []
    for path in [*_python_sources(APP), *_python_sources(ALEMBIC), *OPERATIONAL]:
        if not path.is_file():
            continue
        if "wget" in _text(path):
            offenders.append(path.relative_to(ROOT).as_posix())
    dockerfile = _text(ROOT / "Dockerfile")
    assert "urllib.request" in dockerfile
    assert offenders == []
