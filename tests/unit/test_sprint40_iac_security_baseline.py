"""IaC security gate: pinned Trivy misconfiguration scan of infra/terraform."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.check_iac_security_baseline import (
    RATIONALES,
    REQUIRED_ROOTS,
    SCAN_RELATIVE,
    TRIVY_LINUX_AMD64_SHA256,
    TRIVY_VERSION,
    Finding,
    GateError,
    assert_no_scanner_ignores,
    assert_scanner_stderr,
    compare,
    exception_matches,
    fingerprint_for,
    format_summary,
    load_baseline,
    parse_trivy_document,
    parse_version_text,
    referenced_directories,
    require_scanner_version,
    run,
    scanner_command,
    severity_counts,
    terraform_directories,
)

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github/workflows/ci.yml"
BASELINE = ROOT / "tests/security/baselines/trivy-iac.baseline.json"
INSTALL = ROOT / "scripts/security/install_trivy.sh"


def _baseline(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "version": 1,
        "scanner": "trivy",
        "scanner_version": TRIVY_VERSION,
        "scope": SCAN_RELATIVE,
        "checks": "embedded",
        "exceptions": [],
    }
    payload.update(overrides)
    return payload


def _write_baseline(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _identity(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "rule_id": "AWS-0104",
        "severity": "CRITICAL",
        "title": "A security group rule should not allow unrestricted egress to any IP address.",
        "path": "infra/terraform/modules/security_groups/main.tf",
        "start_line": 73,
        "end_line": 73,
        "resource": "aws_vpc_security_group_egress_rule.api_all",
        "caller_path": "infra/terraform/environments/production/main.tf",
        "caller_resource": "module.security_groups",
        "namespace": "builtin.aws.ec2.aws0104",
    }
    payload.update(overrides)
    payload["fingerprint"] = fingerprint_for(payload)
    return payload


def _finding(**overrides: object) -> Finding:
    identity = _identity(**overrides)
    return Finding(
        rule_id=str(identity["rule_id"]),
        severity=str(identity["severity"]),
        title=str(identity["title"]),
        path=str(identity["path"]),
        start_line=int(identity["start_line"]),
        end_line=int(identity["end_line"]),
        resource=str(identity["resource"]),
        caller_path=str(identity["caller_path"]),
        caller_resource=str(identity["caller_resource"]),
        namespace=str(identity["namespace"]),
        fingerprint=str(identity["fingerprint"]),
    )


def _exception_for(finding: Finding, **overrides: object) -> dict:
    payload: dict[str, object] = {
        "rule_id": finding.rule_id,
        "severity": finding.severity,
        "title": finding.title,
        "path": finding.path,
        "start_line": finding.start_line,
        "end_line": finding.end_line,
        "resource": finding.resource,
        "caller_path": finding.caller_path,
        "caller_resource": finding.caller_resource,
        "namespace": finding.namespace,
        "fingerprint": finding.fingerprint,
        "rationale": "not_applicable",
        "reason": "Reviewed against the documented network design for this one resource.",
    }
    payload.update(overrides)
    return payload


def _root_result(target: str) -> dict:
    return {
        "Target": target,
        "Class": "config",
        "Type": "terraform",
        "MisconfSummary": {"Successes": 1, "Failures": 0},
    }


def _misconfiguration(finding: Finding) -> dict:
    return {
        "Type": "Terraform Security Check",
        "ID": finding.rule_id,
        "Title": finding.title,
        "Severity": finding.severity,
        "Namespace": finding.namespace,
        "Status": "FAIL",
        "CauseMetadata": {
            "Resource": finding.caller_resource,
            "StartLine": finding.start_line,
            "EndLine": finding.end_line,
            "Occurrences": [
                {
                    "Resource": finding.resource,
                    "Filename": finding.path.removeprefix(f"{SCAN_RELATIVE}/"),
                },
                {
                    "Resource": finding.caller_resource,
                    "Filename": finding.caller_path.removeprefix(f"{SCAN_RELATIVE}/"),
                },
            ],
        },
    }


def _document(findings: list[Finding] | None = None, **overrides: object) -> dict:
    results = [_root_result(target) for target in REQUIRED_ROOTS]
    if findings:
        results.append(
            {
                "Target": "modules/security_groups/main.tf",
                "Class": "config",
                "Type": "terraform",
                "MisconfSummary": {"Successes": 0, "Failures": len(findings)},
                "Misconfigurations": [_misconfiguration(finding) for finding in findings],
            }
        )
    payload: dict[str, object] = {
        "SchemaVersion": 2,
        "CreatedAt": "2026-10-20T00:00:00Z",
        "ArtifactName": SCAN_RELATIVE,
        "ArtifactType": "filesystem",
        "Results": results,
        "Trivy": {"Version": TRIVY_VERSION},
    }
    payload.update(overrides)
    return payload


def test_installer_and_gate_pin_the_same_official_checksum() -> None:
    text = INSTALL.read_text(encoding="utf-8")
    assert f'TRIVY_VERSION="{TRIVY_VERSION}"' in text
    assert TRIVY_LINUX_AMD64_SHA256 in text
    assert "sha256sum -c" in text
    assert "curl | sh" not in text
    assert "latest" not in text
    command = scanner_command(Path("report.json"), Path("cache"), "/usr/local/bin/trivy")
    assert command[0] == "/usr/local/bin/trivy"
    assert command[1] == "config"
    assert "--config=" in command
    assert "--ignorefile=" in command
    assert "--skip-check-update" in command
    assert "--misconfig-scanners" in command
    assert command[command.index("--misconfig-scanners") + 1] == "terraform"
    assert command[-1] == SCAN_RELATIVE
    assert "--exit-code" in command
    assert command[command.index("--exit-code") + 1] == "0"


def test_exact_scanner_version_is_required() -> None:
    assert parse_version_text(f"Version: {TRIVY_VERSION}\n") == TRIVY_VERSION
    require_scanner_version(TRIVY_VERSION)
    with pytest.raises(GateError, match="requires 0.76.0"):
        require_scanner_version("0.76.1")
    with pytest.raises(GateError, match="unexpected trivy version"):
        parse_version_text("trivy version 0.76.0\n")
    with pytest.raises(GateError, match="no output"):
        parse_version_text(" \n")
    document = _document()
    document["Trivy"] = {"Version": "0.75.0"}
    with pytest.raises(GateError, match="scanner version is not 0.76.0"):
        parse_trivy_document(document, ROOT)


def test_malformed_json_and_missing_results_fail() -> None:
    with pytest.raises(GateError, match="missing SchemaVersion"):
        parse_trivy_document({}, ROOT)
    document = _document()
    document["Results"] = []
    with pytest.raises(GateError, match="missing scan results"):
        parse_trivy_document(document, ROOT)
    document = _document()
    document["Results"] = None
    with pytest.raises(GateError, match="missing scan results"):
        parse_trivy_document(document, ROOT)
    document = _document()
    document["SchemaVersion"] = 1
    with pytest.raises(GateError, match="schema is not version 2"):
        parse_trivy_document(document, ROOT)
    broken = _document()
    broken["Results"][0]["MisconfSummary"]["Failures"] = 2
    with pytest.raises(GateError, match="reported 2 failures"):
        parse_trivy_document(broken, ROOT)


def test_incorrect_scope_fails() -> None:
    document = _document()
    document["ArtifactName"] = "infra/terraform/modules"
    with pytest.raises(GateError, match="this gate requires infra/terraform"):
        parse_trivy_document(document, ROOT)
    document = _document()
    document["Results"] = [
        result for result in document["Results"] if result["Target"] != "environments/production"
    ]
    with pytest.raises(GateError, match="did not scan required Terraform roots"):
        parse_trivy_document(document, ROOT)
    document = _document()
    document["Results"].append(
        {
            "Target": "../secrets.tf",
            "Class": "config",
            "Type": "terraform",
            "MisconfSummary": {"Successes": 0, "Failures": 0},
        }
    )
    with pytest.raises(GateError, match="outside infra/terraform"):
        parse_trivy_document(document, ROOT)
    document = _document()
    document["Results"].append(
        {
            "Target": "account/terraform.tfstate",
            "Class": "config",
            "Type": "terraform",
            "MisconfSummary": {"Successes": 0, "Failures": 0},
        }
    )
    with pytest.raises(GateError, match="state"):
        parse_trivy_document(document, ROOT)
    document = _document()
    document["Results"][0]["Type"] = "dockerfile"
    with pytest.raises(GateError, match="not a Terraform misconfiguration"):
        parse_trivy_document(document, ROOT)


def test_current_module_tree_is_reachable_from_the_three_roots() -> None:
    reachable = referenced_directories(ROOT, set(REQUIRED_ROOTS))
    assert terraform_directories(ROOT) <= reachable
    assert parse_trivy_document(_document(), ROOT) == []


def test_unknown_finding_fails_and_exact_exception_passes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    finding = _finding()
    assert compare([finding], []) == [f"unbaselined IaC finding: {finding.label()}"]
    assert "resource=" in finding.label()
    assert finding.path in finding.label()
    empty = _write_baseline(tmp_path / "empty.json", _baseline())
    assert run(empty, scan=lambda: [finding]) == 1
    assert "unbaselined IaC finding:" in capsys.readouterr().err
    exception = _exception_for(finding)
    assert exception_matches(finding, exception)
    assert compare([finding], [exception]) == []
    matched = _write_baseline(tmp_path / "matched.json", _baseline(exceptions=[exception]))
    assert run(matched, scan=lambda: [finding]) == 0
    assert "OK: no unbaselined IaC findings" in capsys.readouterr().out


def test_stale_and_excess_exceptions_fail() -> None:
    finding = _finding()
    other = _finding(caller_path="infra/terraform/environments/staging/main.tf")
    stale = compare([], [_exception_for(finding)])
    assert len(stale) == 1
    assert stale[0].startswith("stale baseline exception 0:")
    mixed = compare([other], [_exception_for(finding)])
    assert any(line.startswith("stale baseline exception") for line in mixed)
    assert any(line.startswith("unbaselined IaC finding") for line in mixed)
    excess = compare([finding], [_exception_for(finding), _exception_for(finding)])
    assert len(excess) == 1
    assert excess[0].startswith("excess baseline exception 1:")


def test_wildcard_and_malformed_exceptions_are_rejected(tmp_path: Path) -> None:
    finding = _finding()
    for field, value in (
        ("path", "infra/terraform/modules/*.tf"),
        ("path", "*"),
        ("rule_id", "AWS-*"),
        ("resource", "aws_*"),
        ("caller_path", "infra/terraform/environments/*"),
        ("namespace", "builtin.*"),
        ("title", "any *"),
    ):
        payload = _baseline(exceptions=[_exception_for(finding, **{field: value})])
        path = _write_baseline(tmp_path / f"{field}.json", payload)
        with pytest.raises(GateError, match="wildcard|malformed|outside"):
            load_baseline(path)
    bad_fingerprint = _exception_for(finding)
    bad_fingerprint["fingerprint"] = "a" * 64
    path = _write_baseline(tmp_path / "fingerprint.json", _baseline(exceptions=[bad_fingerprint]))
    with pytest.raises(GateError, match="fingerprint does not match"):
        load_baseline(path)
    for rationale in ("waived", "risk_accepted", "accepted"):
        unknown = _exception_for(finding, rationale=rationale)
        path = _write_baseline(tmp_path / f"{rationale}.json", _baseline(exceptions=[unknown]))
        with pytest.raises(GateError, match="rationale"):
            load_baseline(path)
    missing = _exception_for(finding)
    del missing["resource"]
    path = _write_baseline(tmp_path / "missing.json", _baseline(exceptions=[missing]))
    with pytest.raises(GateError, match="missing"):
        load_baseline(path)
    extra = _exception_for(finding)
    extra["ticket"] = "SEC-1"
    path = _write_baseline(tmp_path / "extra.json", _baseline(exceptions=[extra]))
    with pytest.raises(GateError, match="unknown fields"):
        load_baseline(path)


def test_severity_counts_include_every_rank() -> None:
    findings = [
        _finding(),
        _finding(severity="HIGH", rule_id="AWS-0053", namespace="builtin.aws.elb.aws0053"),
        _finding(severity="MEDIUM", rule_id="AWS-0178", namespace="builtin.aws.ec2.aws0178"),
        _finding(severity="LOW", rule_id="AWS-0017", namespace="builtin.aws.cloudwatch.aws0017"),
        _finding(severity="UNKNOWN", rule_id="AWS-0001", namespace="builtin.aws.ec2.aws0001"),
    ]
    assert severity_counts(findings) == {
        "UNKNOWN": 1,
        "LOW": 1,
        "MEDIUM": 1,
        "HIGH": 1,
        "CRITICAL": 1,
    }
    text = format_summary(findings, [], status="FAIL")
    assert "critical=1" in text
    assert "high=1" in text
    assert "medium=1" in text
    assert "low=1" in text
    assert "unknown=1" in text
    assert "findings=5" in text
    parsed = parse_trivy_document(_document(findings), ROOT)
    assert severity_counts(parsed) == severity_counts(findings)
    assert {item.resource for item in parsed} == {findings[0].resource}
    assert {item.path for item in parsed} == {findings[0].path}


def test_scanner_cannot_silently_ignore_findings(tmp_path: Path) -> None:
    with pytest.raises(GateError, match="ignored a finding"):
        assert_scanner_stderr(
            'INFO [terraform executor] Ignore finding rule="aws-ec2-no-public-ip-subnet"\n'
        )
    with pytest.raises(GateError, match="reported an error"):
        assert_scanner_stderr("ERROR scan failed\n")
    assert_scanner_stderr(
        'ERROR [misconfig] Falling back to embedded checks err="cache does not exist"\n'
        "WARN variable values were not found\n"
    )
    tree = tmp_path / "infra" / "terraform" / "modules" / "example"
    tree.mkdir(parents=True)
    ignored = tree / "main.tf"
    ignored.write_text('cidr = "0.0.0.0/0" # trivy:ignore:AWS-0104\n', encoding="utf-8")
    with pytest.raises(GateError, match="trivy:ignore"):
        assert_no_scanner_ignores(tmp_path)
    (tmp_path / ".trivyignore").write_text("AWS-0104\n", encoding="utf-8")
    ignored.write_text('cidr = "10.0.0.0/8"\n', encoding="utf-8")
    with pytest.raises(GateError, match="ignore file"):
        assert_no_scanner_ignores(tmp_path)
    document = _document([_finding()])
    item = document["Results"][-1]["Misconfigurations"][0]
    item["Status"] = "IGNORED"
    with pytest.raises(GateError, match="unexpected status"):
        parse_trivy_document(document, ROOT)


_API_HTTPS_FINGERPRINTS = {
    "infra/terraform/environments/staging/main.tf": (
        "9e8497f7734dd975357b9c7cb37bf14d95e1267bdbf294098a2aeecfce90c9e9"
    ),
    "infra/terraform/environments/production/main.tf": (
        "d0ad7490521db278f1841a1efb7c6c40f0656309d04d97c8f8ed345dcfd1d277"
    ),
}
_API_HTTPS_REASON_MARKERS = (
    "api_https",
    "TCP 443 to 0.0.0.0/0",
    "private EC2 application host",
    "NAT egress architecture",
    "required external HTTPS services",
    "explicit owner risk acceptance",
)


def _api_https_finding(caller_path: str) -> Finding:
    return _finding(
        start_line=77,
        end_line=77,
        resource="aws_vpc_security_group_egress_rule.api_https",
        caller_path=caller_path,
    )


def test_committed_api_https_acceptances_are_exact(tmp_path: Path) -> None:
    assert RATIONALES == ("false_positive", "not_applicable", "accepted_risk")
    data = load_baseline(BASELINE)
    assert data["scanner_version"] == TRIVY_VERSION
    assert data["scope"] == SCAN_RELATIVE
    exceptions = data["exceptions"]
    assert len(exceptions) == 2
    by_caller = {item["caller_path"]: item for item in exceptions}
    assert set(by_caller) == set(_API_HTTPS_FINGERPRINTS)
    findings: list[Finding] = []
    for caller_path, digest in _API_HTTPS_FINGERPRINTS.items():
        item = by_caller[caller_path]
        assert item["fingerprint"] == digest
        assert item["rationale"] == "accepted_risk"
        assert item["rule_id"] == "AWS-0104"
        assert item["severity"] == "CRITICAL"
        assert item["resource"] == "aws_vpc_security_group_egress_rule.api_https"
        assert item["path"] == "infra/terraform/modules/security_groups/main.tf"
        assert item["start_line"] == 77
        assert item["end_line"] == 77
        assert item["caller_resource"] == "module.security_groups"
        assert item["namespace"] == "builtin.aws.ec2.aws0104"
        assert "*" not in json.dumps(item)
        assert "?" not in json.dumps(item)
        assert len(item["reason"]) <= 300
        for marker in _API_HTTPS_REASON_MARKERS:
            assert marker in item["reason"]
        finding = _api_https_finding(caller_path)
        assert finding.fingerprint == digest
        assert exception_matches(finding, item)
        findings.append(finding)
    assert compare(findings, exceptions) == []
    other_critical = _finding()
    assert other_critical.severity == "CRITICAL"
    assert other_critical.resource != "aws_vpc_security_group_egress_rule.api_https"
    regressions = compare([*findings, other_critical], exceptions)
    assert regressions == [f"unbaselined IaC finding: {other_critical.label()}"]
    high = _finding(
        severity="HIGH",
        rule_id="AWS-0053",
        namespace="builtin.aws.elb.aws0053",
        resource="aws_lb.this",
        path="infra/terraform/modules/alb/main.tf",
        start_line=3,
        end_line=3,
    )
    medium = _finding(
        severity="MEDIUM",
        rule_id="AWS-0178",
        namespace="builtin.aws.ec2.aws0178",
    )
    low = _finding(
        severity="LOW",
        rule_id="AWS-0017",
        namespace="builtin.aws.cloudwatch.aws0017",
    )
    remaining = compare([*findings, other_critical, high, medium, low], exceptions)
    assert [line for line in remaining if "unbaselined" in line] == [
        f"unbaselined IaC finding: {item.label()}"
        for item in sorted(
            (other_critical, high, medium, low),
            key=lambda item: (item.path, item.start_line, item.rule_id, item.caller_path),
        )
    ]
    stale = compare([], exceptions)
    assert len(stale) == 2
    assert all(line.startswith("stale baseline exception") for line in stale)
    one_caller = compare(findings[:1], exceptions)
    assert sum(line.startswith("stale baseline exception") for line in one_caller) == 1
    assert not any(line.startswith("unbaselined IaC finding") for line in one_caller)
    changed = json.loads(json.dumps(exceptions))
    changed[0]["fingerprint"] = "b" * 64
    path = _write_baseline(tmp_path / "changed-fingerprint.json", _baseline(exceptions=changed))
    with pytest.raises(GateError, match="fingerprint does not match"):
        load_baseline(path)
    broad = json.loads(json.dumps(exceptions[0]))
    broad["resource"] = "aws_*"
    path = _write_baseline(tmp_path / "broad.json", _baseline(exceptions=[broad]))
    with pytest.raises(GateError, match="wildcard"):
        load_baseline(path)
    assert run(BASELINE, scan=lambda: findings) == 0
    assert run(BASELINE, scan=lambda: [*findings, other_critical]) == 1
    assert run(BASELINE, scan=lambda: []) == 1


def test_ci_runs_the_gate_in_the_terraform_job_without_aws() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "bash scripts/security/install_trivy.sh" in text
    assert "python scripts/check_iac_security_baseline.py" in text
    assert "tests/unit/test_sprint40_iac_security_baseline.py" in text
    terraform = text.split("name: Terraform fmt and validate", 1)[1].split("\n  compose:", 1)[0]
    assert "terraform fmt -check -recursive infra/terraform" in terraform
    assert "terraform validate" in terraform
    assert "Install Trivy 0.76.0" in terraform
    assert "IaC security scan (Trivy baseline gate)" in terraform
    assert "continue-on-error" not in terraform
    assert "aquasecurity/trivy-action" not in text.lower()
    assert "tfsec" not in text.lower()
    assert "checkov" not in text.lower()
    assert "id-token: write" not in text
    assert "terraform apply" not in text
    validate = terraform.index("terraform validate")
    gate = terraform.index("IaC security scan (Trivy baseline gate)")
    assert validate < gate
