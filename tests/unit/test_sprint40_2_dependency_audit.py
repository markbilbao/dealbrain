"""Sprint 40.2: pip-audit is a required CI gate with an explicit baseline."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
from scripts.check_pip_audit_baseline import (
    PIP_AUDIT_VERSION,
    Finding,
    GateError,
    compare,
    dependency_class,
    dependency_origin,
    ensure_same_closure,
    exception_matches,
    load_baseline,
    locked_distributions,
    normalize_name,
    parse_audit_payload,
    parse_export,
    requirement_name,
    via_for,
)

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github/workflows/ci.yml"
BASELINE = ROOT / "tests/security/baselines/pip-audit.baseline.json"
SCRIPT = ROOT / "scripts/check_pip_audit_baseline.py"
EVIDENCE = ROOT / "docs/roadmap/evidence/SPRINT_40_2_DEPENDENCY_AUDIT_BASELINE_2026-10-09.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
START_SHA = "ed666678691522238eb44c395a3bc5273f36fa4b"

EXPORT = """\
alembic==1.18.5
colorama==0.4.6 ; sys_platform == 'win32'
mako==1.4.3
pip-audit==2.10.1
"""


def _finding(**overrides: object) -> Finding:
    payload: dict[str, object] = {
        "package": "mako",
        "version": "1.3.12",
        "advisory_id": "CVE-2026-102991",
        "aliases": ("GHSA-5639-2j2p-m4mx",),
        "fix_versions": ("1.4.2",),
        "dependency_class": "transitive",
        "origin": "transitive",
        "via": ("alembic",),
    }
    payload.update(overrides)
    return Finding(**payload)  # type: ignore[arg-type]


def _exception(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "package": "mako",
        "version": "1.3.12",
        "advisory_id": "GHSA-5639-2j2p-m4mx",
    }
    payload.update(overrides)
    return payload


def test_export_strips_markers_and_rejects_unpinned_lines() -> None:
    pins = parse_export(EXPORT)
    assert pins == {
        "alembic": "1.18.5",
        "colorama": "0.4.6",
        "mako": "1.4.3",
        "pip-audit": "2.10.1",
    }
    with pytest.raises(GateError, match="exact pin"):
        parse_export("mako>=1.4.2\n")


def test_requirement_names_and_classes() -> None:
    assert requirement_name("psycopg[binary]>=3.2.0") == "psycopg"
    assert normalize_name("PyYAML") == "pyyaml"
    runtime = {"alembic"}
    dev = {"pip-audit"}
    assert dependency_class("alembic", runtime, dev) == "direct"
    assert dependency_origin("alembic", runtime, dev) == "project.dependencies"
    assert dependency_class("pip-audit", runtime, dev) == "direct"
    assert dependency_origin("pip-audit", runtime, dev) == "project.optional-dependencies.dev"
    assert dependency_class("mako", runtime, dev) == "transitive"
    assert dependency_origin("mako", runtime, dev) == "transitive"


def test_lock_closure_skips_the_local_project_and_must_match_export() -> None:
    lock = {
        "package": [
            {"name": "dealbrain", "version": "1.0.0", "source": {"editable": "."}},
            {"name": "mako", "version": "1.4.3", "source": {"registry": "https://pypi.org/simple"}},
        ]
    }
    locked = locked_distributions(lock)
    assert locked == {"mako": "1.4.3"}
    ensure_same_closure({"mako": "1.4.3"}, locked)
    with pytest.raises(GateError, match="does not match"):
        ensure_same_closure({}, locked)
    parents = {"mako": ("alembic", "dealbrain")}
    assert via_for("mako", parents) == ("alembic",)


def test_unbaselined_and_version_scoped_exceptions() -> None:
    current = _finding()
    assert compare([current], [])
    assert compare([current], [])[0].startswith("unbaselined advisory:")
    assert compare([current], [_exception()]) == []
    assert exception_matches(current, _exception(advisory_id="CVE-2026-102991", aliases=[]))
    upgraded = _finding(version="1.4.3")
    mismatch = compare([upgraded], [_exception()])
    assert any("unbaselined advisory" in line for line in mismatch)
    assert any("stale baseline exception" in line for line in mismatch)
    other = compare([current], [_exception(advisory_id="PYSEC-0000-00000")])
    assert any("unbaselined advisory" in line for line in other)
    assert any("stale baseline exception" in line for line in other)


def test_payload_parser_fails_closed_on_skips_and_missing_packages() -> None:
    exported = {"mako": "1.4.3", "alembic": "1.18.5"}
    payload = {
        "dependencies": [
            {"name": "mako", "version": "1.4.3", "vulns": []},
            {
                "name": "alembic",
                "version": "1.18.5",
                "vulns": [
                    {
                        "id": "PYSEC-2099-1",
                        "aliases": [],
                        "fix_versions": [],
                    }
                ],
            },
        ]
    }
    findings = parse_audit_payload(payload, exported, {"alembic"}, set(), {"alembic": ()})
    assert len(findings) == 1
    assert findings[0].dependency_class == "direct"
    assert findings[0].advisory_id == "PYSEC-2099-1"
    with pytest.raises(GateError, match="skipped"):
        parse_audit_payload(
            {
                "dependencies": [
                    {"name": "mako", "version": "1.4.3", "skip_reason": "unavailable", "vulns": []},
                    {"name": "alembic", "version": "1.18.5", "vulns": []},
                ]
            },
            exported,
            set(),
            set(),
            {},
        )
    with pytest.raises(GateError, match="does not match"):
        parse_audit_payload(
            {"dependencies": [{"name": "mako", "version": "1.4.3", "vulns": []}]},
            exported,
            set(),
            set(),
            {},
        )


def test_baseline_rejects_wildcards_and_the_committed_file_is_empty() -> None:
    data = load_baseline(BASELINE)
    assert data["exceptions"] == []
    assert data["scanner_version"] == PIP_AUDIT_VERSION
    assert compare([_finding()], data["exceptions"])
    script = SCRIPT.read_text(encoding="utf-8")
    assert "--ignore-vuln" not in script
    assert "ignore-all" not in script
    raw = json.loads(BASELINE.read_text(encoding="utf-8"))
    raw["exceptions"] = [{"package": "*", "version": "1.3.12", "advisory_id": "CVE-2026-102991"}]
    path = BASELINE.with_name("pip-audit.baseline.invalid.json")
    path.write_text(json.dumps(raw), encoding="utf-8")
    try:
        with pytest.raises(GateError, match="wildcard"):
            load_baseline(path)
    finally:
        path.unlink()


def test_locked_mako_is_the_fixed_release_and_scanner_is_pinned() -> None:
    with (ROOT / "uv.lock").open("rb") as handle:
        lock = tomllib.load(handle)
    locked = locked_distributions(lock)
    mako = tuple(int(part) for part in locked["mako"].split("."))
    assert mako >= (1, 4, 2)
    assert locked["pip-audit"] == PIP_AUDIT_VERSION
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "pip-audit==2.10.1" in pyproject


def test_ci_runs_the_scanner_without_replacing_existing_gates() -> None:
    text = CI.read_text(encoding="utf-8")
    for needle in (
        "check_ruff_baseline",
        "secret_scan_25a",
        "test_openapi_drift",
        "test_sprint25a_infrastructure",
        "test_sprint40_2_dependency_audit",
        "uv run pytest -q",
        "terraform validate",
        "docker compose",
        "build-push-action",
        "scripts/check_pip_audit_baseline.py",
    ):
        assert needle in text, needle
    assert re.search(
        r"- name: Dependency audit \(pip-audit baseline gate\)\n"
        r"\s+run: uv run python scripts/check_pip_audit_baseline\.py\n",
        text,
    )
    step = text.split("Dependency audit (pip-audit baseline gate)", 1)[1].split("\n\n", 1)[0]
    assert "continue-on-error" not in step
    assert "|| true" not in step
    assert "\n        if:" not in step
    assert "--ignore-vuln" not in text
    assert "terraform apply" not in text
    assert "id-token: write" not in text
    assert "packages: write" not in text


def test_sprint_40_stays_planned_and_records_the_one_fixed_advisory() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    sprint = SPRINT40.read_text(encoding="utf-8")
    assert START_SHA in evidence
    assert "**Status:** Planned" in sprint
    assert "Sprint 40 stays Planned" in evidence
    assert "Not ENGINEERING COMPLETE" in evidence
    assert "in-process rate limits only" in evidence
    assert "CSRF not enforced" in evidence
    assert "CSP `'unsafe-inline'`" in evidence
    assert "URL validation / SSRF" in evidence
    assert "Class C count remains 19" in evidence
    assert "selected next engineering slice remains NONE" in evidence
    assert "Sprint 41 stays UNSTARTED" in evidence
    assert "No deploy was performed." in evidence
    assert "Routing stays 0." in evidence
    assert "CVE-2026-102991" in evidence
    assert "GHSA-5639-2j2p-m4mx" in evidence
    assert "transitive" in evidence
    assert "mako" in evidence
    assert "1.4.3" in evidence
    assert "exceptions" in evidence
    assert "pip-audit 2.10.1" in evidence
    assert "no longer an open absence" in evidence
    assert "R6 stays PARTIAL" in evidence
