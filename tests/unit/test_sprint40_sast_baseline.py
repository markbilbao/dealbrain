"""SAST baseline gate: pinned local Bandit over app/**/*.py."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest
from scripts.check_sast_baseline import (
    BANDIT_VERSION,
    SCAN_TARGET,
    SCOPE,
    Finding,
    GateError,
    application_python_files,
    code_fingerprint,
    compare,
    exception_matches,
    interpret_scanner_output,
    load_baseline,
    parse_bandit_payload,
    require_scanner_version,
    run,
    run_bandit,
    scanner_command,
)

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github/workflows/ci.yml"
BASELINE = ROOT / "tests/security/baselines/bandit.baseline.json"
EVIDENCE = ROOT / "docs/roadmap/evidence/SPRINT_40_SAST_GATE_2026-10-14.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
START_SHA = "871e761685fe663c4d0ef4cf3b11094c32ed90b9"


def _baseline(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "version": 1,
        "scanner": "bandit",
        "scanner_version": BANDIT_VERSION,
        "scope": SCOPE,
        "exceptions": [],
    }
    payload.update(overrides)
    return payload


def _write_baseline(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _snippet(line: int, source: str) -> str:
    return f"{line} {source}\n"


def _result(
    *,
    path: str = "app/example.py",
    test_id: str = "B101",
    severity: str = "LOW",
    confidence: str = "HIGH",
    line: int = 10,
    source: str = "    assert ready",
    issue: str = "Use of assert detected.",
    line_range: list[int] | None = None,
) -> dict:
    return {
        "filename": path,
        "test_id": test_id,
        "issue_severity": severity,
        "issue_confidence": confidence,
        "line_number": line,
        "line_range": [line] if line_range is None else line_range,
        "code": _snippet(line, source),
        "issue_text": issue,
    }


def _finding(**overrides: object) -> Finding:
    result = _result()
    payload: dict[str, object] = {
        "path": result["filename"],
        "test_id": result["test_id"],
        "severity": result["issue_severity"],
        "confidence": result["issue_confidence"],
        "code_sha256": code_fingerprint(
            str(result["code"]),
            list(result["line_range"]),
            str(result["issue_text"]),
        ),
        "line_number": result["line_number"],
    }
    payload.update(overrides)
    return Finding(**payload)  # type: ignore[arg-type]


def _exception_for(finding: Finding, **overrides: object) -> dict:
    payload: dict[str, object] = {
        "path": finding.path,
        "test_id": finding.test_id,
        "severity": finding.severity,
        "confidence": finding.confidence,
        "code_sha256": finding.code_sha256,
        "rationale": "false_positive",
        "reason": "Reviewed invariant. It is not an authorization check.",
    }
    payload.update(overrides)
    return payload


def _metrics(files: set[str], results: list[dict]) -> dict:
    totals = {f"SEVERITY.{name}": 0 for name in ("UNDEFINED", "LOW", "MEDIUM", "HIGH")}
    totals.update({f"CONFIDENCE.{name}": 0 for name in ("UNDEFINED", "LOW", "MEDIUM", "HIGH")})
    totals["nosec"] = 0
    totals["skipped_tests"] = 0
    totals["loc"] = len(files)
    for result in results:
        totals[f"SEVERITY.{result['issue_severity']}"] += 1
        totals[f"CONFIDENCE.{result['issue_confidence']}"] += 1
    metrics: dict[str, object] = {"_totals": totals}
    for name in files:
        metrics[name] = {"loc": 1, "nosec": 0, "skipped_tests": 0}
    return metrics


def _payload(results: list[dict], files: set[str] | None = None) -> dict:
    expected = files if files is not None else {str(result["filename"]) for result in results}
    if not expected:
        expected = {"app/example.py"}
    return {
        "errors": [],
        "generated_at": "2026-10-14T00:00:00Z",
        "metrics": _metrics(expected, results),
        "results": results,
    }


def test_empty_baseline_and_zero_findings_pass(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_baseline(tmp_path / "bandit.baseline.json", _baseline())
    assert run(path, scan=lambda _expected: []) == 0
    captured = capsys.readouterr()
    assert "findings=0 exceptions=0" in captured.out
    assert "OK: no unbaselined SAST findings" in captured.out
    assert compare([], []) == []


def test_new_unbaselined_finding_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    finding = _finding()
    assert compare([finding], [])[0].startswith("unbaselined SAST finding:")
    path = _write_baseline(tmp_path / "bandit.baseline.json", _baseline())
    assert run(path, scan=lambda _expected: [finding]) == 1
    assert "unbaselined SAST finding:" in capsys.readouterr().err


def test_exact_exception_matches_only_the_intended_finding() -> None:
    intended = _finding()
    other = _finding(path="app/other.py", line_number=11)
    exception = _exception_for(intended)
    assert exception_matches(intended, exception)
    assert not exception_matches(other, exception)
    assert compare([intended], [exception]) == []
    assert any("unbaselined" in line for line in compare([intended, other], [exception]))
    twin = _finding(line_number=40)
    assert twin.code_sha256 == intended.code_sha256
    one_left = compare([intended, twin], [exception])
    assert len(one_left) == 1
    assert one_left[0].startswith("unbaselined SAST finding:")
    assert compare([intended, twin], [exception, _exception_for(twin)]) == []


def test_stale_baseline_exception_fails() -> None:
    finding = _finding()
    regressions = compare([], [_exception_for(finding)])
    assert len(regressions) == 1
    assert regressions[0].startswith("stale baseline exception 0:")
    changed = _finding(
        code_sha256=code_fingerprint(
            _snippet(10, "    assert missing"),
            [10],
            "Use of assert detected.",
        )
    )
    mixed = compare([changed], [_exception_for(finding)])
    assert any(line.startswith("stale baseline exception") for line in mixed)
    assert any(line.startswith("unbaselined SAST finding") for line in mixed)


def test_wildcard_exceptions_are_rejected(tmp_path: Path) -> None:
    finding = _finding()
    for field, value in (
        ("path", "app/*.py"),
        ("path", "*"),
        ("test_id", "B*"),
        ("test_id", "*"),
        ("severity", "*"),
        ("confidence", "all"),
    ):
        payload = _baseline(exceptions=[_exception_for(finding, **{field: value})])
        path = _write_baseline(tmp_path / f"{field}.json", payload)
        with pytest.raises(GateError, match="wildcard"):
            load_baseline(path)


def test_malformed_baseline_fails(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(GateError, match="not JSON"):
        load_baseline(broken)
    not_object = tmp_path / "list.json"
    not_object.write_text("[]", encoding="utf-8")
    with pytest.raises(GateError, match="JSON object"):
        load_baseline(not_object)
    missing = tmp_path / "missing.json"
    with pytest.raises(GateError, match="missing SAST baseline"):
        load_baseline(missing)
    for payload, match in (
        (_baseline(version=2), "version must be 1"),
        (_baseline(scanner="semgrep"), "scanner must be bandit"),
        (_baseline(scope="tests/**/*.py"), "scope must be"),
        (_baseline(exceptions={"path": "app/example.py"}), "exceptions must be a list"),
        (_baseline(skips=[]), "unknown fields"),
    ):
        path = _write_baseline(tmp_path / f"{match}.json", payload)
        with pytest.raises(GateError, match=match):
            load_baseline(path)


def test_wrong_baseline_scanner_version_fails(tmp_path: Path) -> None:
    path = _write_baseline(tmp_path / "old.json", _baseline(scanner_version="1.0.0"))
    with pytest.raises(GateError, match="scanner_version must be 1.9.4"):
        load_baseline(path)


def test_installed_bandit_version_mismatch_fails() -> None:
    with pytest.raises(GateError, match="installed bandit is 1.0.0"):
        require_scanner_version("1.0.0")
    require_scanner_version(BANDIT_VERSION)


def test_scanner_execution_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(GateError, match="exit 2"):
        interpret_scanner_output(2, "{}")

    def fake_command(output_path: Path) -> list[str]:
        output_path.write_text("{}", encoding="utf-8")
        return [sys.executable, "-c", "import sys; sys.exit(2)"]

    monkeypatch.setattr(
        "scripts.check_sast_baseline.installed_bandit_version",
        lambda: BANDIT_VERSION,
    )
    monkeypatch.setattr("scripts.check_sast_baseline.scanner_command", fake_command)
    with pytest.raises(GateError, match="exit 2"):
        run_bandit({"app/example.py"})


def test_invalid_scanner_json_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(GateError, match="did not parse"):
        interpret_scanner_output(0, "not-json")
    with pytest.raises(GateError, match="not an object"):
        interpret_scanner_output(1, "[]")
    with pytest.raises(GateError, match="no JSON"):
        interpret_scanner_output(1, "")

    def fake_command(output_path: Path) -> list[str]:
        output_path.write_text("{", encoding="utf-8")
        return [sys.executable, "-c", "import sys; sys.exit(1)"]

    monkeypatch.setattr(
        "scripts.check_sast_baseline.installed_bandit_version",
        lambda: BANDIT_VERSION,
    )
    monkeypatch.setattr("scripts.check_sast_baseline.scanner_command", fake_command)
    with pytest.raises(GateError, match="did not parse"):
        run_bandit({"app/example.py"})


def test_same_test_id_in_another_file_does_not_match() -> None:
    first = _finding(path="app/auth/service.py")
    second = _finding(path="app/launch/internal_auth.py", line_number=4)
    assert first.test_id == second.test_id
    assert first.code_sha256 == second.code_sha256
    exception = _exception_for(first)
    assert not exception_matches(second, exception)
    regressions = compare([second], [exception])
    assert any("unbaselined SAST finding" in line for line in regressions)
    assert any("stale baseline exception" in line for line in regressions)


def test_changed_source_fingerprint_does_not_match() -> None:
    original = _finding()
    exception = _exception_for(original)
    moved_source = "    assert ready_now"
    changed = _finding(
        code_sha256=code_fingerprint(_snippet(10, moved_source), [10], "Use of assert detected.")
    )
    assert changed.code_sha256 != original.code_sha256
    assert not exception_matches(changed, exception)
    other_message = code_fingerprint(
        _snippet(10, "    assert ready"),
        [10],
        "Use of assert detected. Extra.",
    )
    assert other_message != original.code_sha256


def test_harmless_line_movement_keeps_the_fingerprint() -> None:
    source = "    assert session is not None"
    issue = "Use of assert detected."
    original = code_fingerprint(_snippet(389, source), [389], issue)
    moved = code_fingerprint(_snippet(420, source), [420], issue)
    assert original == moved
    finding = _finding(line_number=420, code_sha256=moved)
    exception = _exception_for(_finding(line_number=389, code_sha256=original))
    assert exception_matches(finding, exception)
    assert compare([finding], [exception]) == []


def test_scan_scope_is_application_python() -> None:
    files = application_python_files()
    assert files
    assert all(path.startswith("app/") and path.endswith(".py") for path in files)
    assert not any(path.startswith("tests/") for path in files)
    command = scanner_command(Path("bandit.json"))
    assert SCAN_TARGET in command
    assert "tests" not in command
    assert "--configfile" not in command
    assert "--skip" not in command
    assert "--baseline" not in command
    assert "--exit-zero" not in command
    assert "--ignore-nosec" in command
    assert "--severity-level" in command
    assert command[command.index("--severity-level") + 1] == "all"
    data = load_baseline(BASELINE)
    assert data["scope"] == SCOPE
    assert data["scanner"] == "bandit"
    assert data["scanner_version"] == BANDIT_VERSION
    low = _result(severity="LOW")
    undefined = _result(
        path="app/other.py",
        severity="UNDEFINED",
        confidence="UNDEFINED",
        line=2,
        source="    value = 'marker'",
        issue="Informational marker.",
    )
    parsed = parse_bandit_payload(
        _payload([low, undefined], {"app/example.py", "app/other.py"}),
        {"app/example.py", "app/other.py"},
    )
    assert {item.severity for item in parsed} == {"LOW", "UNDEFINED"}


def test_ci_invokes_the_gate_before_contracts() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "SAST (Bandit baseline gate)" in text
    assert "uv run python scripts/check_sast_baseline.py" in text
    assert "tests/unit/test_sprint40_sast_baseline.py" in text
    audit = text.index("Dependency audit (pip-audit baseline gate)")
    sast = text.index("SAST (Bandit baseline gate)")
    contracts = text.index("OpenAPI / API contract tests")
    assert audit < sast < contracts
    step = text.split("SAST (Bandit baseline gate)", 1)[1].split("\n\n", 1)[0]
    assert "continue-on-error" not in step
    assert "|| true" not in step


def test_ci_does_not_add_hosted_code_scanning_permissions() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "contents: read" in text
    assert "security-events" not in text
    assert "codeql" not in text.lower()
    assert "upload-sarif" not in text
    assert "github/codeql-action" not in text
    assert "aquasecurity/trivy-action" not in text.lower()
    assert "checkov" not in text.lower()
    assert "tfsec" not in text.lower()


def test_committed_baseline_is_exact_and_the_gate_passes() -> None:
    data = load_baseline(BASELINE)
    assert data["exceptions"]
    assert all(item["rationale"] != "ignore" for item in data["exceptions"])
    for item in data["exceptions"]:
        assert item["severity"] in {"LOW", "MEDIUM"}
        assert "accepted risk" not in item["reason"].lower()
        assert "*" not in item["path"]
        assert "*" not in item["test_id"]
    assert run(BASELINE) == 0


def test_incomplete_bandit_json_fails_closed() -> None:
    files = {"app/example.py"}
    with pytest.raises(GateError, match="nosec"):
        payload = _payload([], files)
        payload["metrics"]["_totals"]["nosec"] = 1
        parse_bandit_payload(payload, files)
    with pytest.raises(GateError, match="scan error"):
        payload = _payload([], files)
        payload["errors"] = [{"filename": "app/example.py", "reason": "syntax"}]
        parse_bandit_payload(payload, files)
    with pytest.raises(GateError, match="does not cover"):
        parse_bandit_payload(
            _payload([_result(line_range=[10, 11])], files),
            files,
        )
    with pytest.raises(GateError, match="did not scan exactly"):
        parse_bandit_payload(_payload([_result()], {"app/example.py", "app/missing.py"}), files)


def test_bandit_pin_is_exact_in_project_and_lock() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f"bandit=={BANDIT_VERSION}" in pyproject
    assert "bandit>=" not in pyproject
    with (ROOT / "uv.lock").open("rb") as handle:
        lock = tomllib.load(handle)
    packages = {package["name"]: package for package in lock["package"]}
    assert packages["bandit"]["version"] == BANDIT_VERSION
    dealbrain = packages["dealbrain"]
    dev_names = {item["name"] for item in dealbrain["optional-dependencies"]["dev"]}
    assert "bandit" in dev_names
    requires = next(
        item for item in dealbrain["metadata"]["requires-dist"] if item["name"] == "bandit"
    )
    assert requires["specifier"] == f"=={BANDIT_VERSION}"


def test_sprint_40_records_the_gate_without_closing_r6() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    sprint = SPRINT40.read_text(encoding="utf-8")
    assert START_SHA in evidence
    assert START_SHA in sprint
    assert f"bandit {BANDIT_VERSION}" in evidence
    assert "IMPLEMENTED-NOT-PROVEN" in evidence
    assert "R6 stays PARTIAL" in evidence
    assert "container vulnerability scanning" in evidence
    assert "IaC security scanning" in evidence
    assert "Not ENGINEERING COMPLETE" in evidence
    assert "not named Sprint 40.8" in evidence
    assert "does not select a later engineering slice" in evidence
    assert "No deploy was performed." in evidence
    assert "CLOSED BY IMPLEMENTATION" in evidence
    assert sprint.startswith("# Sprint 40")
    assert "**Status:** Planned" in sprint.split("## Current reading", 1)[0]
