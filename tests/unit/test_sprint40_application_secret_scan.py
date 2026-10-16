"""Application-source secret scan: exact exceptions, no raw credential output."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from app.launch.internal_auth import _LOCAL_DEVELOPMENT_GATE
from app.user.fixtures import DEMO_PASSWORD
from scripts.secret_scan_25a import (
    APPLICATION_GLOB,
    BASELINE_PATH,
    ROOT,
    RULE_AWS_ACCESS_KEY,
    RULE_PASSWORD,
    RULE_PRIVATE_KEY,
    RULE_PYTHON_LITERAL,
    SCAN_GLOBS,
    ScanError,
    _read_required,
    compare_findings,
    load_baseline,
    main,
    scan_tree,
)

CI = ROOT / ".github/workflows/ci.yml"
FAKE_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
FAKE_PEM = "-----BEGIN PRIVATE KEY-----"
FAKE_PASSWORD = "not-a-real-password"
FAKE_TOKEN = "review-token-value"
FAKE_API_KEY = "review-api-key-value"
_FINGERPRINT = "a" * 64


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _findings(root: Path, relative: str, text: str):
    _write(root, relative, text)
    return scan_tree(root).findings


def _exception(finding, **overrides: object) -> dict:
    payload: dict[str, object] = {
        "path": finding.path,
        "rule_id": finding.rule_id,
        "symbol": finding.symbol,
        "source_fingerprint": finding.source_fingerprint,
        "rationale": "false_positive",
        "reason": "Reviewed test fixture. It is not a production credential.",
    }
    payload.update(overrides)
    return payload


def _baseline_payload(exceptions: list[dict], **overrides: object) -> dict:
    payload: dict[str, object] = {
        "version": 1,
        "scanner": "secret_scan_25a",
        "scope": list(SCAN_GLOBS),
        "exceptions": exceptions,
    }
    payload.update(overrides)
    return payload


def _write_baseline(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _one(findings, rule_id: str, symbol: str | None = None):
    matches = [
        finding
        for finding in findings
        if finding.rule_id == rule_id and (symbol is None or finding.symbol == symbol)
    ]
    assert len(matches) == 1
    return matches[0]


def test_application_python_scope_reports_a_fake_secret(tmp_path: Path) -> None:
    findings = _findings(tmp_path, "app/sample.py", f'api_key = "{FAKE_API_KEY}"\n')
    finding = _one(findings, RULE_PYTHON_LITERAL, "api_key")
    assert finding.path == "app/sample.py"
    assert FAKE_API_KEY not in finding.label("finding")
    assert APPLICATION_GLOB in SCAN_GLOBS


def test_existing_infra_env_script_and_workflow_scope_remains(tmp_path: Path) -> None:
    assert SCAN_GLOBS[:4] == (
        "infra/**/*",
        ".env*.example",
        "scripts/**/*",
        ".github/workflows/**/*",
    )
    _write(tmp_path, "infra/main.tf", f'access = "{FAKE_AWS_KEY}"\n')
    _write(tmp_path, ".env.example", f"AWS_ACCESS_KEY_ID={FAKE_AWS_KEY}\n")
    _write(tmp_path, "scripts/deploy.py", f'value = "{FAKE_AWS_KEY}"\n')
    _write(tmp_path, ".github/workflows/ci.yml", f"# {FAKE_AWS_KEY}\n")
    paths = {finding.path for finding in scan_tree(tmp_path).findings}
    assert paths == {
        "infra/main.tf",
        ".env.example",
        "scripts/deploy.py",
        ".github/workflows/ci.yml",
    }


def test_fake_aws_key_private_key_and_password_in_app_are_detected(tmp_path: Path) -> None:
    source = f'access = "{FAKE_AWS_KEY}"\nmarker = "{FAKE_PEM}"\npassword = "{FAKE_PASSWORD}"\n'
    findings = _findings(tmp_path, "app/sample.py", source)
    assert _one(findings, RULE_AWS_ACCESS_KEY).path == "app/sample.py"
    assert _one(findings, RULE_PRIVATE_KEY).path == "app/sample.py"
    assert _one(findings, RULE_PASSWORD, "password").path == "app/sample.py"
    assert _one(findings, RULE_PYTHON_LITERAL, "password").path == "app/sample.py"


def test_token_and_api_key_literals_and_field_default_are_detected(tmp_path: Path) -> None:
    source = (
        f'INTERNAL_TOKEN = "{FAKE_TOKEN}"\n'
        f'api_key = "{FAKE_API_KEY}"\n'
        "secret_name: str = Field(default="
        f'"{FAKE_API_KEY}", min_length=1)\n'
    )
    findings = _findings(tmp_path, "app/sample.py", source)
    assert _one(findings, RULE_PYTHON_LITERAL, "INTERNAL_TOKEN")
    assert _one(findings, RULE_PYTHON_LITERAL, "api_key")
    assert _one(findings, RULE_PYTHON_LITERAL, "secret_name")


def test_empty_secret_default_and_ordinary_token_text_are_not_findings(tmp_path: Path) -> None:
    source = (
        'openai_api_key = ""\n'
        'api_key: str = Field(default="")\n'
        'message = "send the token to the user"\n'
        'max_tokens = "not-a-secret"\n'
        "def describe():\n"
        '    return "api_key is not assigned here"\n'
    )
    assert _findings(tmp_path, "app/clean.py", source) == ()


def test_exact_exception_does_not_cover_another_path(tmp_path: Path) -> None:
    source = f'api_key = "{FAKE_API_KEY}"\n'
    _write(tmp_path, "app/original.py", source)
    _write(tmp_path, "app/other.py", source)
    findings = scan_tree(tmp_path).findings
    original = next(finding for finding in findings if finding.path == "app/original.py")
    other = next(finding for finding in findings if finding.path == "app/other.py")
    assert original.source_fingerprint != other.source_fingerprint
    problems = compare_findings([original, other], [_exception(original)])
    assert any(
        line.startswith("unbaselined finding") and "path=app/other.py" in line for line in problems
    )
    assert not any("path=app/original.py" in line for line in problems)


def test_changed_credential_invalidates_the_fingerprint(tmp_path: Path) -> None:
    original = _findings(tmp_path, "app/sample.py", f'api_key = "{FAKE_API_KEY}"\n')
    moved = _findings(
        tmp_path,
        "app/sample.py",
        f'"""note"""\n\napi_key = "{FAKE_API_KEY}"\n',
    )
    changed = _findings(tmp_path, "app/sample.py", f'api_key = "{FAKE_API_KEY}-changed"\n')
    assert original[0].source_fingerprint == moved[0].source_fingerprint
    assert original[0].source_fingerprint != changed[0].source_fingerprint
    problems = compare_findings(changed, [_exception(original[0])])
    assert any(line.startswith("stale baseline exception") for line in problems)
    assert any(line.startswith("unbaselined finding") for line in problems)


def test_wildcard_malformed_version_and_rationale_fail(tmp_path: Path) -> None:
    valid = _exception_shape()
    wildcard_path = dict(valid)
    wildcard_path["path"] = "app/*.py"
    path = _write_baseline(tmp_path / "wild-path.json", _baseline_payload([wildcard_path]))
    with pytest.raises(ScanError, match="wildcard path"):
        load_baseline(path)

    wildcard_rule = dict(valid)
    wildcard_rule["rule_id"] = "*"
    path = _write_baseline(tmp_path / "wild-rule.json", _baseline_payload([wildcard_rule]))
    with pytest.raises(ScanError, match="wildcard rule"):
        load_baseline(path)

    _write_baseline(tmp_path / "bad.json", _baseline_payload([]))
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(ScanError, match="malformed baseline"):
        load_baseline(tmp_path / "bad.json")

    version = _baseline_payload([], version=2)
    path = _write_baseline(tmp_path / "version.json", version)
    with pytest.raises(ScanError, match="unsupported baseline version"):
        load_baseline(path)

    unknown = dict(valid)
    unknown["rationale"] = "risk_accepted"
    path = _write_baseline(tmp_path / "rationale.json", _baseline_payload([unknown]))
    with pytest.raises(ScanError, match="unknown rationale"):
        load_baseline(path)

    outside = dict(valid)
    outside["path"] = "../secret.py"
    path = _write_baseline(tmp_path / "outside.json", _baseline_payload([outside]))
    with pytest.raises(ScanError, match="outside repository"):
        load_baseline(path)

    missing_scope = _baseline_payload([])
    missing_scope["scope"] = [item for item in SCAN_GLOBS if item != APPLICATION_GLOB]
    path = _write_baseline(tmp_path / "scope.json", missing_scope)
    with pytest.raises(ScanError, match="missing application scan scope"):
        load_baseline(path)


def test_python_parse_error_and_unreadable_file_fail_closed(tmp_path: Path) -> None:
    _write(tmp_path, "app/good.py", "value = 1\n")
    _write(tmp_path, "app/broken.py", "def broken(\n")
    with pytest.raises(ScanError, match="Python syntax parse failure: app/broken.py"):
        scan_tree(tmp_path)
    missing = tmp_path / "absent.py"
    with pytest.raises(ScanError, match="unable to read required scanned file"):
        _read_required(missing, "app/absent.py")


def test_scanner_and_baseline_do_not_contain_raw_secret_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main() == 0
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "secret_scan_25a: OK" in captured.out
    assert "application_python=649" in captured.out
    assert "findings=8" in captured.out
    assert "exceptions=8" in captured.out
    for secret in (DEMO_PASSWORD, _LOCAL_DEVELOPMENT_GATE, FAKE_AWS_KEY):
        assert secret not in combined
    baseline_text = BASELINE_PATH.read_text(encoding="utf-8")
    assert DEMO_PASSWORD not in baseline_text
    assert _LOCAL_DEVELOPMENT_GATE not in baseline_text
    assert "INTERNAL_LAUNCH_ADMIN_TOKEN" not in baseline_text


def test_reviewed_demo_exceptions_are_exact_and_a_new_credential_fails(tmp_path: Path) -> None:
    baseline = load_baseline(BASELINE_PATH)
    result = scan_tree(ROOT)
    assert result.application_python == 649
    assert result.files == 809
    assert compare_findings(result.findings, baseline["exceptions"]) == []
    counts = Counter(item["rationale"] for item in baseline["exceptions"])
    assert counts["safe_demo_constant"] == 2
    assert counts["false_positive"] == 6
    assert counts.get("documented_placeholder", 0) == 0
    demo = [
        item
        for item in baseline["exceptions"]
        if item["path"] == "app/user/fixtures.py" and item["symbol"] == "DEMO_PASSWORD"
    ]
    assert {item["rule_id"] for item in demo} == {RULE_PASSWORD, RULE_PYTHON_LITERAL}
    assert all(item["rationale"] == "safe_demo_constant" for item in demo)
    auth = (ROOT / "app/launch/internal_auth.py").read_text(encoding="utf-8")
    assert "INTERNAL_LAUNCH_ADMIN_TOKEN" not in auth
    assert "LAUNCH_ADMIN_TOKEN" in auth
    assert not any(finding.path == "app/launch/internal_auth.py" for finding in result.findings)
    assert not any(finding.path == "app/core/config.py" for finding in result.findings)
    assert not any(
        item["path"] == "app/launch/internal_auth.py" or item["symbol"] == "_LOCAL_DEVELOPMENT_GATE"
        for item in baseline["exceptions"]
    )
    assert all(
        "*" not in item["path"] and "*" not in item["rule_id"] for item in baseline["exceptions"]
    )
    fresh = _findings(tmp_path, "app/new_credential.py", f'api_key = "{FAKE_API_KEY}"\n')
    problems = compare_findings(fresh, [])
    assert len(problems) == 1
    assert problems[0].startswith("unbaselined finding")
    assert FAKE_API_KEY not in problems[0]


def test_self_exclusion_does_not_exclude_other_scripts(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/secret_scan_25a.py", f'value = "{FAKE_AWS_KEY}"\n')
    _write(tmp_path, "scripts/other.py", f'value = "{FAKE_AWS_KEY}"\n')
    findings = scan_tree(tmp_path).findings
    assert [finding.path for finding in findings] == ["scripts/other.py"]
    assert FAKE_AWS_KEY not in findings[0].label("finding")


def test_one_exception_does_not_cover_duplicate_findings(tmp_path: Path) -> None:
    source = f'api_key = "{FAKE_API_KEY}"\napi_key = "{FAKE_API_KEY}"\n'
    findings = _findings(tmp_path, "app/sample.py", source)
    assert len(findings) == 2
    assert findings[0].source_fingerprint == findings[1].source_fingerprint
    uncovered = compare_findings(findings, [_exception(findings[0])])
    assert len(uncovered) == 1
    assert uncovered[0].startswith("unbaselined finding")
    extra = compare_findings(findings[:1], [_exception(findings[0]), _exception(findings[0])])
    assert len(extra) == 1
    assert extra[0].startswith("duplicate exception exceeds finding multiplicity")


def test_ci_invokes_this_scanner_before_later_test_gates() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read\n" in text
    assert "security-events" not in text
    secret_at = text.index("Secret scan (deterministic)")
    contract_at = text.index("OpenAPI / API contract tests")
    pytest_at = text.index("uv run pytest -q")
    assert secret_at < contract_at < pytest_at
    assert "uv run python scripts/secret_scan_25a.py" in text
    assert "tests/unit/test_sprint40_application_secret_scan.py" in text
    step = text.split("Secret scan (deterministic)", 1)[1].split("\n\n", 1)[0]
    assert "continue-on-error" not in step
    assert "|| true" not in step


def _exception_shape() -> dict:
    return {
        "path": "app/sample.py",
        "rule_id": RULE_PYTHON_LITERAL,
        "symbol": "api_key",
        "source_fingerprint": _FINGERPRINT,
        "rationale": "false_positive",
        "reason": "Reviewed test fixture. It is not a production credential.",
    }
