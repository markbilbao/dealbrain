"""Container vulnerability gate: pinned local Grype over one Docker image."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from scripts.check_container_vuln_baseline import (
    GRYPE_LINUX_AMD64_SHA256,
    GRYPE_VERSION,
    TARGET_TYPE,
    Finding,
    GateError,
    _validate_exception,
    assert_db_fresh,
    assert_grype_policy,
    assert_report_configuration,
    compare,
    finding_from_match,
    gate_environment,
    load_baseline,
    local_reference,
    package_count,
    parse_json_document,
    parse_report,
    require_executable,
    require_version,
    run_gate,
    scanner_command,
)

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github/workflows/ci.yml"
BUILD = ROOT / ".github/workflows/build-image.yml"
POLICY = ROOT / "scripts/security/grype.yaml"
INSTALL = ROOT / "scripts/security/install_grype.sh"
BASELINE = ROOT / "tests/security/baselines/grype-image.baseline.json"
IMAGE = "docker:dealbrain:ci-local"
REFERENCE = "dealbrain:ci-local"
ARCHIVE_SHA = "ab" * 32
IMAGE_ID = "sha256:" + ("a" * 64)


def _baseline(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "version": 1,
        "scanner": "grype",
        "scanner_version": GRYPE_VERSION,
        "target_type": TARGET_TYPE,
        "max_allowed_db_built_age": "120h",
        "exceptions": [],
    }
    payload.update(overrides)
    return payload


def _write_baseline(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _finding(**overrides: object) -> Finding:
    payload: dict[str, object] = {
        "vulnerability_id": "CVE-2026-0001",
        "package_name": "zlib1g",
        "package_version": "1:1.3.1-1",
        "package_type": "deb",
        "package_purl": "pkg:deb/debian/zlib1g@1:1.3.1-1",
        "severity": "Low",
        "fix_state": "not-fixed",
        "fixed_versions": (),
    }
    payload.update(overrides)
    versions = payload["fixed_versions"]
    if isinstance(versions, list):
        payload["fixed_versions"] = tuple(versions)
    return Finding(**payload)  # type: ignore[arg-type]


def _exception_for(item: Finding, **overrides: object) -> dict:
    payload: dict[str, object] = {
        "id": "GRYPE-001",
        "vulnerability_id": item.vulnerability_id,
        "package_name": item.package_name,
        "package_version": item.package_version,
        "package_type": item.package_type,
        "package_purl": item.package_purl,
        "severity": item.severity,
        "fix_state": item.fix_state,
        "fixed_versions": list(item.fixed_versions),
        "fingerprint": item.fingerprint(),
        "rationale": "metadata_mismatch",
        "reason": "Reviewed: this exact package build does not ship the affected file.",
    }
    payload.update(overrides)
    return payload


def _fresh_built() -> str:
    built = datetime.now(UTC) - timedelta(hours=2)
    return built.strftime("%Y-%m-%dT%H:%M:%SZ")


def _db_status() -> dict:
    return {
        "valid": True,
        "schemaVersion": "v6.1.10",
        "built": _fresh_built(),
        "from": f"https://example.invalid/db.tar.zst?checksum=sha256:{ARCHIVE_SHA}",
        "path": "/tmp/vulnerability.db",
    }


def _configuration() -> dict:
    return {
        "check-for-app-update": False,
        "only-fixed": False,
        "only-notfixed": False,
        "default-image-pull-source": "docker",
        "from": ["docker"],
        "ignore": [],
        "db": {
            "auto-update": True,
            "validate-by-hash-on-start": True,
            "validate-age": True,
            "max-allowed-built-age": 120 * 60 * 60 * 1_000_000_000,
            "require-update-check": True,
        },
    }


def _report(matches: list[dict] | None = None) -> dict:
    return {
        "matches": [] if matches is None else matches,
        "ignoredMatches": [],
        "source": {
            "type": "image",
            "target": {
                "userInput": REFERENCE,
                "tags": [REFERENCE],
                "repoDigests": [],
            },
        },
        "descriptor": {
            "name": "grype",
            "version": GRYPE_VERSION,
            "configuration": _configuration(),
            "db": {"status": _db_status()},
        },
    }


def _parse(report: dict) -> tuple[list[Finding], dict[str, str]]:
    return parse_report(report, IMAGE, (), read_integrity=lambda _status: "xxh64:abc123")


class _Runner:
    def __init__(
        self,
        report_text: str,
        *,
        version: str = GRYPE_VERSION,
        scan_code: int = 0,
        update_code: int = 0,
        packages: int = 4,
        image_ids: list[tuple[str, tuple[str, ...]]] | None = None,
    ) -> None:
        self.report_text = report_text
        self.version = version
        self.scan_code = scan_code
        self.update_code = update_code
        self.packages = packages
        self.image_ids = image_ids or [(IMAGE_ID, ())]
        self.calls: list[list[str]] = []
        self._seen = 0

    def run(self, command: list[str], _env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        if command[-1] == "version":
            return subprocess.CompletedProcess(command, 0, stdout=f"Version: {self.version}\n")
        if command[-1] == "update":
            detail = "" if self.update_code == 0 else "database update check failed"
            return subprocess.CompletedProcess(command, self.update_code, stderr=detail)
        if "status" in command:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(_db_status()))
        if "--file" in command:
            destination = Path(command[command.index("--file") + 1])
            destination.write_text(self.report_text, encoding="utf-8")
            stderr = f"gathered packages packages={self.packages}\n"
            if self.scan_code != 0:
                stderr = "scanner execution failed"
            return subprocess.CompletedProcess(command, self.scan_code, stderr=stderr)
        raise AssertionError(command)

    def identity(self, _reference: str) -> tuple[str, tuple[str, ...]]:
        item = self.image_ids[min(self._seen, len(self.image_ids) - 1)]
        self._seen += 1
        return item


def _patch(monkeypatch: pytest.MonkeyPatch, runner: _Runner) -> None:
    monkeypatch.setattr(
        "scripts.check_container_vuln_baseline._run",
        runner.run,
    )
    monkeypatch.setattr(
        "scripts.check_container_vuln_baseline.local_image_identity",
        runner.identity,
    )
    monkeypatch.setattr(
        "scripts.check_container_vuln_baseline.require_executable",
        lambda: "grype",
    )
    monkeypatch.setattr(
        "scripts.check_container_vuln_baseline.integrity_checksum",
        lambda _status: "xxh64:abc123",
    )


def _step(text: str, name: str) -> int:
    needle = f"- name: {name}"
    assert needle in text
    return text.index(needle)


def test_scanner_version_and_checksum_are_pinned() -> None:
    assert GRYPE_VERSION == "0.120.1"
    assert GRYPE_LINUX_AMD64_SHA256 == (
        "0a9ee97ef5ae2ee953b0a80098105052e846cdbe319a57d808b519c33cd1343d"
    )
    script = INSTALL.read_text(encoding="utf-8")
    assert f'GRYPE_VERSION="{GRYPE_VERSION}"' in script
    assert GRYPE_LINUX_AMD64_SHA256 in script
    assert "curl | sh" not in script
    assert "latest" not in script
    assert script.index("sha256sum -c") < script.index("tar -xzf")
    assert "https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}" in script
    committed = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert committed["scanner"] == "grype"
    assert committed["scanner_version"] == "0.120.1"
    assert committed["target_type"] == "local_docker_image"
    assert committed["exceptions"] == []


def test_malformed_scanner_json_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(GateError, match="JSON did not parse"):
        parse_json_document("{", "grype")
    with pytest.raises(GateError, match="trailing data"):
        parse_json_document('{"matches": []} trailing', "grype")
    runner = _Runner("{")
    _patch(monkeypatch, runner)
    baseline = _write_baseline(tmp_path / "baseline.json", _baseline())
    with pytest.raises(GateError, match="JSON did not parse"):
        run_gate(IMAGE, baseline, POLICY)


def test_scanner_execution_failure_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _Runner("{}", scan_code=2)
    _patch(monkeypatch, runner)
    baseline = _write_baseline(tmp_path / "baseline.json", _baseline())
    with pytest.raises(GateError, match="grype scan failed"):
        run_gate(IMAGE, baseline, POLICY)


def test_wrong_scanner_version_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(GateError, match="installed grype is 0.9.0"):
        require_version("Version: 0.9.0\n")
    runner = _Runner(json.dumps(_report()), version="0.9.0")
    _patch(monkeypatch, runner)
    baseline = _write_baseline(tmp_path / "baseline.json", _baseline())
    with pytest.raises(GateError, match="installed grype is 0.9.0"):
        run_gate(IMAGE, baseline, POLICY)
    report = _report()
    report["descriptor"]["version"] = "0.9.0"
    with pytest.raises(GateError, match="scanner version is not 0.120.1"):
        _parse(report)


def test_baseline_version_mismatch_fails(tmp_path: Path) -> None:
    path = _write_baseline(tmp_path / "baseline.json", _baseline(version=2))
    with pytest.raises(GateError, match="baseline version must be 1"):
        load_baseline(path)
    path = _write_baseline(tmp_path / "other.json", _baseline(scanner_version="0.9.0"))
    with pytest.raises(GateError, match="scanner_version must be 0.120.1"):
        load_baseline(path)


def test_wildcard_vulnerability_id_and_package_are_rejected() -> None:
    item = _exception_for(_finding())
    item["vulnerability_id"] = "CVE-*"
    with pytest.raises(GateError, match="wildcard"):
        _validate_exception(0, item)
    item = _exception_for(_finding())
    item["package_name"] = "zlib*"
    with pytest.raises(GateError, match="wildcard"):
        _validate_exception(0, item)
    match = {
        "vulnerability": {
            "id": "CVE-*",
            "severity": "Low",
            "fix": {"state": "not-fixed", "versions": []},
        },
        "artifact": {
            "name": "zlib1g",
            "version": "1",
            "type": "deb",
            "purl": "pkg:deb/debian/zlib1g@1",
        },
    }
    with pytest.raises(GateError, match="wildcard"):
        finding_from_match(match)


def _match(fix_state: object | None, *, include_fix: bool = True) -> dict:
    vulnerability: dict[str, object] = {
        "id": "CVE-2025-60876",
        "severity": "Medium",
    }
    if include_fix:
        vulnerability["fix"] = {"state": fix_state, "versions": []}
    return {
        "vulnerability": vulnerability,
        "artifact": {
            "name": "busybox",
            "version": "1.37.0-r31",
            "type": "apk",
            "purl": "pkg:apk/alpine/busybox@1.37.0-r31",
        },
    }


def test_empty_fix_state_normalizes_to_unknown() -> None:
    empty = finding_from_match(_match(""))
    explicit = finding_from_match(_match("unknown"))
    assert empty.fix_state == "unknown"
    assert explicit.fix_state == "unknown"
    assert empty.fingerprint() == explicit.fingerprint()
    for state in ("fixed", "not-fixed", "wont-fix", "unknown"):
        assert finding_from_match(_match(state)).fix_state == state
    for rejected in (" ", "ignored", None, 0, ["fixed"]):
        with pytest.raises(GateError, match="unexpected fix state"):
            finding_from_match(_match(rejected))
    with pytest.raises(GateError, match="missing fix metadata"):
        finding_from_match(_match("", include_fix=False))
    missing_object = _match("")
    missing_object["vulnerability"]["fix"] = None
    with pytest.raises(GateError, match="missing fix metadata"):
        finding_from_match(missing_object)


def test_new_unbaselined_finding_fails() -> None:
    item = _finding()
    regressions = compare([item], [])
    assert regressions == [f"unbaselined container finding: {item.label()}"]


def test_exact_exception_matches_only_the_reviewed_identity() -> None:
    item = _finding()
    assert compare([item], [_exception_for(item)]) == []
    other_cve = _finding(vulnerability_id="CVE-2026-0002")
    other_package = _finding(package_name="openssl")
    other_version = _finding(package_version="1:1.3.1-2")
    allowed = [_exception_for(item)]
    for unexpected in (other_cve, other_package, other_version):
        regressions = compare([unexpected], allowed)
        assert any(line.startswith("stale baseline exception:") for line in regressions)
        assert any(line.startswith("unbaselined container finding:") for line in regressions)
        assert unexpected.label() in "\n".join(regressions)
        assert item.label() not in "\n".join(
            line for line in regressions if line.startswith("unbaselined")
        )


def test_stale_exception_fails() -> None:
    item = _finding()
    regressions = compare([], [_exception_for(item)])
    assert regressions == [f"stale baseline exception: {item.label()}"]


def test_duplicate_finding_multiplicity_is_respected() -> None:
    item = _finding()
    first = _exception_for(item)
    second = _exception_for(item, id="GRYPE-002")
    assert compare([item, item], [first]) == [f"unbaselined container finding: {item.label()}"]
    excess = compare([item], [first, second])
    assert len(excess) == 1
    assert excess[0].startswith("duplicate excess exception:")
    assert compare([item, item], [first, second]) == []


def test_high_and_critical_are_not_hidden_by_a_generic_exception() -> None:
    generic = _exception_for(_finding())
    high = _finding(severity="High", vulnerability_id="CVE-2026-1111", package_name="libc6")
    critical = _finding(
        severity="Critical",
        vulnerability_id="CVE-2026-2222",
        package_name="openssl",
    )
    high_lines = compare([high], [generic])
    critical_lines = compare([critical], [generic])
    assert any(line.startswith("unresolved HIGH finding:") for line in high_lines)
    assert any(line.startswith("unbaselined container finding:") for line in high_lines)
    assert any(line.startswith("unresolved CRITICAL finding:") for line in critical_lines)
    assert any(line.startswith("unbaselined container finding:") for line in critical_lines)
    hidden = _exception_for(high)
    hidden["vulnerability_id"] = "*"
    with pytest.raises(GateError, match="wildcard"):
        _validate_exception(0, hidden)
    hidden = _exception_for(critical)
    hidden["package_name"] = "*"
    with pytest.raises(GateError, match="wildcard"):
        _validate_exception(0, hidden)
    accepted = _exception_for(high)
    accepted["rationale"] = "accepted_risk"
    with pytest.raises(GateError, match="rationale"):
        _validate_exception(0, accepted)


def test_database_freshness_and_app_update_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = POLICY.read_text(encoding="utf-8")
    assert_grype_policy(policy)
    assert "validate-age: true" in policy
    assert "validate-by-hash-on-start: true" in policy
    assert "require-update-check: true" in policy
    assert "max-allowed-built-age: 120h" in policy
    assert "check-for-app-update: false" in policy
    assert "only-fixed: false" in policy
    monkeypatch.setenv("GRYPE_CHECK_FOR_APP_UPDATE", "true")
    monkeypatch.setenv("GRYPE_DB_VALIDATE_AGE", "false")
    monkeypatch.setenv("GRYPE_ONLY_FIXED", "true")
    env = gate_environment()
    assert env["GRYPE_CHECK_FOR_APP_UPDATE"] == "false"
    assert env["GRYPE_DB_VALIDATE_AGE"] == "true"
    assert env["GRYPE_DB_REQUIRE_UPDATE_CHECK"] == "true"
    assert env["GRYPE_DB_MAX_ALLOWED_BUILT_AGE"] == "120h"
    assert env["GRYPE_ONLY_FIXED"] == "false"
    now = datetime(2026, 10, 16, 12, tzinfo=UTC)
    assert_db_fresh(datetime(2026, 10, 16, 6, tzinfo=UTC), now=now)
    with pytest.raises(GateError, match="older than 120h"):
        assert_db_fresh(now - timedelta(hours=121), now=now)
    report = _report()
    report["descriptor"]["configuration"]["check-for-app-update"] = True
    with pytest.raises(GateError, match="application update checking is not disabled"):
        assert_report_configuration(report["descriptor"]["configuration"])
    report = _report()
    report["descriptor"]["configuration"]["db"]["validate-age"] = False
    with pytest.raises(GateError, match="does not validate vulnerability database age"):
        assert_report_configuration(report["descriptor"]["configuration"])


def test_local_docker_source_does_not_pull_a_registry_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = scanner_command("grype", REFERENCE, tmp_path / "out.json", POLICY)
    assert command[command.index("--from") + 1] == "docker"
    assert command[-1] == REFERENCE
    assert "docker:dealbrain:ci-local" not in command
    assert "pull" not in command
    with pytest.raises(GateError, match="docker: local source"):
        local_reference("registry:ghcr.io/example/dealbrain:sha-abc")
    with pytest.raises(GateError, match="not one local docker image"):
        local_reference("docker:registry:ghcr.io/example/dealbrain:sha-abc")
    runner = _Runner(json.dumps(_report()))

    def missing(_reference: str) -> tuple[str, tuple[str, ...]]:
        raise GateError(f"requested local image is missing: {_reference}")

    _patch(monkeypatch, runner)
    monkeypatch.setattr("scripts.check_container_vuln_baseline.local_image_identity", missing)
    baseline = _write_baseline(tmp_path / "baseline.json", _baseline())
    with pytest.raises(GateError, match="requested local image is missing"):
        run_gate(IMAGE, baseline, POLICY)
    assert not any("--file" in call for call in runner.calls)
    changed = _Runner(
        json.dumps(_report()),
        image_ids=[(IMAGE_ID, ()), ("sha256:" + ("b" * 64), ())],
    )
    _patch(monkeypatch, changed)
    with pytest.raises(GateError, match="unexpected registry fallback"):
        run_gate(IMAGE, baseline, POLICY)


def test_missing_executable_and_database_update_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts.check_container_vuln_baseline.shutil.which", lambda _name: None)
    with pytest.raises(GateError, match="missing Grype executable"):
        require_executable()
    runner = _Runner(json.dumps(_report()), update_code=1)
    _patch(monkeypatch, runner)
    baseline = _write_baseline(tmp_path / "baseline.json", _baseline())
    with pytest.raises(GateError, match="vulnerability database update failed"):
        run_gate(IMAGE, baseline, POLICY)
    assert not any("--file" in call for call in runner.calls)


def test_clean_local_scan_summary_omits_the_raw_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _Runner(json.dumps(_report()), packages=11)
    _patch(monkeypatch, runner)
    baseline = _write_baseline(tmp_path / "baseline.json", _baseline())
    text = run_gate(IMAGE, baseline, POLICY)
    captured = capsys.readouterr()
    assert "container_vuln_gate: OK" in text
    assert "scanner=grype" in text
    assert "scanner_version=0.120.1" in text
    assert f"target={IMAGE}" in text
    assert "packages=11" in text
    assert "findings=0" in text
    assert "exceptions=0" in text
    assert "db_built=" in text
    assert "matches" not in captured.out
    assert package_count("gathered packages packages=11\n") == 11
    with pytest.raises(GateError, match="exactly one package count"):
        package_count("")


def test_ci_scans_the_local_image_and_does_not_publish() -> None:
    text = CI.read_text(encoding="utf-8")
    gate = _step(text, "Container vulnerability gate")
    assert _step(text, "Smoke-import production runtime modules") < gate
    assert _step(text, "Verify image exists (no migrate at build)") < gate
    assert "docker:dealbrain:ci-${{ github.sha }}" in text
    assert "scripts/check_container_vuln_baseline.py" in text
    assert "bash scripts/security/install_grype.sh" in text
    assert "push: false" in text
    assert "packages: write" not in text
    assert "docker push" not in text
    assert "docker/login-action" not in text
    assert "docker pull" not in text
    assert "security-events" not in text
    lowered = text.lower()
    for hosted in (
        "anchore/scan-action",
        "anchore/grype-action",
        "aquasecurity/trivy-action",
        "github/codeql-action",
        "docker/scout-action",
    ):
        assert hosted not in lowered
    assert "tests/unit/test_sprint40_container_vuln_baseline.py" in text


def test_release_workflow_scans_before_push_and_keeps_the_registry_digest() -> None:
    text = BUILD.read_text(encoding="utf-8")
    order = [
        "Resolve commit SHA and CI run id",
        "Checkout exact commit",
        "Prepare OCI metadata",
        "Build release image locally",
        "Verify local release image",
        "Install Grype 0.120.1",
        "Container vulnerability gate",
        "Log in to GHCR",
        "Push scanned release image",
        "Capture and validate image digest",
        "Create release manifest",
    ]
    indexes = [_step(text, name) for name in order]
    assert indexes == sorted(indexes)
    gate = indexes[order.index("Container vulnerability gate")]
    push = indexes[order.index("Push scanned release image")]
    assert text.count("docker/build-push-action") == 1
    assert text.index("docker/build-push-action") < gate
    assert "push: false" in text
    assert "load: true" in text
    assert "push: true" not in text
    assert "docker build " not in text[gate:]
    assert text.index("docker push") > gate
    assert text.index("docker push") == text.rindex("docker push")
    build = text[indexes[order.index("Build release image locally")] : gate]
    assert "tag_sha" in build
    assert "org.opencontainers.image.source" in build
    assert "org.opencontainers.image.revision" in build
    assert "org.opencontainers.image.created" in build
    assert "org.opencontainers.image.version" in build
    assert "docker:${IMAGE}:${TAG}" in text
    assert "tag_sha=sha-" in text
    after_push = text[push:]
    assert "RepoDigests" in after_push
    assert "sha256:[0-9a-f]{64}" in after_push
    assert "imagetools inspect" in after_push
    assert "steps.digest.outputs.image_digest" in text
    assert "steps.push.outputs.digest" not in text
    assert "if: always()" not in text[gate:push]
    assert "docker pull" not in text
    assert "security-events" not in text
    lowered = text.lower()
    for hosted in (
        "anchore/scan-action",
        "anchore/grype-action",
        "aquasecurity/trivy-action",
        "github/codeql-action",
    ):
        assert hosted not in lowered
    assert "trivy" not in lowered
    assert "checkov" not in lowered
    assert "tfsec" not in lowered
