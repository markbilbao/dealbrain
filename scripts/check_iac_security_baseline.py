#!/usr/bin/env python3
"""Terraform misconfiguration gate for infra/terraform.

The scanner is the pinned Trivy 0.76.0 binary. ``scripts/security/install_trivy.sh``
verifies the official linux/amd64 archive checksum
``e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7``
before it extracts that binary. This gate does not download Trivy and does
not trust a floating checks bundle: each run uses an empty cache directory
and ``--skip-check-update``, so the checks embedded in that binary are the
rule source.

The scan target is ``infra/terraform`` only. The gate parses Trivy's JSON
itself. ``.trivyignore``, ``trivy.yaml``, and ``#trivy:ignore`` are rejected.
A finding is accepted only when the baseline names that same rule, severity,
title, file, line range, resource, caller, namespace, and fingerprint.
The baseline starts empty. Critical and high findings are not given a
convenience exception by this gate.

Usage:
    uv run python scripts/check_iac_security_baseline.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "security" / "baselines" / "trivy-iac.baseline.json"
TRIVY_VERSION = "0.76.0"
TRIVY_LINUX_AMD64_SHA256 = "e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7"
SCANNER = "trivy"
SCAN_RELATIVE = "infra/terraform"
SCOPE = "infra/terraform"
CHECKS = "embedded"
SEVERITIES = ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")
RATIONALES = ("false_positive", "not_applicable")
REQUIRED_ROOTS = (
    "account",
    "environments/production",
    "environments/staging",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RULE_ID = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")
_VERSION_LINE = re.compile(r"^Version:\s+(\d+\.\d+\.\d+)$")
_MODULE_SOURCE = re.compile(r"""(?m)^[ \t]*source[ \t]*=[ \t]*"(\.[^"]+)"\s*$""")
_IGNORE_DIRECTIVE = re.compile(r"trivy\s*:\s*ignore", re.IGNORECASE)
_ALLOWED_STDERR_ERROR = "Falling back to embedded checks"
_BASELINE_KEYS = {"version", "scanner", "scanner_version", "scope", "checks", "exceptions"}
_EXCEPTION_KEYS = {
    "rule_id",
    "severity",
    "title",
    "path",
    "start_line",
    "end_line",
    "resource",
    "caller_path",
    "caller_resource",
    "namespace",
    "fingerprint",
    "rationale",
    "reason",
}
_IDENTITY_KEYS = (
    "rule_id",
    "severity",
    "title",
    "path",
    "start_line",
    "end_line",
    "resource",
    "caller_path",
    "caller_resource",
    "namespace",
)


class GateError(Exception):
    """The scan did not finish. CI must fail closed."""


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    title: str
    path: str
    start_line: int
    end_line: int
    resource: str
    caller_path: str
    caller_resource: str
    namespace: str
    fingerprint: str

    def label(self) -> str:
        return (
            f"{self.path}:{self.start_line}-{self.end_line} "
            f"{self.rule_id} {self.severity} resource={self.resource} "
            f"caller={self.caller_path}:{self.caller_resource} "
            f"namespace={self.namespace} sha256={self.fingerprint}"
        )


def scanner_command(output_path: Path, cache_dir: Path, executable: str = "trivy") -> list[str]:
    """Pinned misconfiguration scan. No ignore file, config file, or cloud upload."""
    return [
        executable,
        "config",
        "--config=",
        "--ignorefile=",
        "--disable-telemetry",
        "--skip-version-check",
        "--skip-check-update",
        "--cache-dir",
        str(cache_dir),
        "--misconfig-scanners",
        "terraform",
        "--tf-exclude-downloaded-modules",
        "--skip-dirs",
        "**/.terraform/**",
        "--severity",
        ",".join(SEVERITIES),
        "--exit-code",
        "0",
        "--format",
        "json",
        "--output",
        str(output_path),
        SCAN_RELATIVE,
    ]


def fingerprint_for(identity: dict[str, object]) -> str:
    payload = {key: identity[key] for key in _IDENTITY_KEYS}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {name: 0 for name in SEVERITIES}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def parse_version_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise GateError("trivy version returned no output")
    match = _VERSION_LINE.fullmatch(lines[0])
    if match is None:
        raise GateError(f"unexpected trivy version output: {lines[0]}")
    return match.group(1)


def require_scanner_version(installed: str) -> None:
    if installed != TRIVY_VERSION:
        raise GateError(f"installed trivy is {installed}; this gate requires {TRIVY_VERSION}")


def _reject_wildcard(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise GateError(f"{label} must be one exact string")
    stripped = value.strip()
    if stripped.lower() in {"", "*", "all", "any"} or "*" in value or "?" in value:
        raise GateError(f"{label} must be one exact value, not a wildcard")
    if "\n" in value or ".." in value.split("/"):
        raise GateError(f"{label} is malformed")
    return value


def _exact_line(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise GateError(f"{label} must be one exact line number")
    return value


def _terraform_root(root: Path) -> Path:
    path = root / SCAN_RELATIVE
    if not path.is_dir():
        raise GateError(f"missing scan scope: {SCAN_RELATIVE} is not a directory")
    return path


def terraform_directories(root: Path = ROOT) -> set[str]:
    """Directories under infra/terraform that contain Terraform source."""
    base = _terraform_root(root)
    found: set[str] = set()
    for path in base.rglob("*.tf"):
        if ".terraform" in path.parts or ".git" in path.parts:
            continue
        relative = path.parent.relative_to(base).as_posix()
        if relative != ".":
            found.add(relative)
    if not found:
        raise GateError("missing scan scope: infra/terraform contains no Terraform files")
    return found


def terraform_files(root: Path = ROOT) -> set[str]:
    base = _terraform_root(root)
    found: set[str] = set()
    for path in base.rglob("*.tf"):
        if ".terraform" in path.parts or ".git" in path.parts:
            continue
        found.add(path.relative_to(root).as_posix())
    if not found:
        raise GateError("missing scan scope: infra/terraform contains no Terraform files")
    return found


def assert_no_scanner_ignores(root: Path = ROOT) -> None:
    """The repository baseline is the only exception authority."""
    base = _terraform_root(root)
    for name in (".trivyignore", "trivy.yaml", ".trivy.yaml"):
        if (root / name).exists() or (base / name).exists():
            raise GateError(f"{name} is present; this gate does not accept a Trivy ignore file")
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if path.name in {".trivyignore", "trivy.yaml", ".trivy.yaml"}:
            raise GateError(f"Trivy ignore file is present: {path.relative_to(root).as_posix()}")
        if path.suffix not in {".tf", ".tfvars"}:
            continue
        text = path.read_text(encoding="utf-8")
        if _IGNORE_DIRECTIVE.search(text):
            raise GateError(
                "Terraform source contains a trivy:ignore directive: "
                f"{path.relative_to(root).as_posix()}"
            )


def assert_scanner_stderr(stderr: str) -> None:
    if "Ignore finding" in stderr:
        raise GateError("trivy ignored a finding; suppressions belong in the baseline")
    for raw in stderr.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "FATAL" in line:
            raise GateError(f"trivy failed: {line[:200]}")
        if "ERROR" in line and _ALLOWED_STDERR_ERROR not in line:
            raise GateError(f"trivy reported an error: {line[:200]}")


def _module_dirs_from(directory: Path, relative: str) -> set[str]:
    """Return module directories referenced by ``directory``, relative to the scan root."""
    found: set[str] = set()
    if not directory.is_dir():
        return found
    parts = Path(relative).parts
    if not parts:
        raise GateError("terraform root path is empty")
    scan_root = directory
    for _ in parts:
        scan_root = scan_root.parent
    repo_root = scan_root.parent.parent
    prefix = f"{SCAN_RELATIVE}/"
    for path in directory.glob("*.tf"):
        text = path.read_text(encoding="utf-8")
        for match in _MODULE_SOURCE.finditer(text):
            resolved = (directory / match.group(1)).resolve()
            try:
                repo_relative = resolved.relative_to(repo_root).as_posix()
            except ValueError as exc:
                raise GateError(f"module source escapes infra/terraform: {match.group(1)}") from exc
            if not repo_relative.startswith(prefix) or not resolved.is_dir():
                raise GateError(f"module source escapes infra/terraform: {match.group(1)}")
            found.add(repo_relative.removeprefix(prefix))
    return found


def referenced_directories(root: Path, seeds: set[str]) -> set[str]:
    """Local module directories reachable from scanned Terraform roots."""
    base = _terraform_root(root)
    reachable = set(seeds)
    pending = set(seeds)
    while pending:
        current = pending.pop()
        directory = base / current
        for module_dir in _module_dirs_from(directory, current):
            if module_dir not in reachable:
                reachable.add(module_dir)
                pending.add(module_dir)
    return reachable


def _result_directories(targets: set[str]) -> set[str]:
    found: set[str] = set()
    for target in targets:
        if target.endswith(".tf"):
            parent = Path(target).parent.as_posix()
            if parent != ".":
                found.add(parent)
        else:
            found.add(target)
    return found


def assert_scope(targets: set[str], root: Path = ROOT) -> None:
    missing_roots = [name for name in REQUIRED_ROOTS if name not in targets]
    if missing_roots:
        raise GateError(f"trivy did not scan required Terraform roots: {missing_roots}")
    for target in targets:
        if target.startswith("/") or ".." in target.split("/") or target.startswith("."):
            raise GateError(f"trivy reported a path outside infra/terraform: {target}")
        if ".terraform" in target.split("/") or target.endswith(".tfstate"):
            raise GateError(f"trivy scanned state or a downloaded module: {target}")
        candidate = (_terraform_root(root) / target).resolve()
        try:
            candidate.relative_to(_terraform_root(root).resolve())
        except ValueError as exc:
            raise GateError(f"trivy reported a path outside infra/terraform: {target}") from exc
    reachable = referenced_directories(root, _result_directories(targets))
    missing = sorted(terraform_directories(root) - reachable)
    if missing:
        raise GateError(f"trivy scan scope did not include: {missing}")


def _repo_path(relative: str) -> str:
    raw = relative.replace("\\", "/").strip()
    if raw.startswith("./"):
        raw = raw[2:]
    if (
        not raw
        or raw.startswith("/")
        or raw.startswith(".")
        or ".." in raw.split("/")
        or "*" in raw
        or "?" in raw
    ):
        raise GateError(f"trivy reported a path outside infra/terraform: {relative}")
    prefix = f"{SCAN_RELATIVE}/"
    if raw == SCAN_RELATIVE or raw.startswith(prefix):
        return raw
    return prefix + raw


def _occurrence(item: object, label: str) -> tuple[str, str]:
    if not isinstance(item, dict):
        raise GateError(f"{label} occurrence is not an object")
    filename = item.get("Filename")
    resource = item.get("Resource")
    if not isinstance(filename, str) or not filename.strip():
        raise GateError(f"{label} occurrence is missing a file")
    if not isinstance(resource, str) or not resource.strip():
        raise GateError(f"{label} occurrence is missing a resource")
    return _repo_path(filename), resource.strip()


def _identity_from_misconfiguration(target: str, item: dict) -> dict[str, object]:
    rule_id = item.get("ID")
    if not isinstance(rule_id, str) or _RULE_ID.fullmatch(rule_id) is None:
        raise GateError(f"trivy finding has an unexpected rule id: {rule_id!r}")
    severity = item.get("Severity")
    if severity not in SEVERITIES:
        raise GateError(f"trivy finding {rule_id} has an unexpected severity: {severity!r}")
    title = item.get("Title")
    if not isinstance(title, str) or not title.strip() or "\n" in title or "*" in title:
        raise GateError(f"trivy finding {rule_id} is missing an exact title")
    namespace = item.get("Namespace")
    if not isinstance(namespace, str) or not namespace.startswith("builtin."):
        raise GateError(f"trivy finding {rule_id} has an unexpected namespace")
    if item.get("Type") != "Terraform Security Check":
        raise GateError(f"trivy finding {rule_id} is not a Terraform security check")
    cause = item.get("CauseMetadata")
    if not isinstance(cause, dict):
        raise GateError(f"trivy finding {rule_id} is missing cause metadata")
    start_line = _exact_line(cause.get("StartLine"), f"{rule_id} start line")
    end_line = _exact_line(cause.get("EndLine"), f"{rule_id} end line")
    if end_line < start_line:
        raise GateError(f"trivy finding {rule_id} has a reversed line range")
    if not target.endswith(".tf"):
        raise GateError(f"trivy finding {rule_id} is not anchored to a Terraform file")
    path = _repo_path(target)
    occurrences = cause.get("Occurrences") or []
    if not isinstance(occurrences, list):
        raise GateError(f"trivy finding {rule_id} occurrences are malformed")
    parsed = [_occurrence(entry, rule_id) for entry in occurrences]
    source = [entry for entry in parsed if entry[0] == path]
    callers = [entry for entry in parsed if entry[0] != path]
    if len({entry[1] for entry in source}) > 1:
        raise GateError(f"trivy finding {rule_id} names more than one resource")
    if len(callers) > 1:
        raise GateError(f"trivy finding {rule_id} names more than one caller")
    if source:
        resource = source[0][1]
    else:
        fallback = cause.get("Resource")
        if not isinstance(fallback, str) or not fallback.strip() or "*" in fallback:
            raise GateError(f"trivy finding {rule_id} is missing a resource address")
        resource = fallback.strip()
    if callers:
        caller_path, caller_resource = callers[0]
    else:
        caller_path, caller_resource = path, resource
    return {
        "rule_id": rule_id,
        "severity": severity,
        "title": title.strip(),
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
        "resource": resource,
        "caller_path": caller_path,
        "caller_resource": caller_resource,
        "namespace": namespace,
    }


def parse_trivy_document(data: dict, root: Path = ROOT) -> list[Finding]:
    for key in ("SchemaVersion", "CreatedAt", "ArtifactName", "ArtifactType", "Results", "Trivy"):
        if key not in data:
            raise GateError(f"trivy JSON is missing {key}")
    if data.get("SchemaVersion") != 2:
        raise GateError("trivy JSON schema is not version 2")
    if not isinstance(data.get("CreatedAt"), str) or not data["CreatedAt"].strip():
        raise GateError("trivy JSON CreatedAt is incomplete")
    if data.get("ArtifactName") != SCAN_RELATIVE:
        raise GateError(
            f"trivy scanned {data.get('ArtifactName')!r}; this gate requires {SCAN_RELATIVE}"
        )
    if data.get("ArtifactType") != "filesystem":
        raise GateError("trivy JSON artifact type is not a filesystem scan")
    meta = data.get("Trivy")
    if not isinstance(meta, dict) or meta.get("Version") != TRIVY_VERSION:
        raise GateError(f"trivy JSON scanner version is not {TRIVY_VERSION}")
    results = data.get("Results")
    if not isinstance(results, list) or not results:
        raise GateError("trivy JSON is missing scan results")
    targets: set[str] = set()
    findings: list[Finding] = []
    for result in results:
        if not isinstance(result, dict):
            raise GateError("trivy scan result is not an object")
        target = result.get("Target")
        if not isinstance(target, str) or not target:
            raise GateError("trivy scan result is missing a target")
        if result.get("Class") != "config" or result.get("Type") != "terraform":
            raise GateError(f"trivy result {target} is not a Terraform misconfiguration scan")
        summary = result.get("MisconfSummary")
        if not isinstance(summary, dict):
            raise GateError(f"trivy result {target} is missing a misconfiguration summary")
        failures = summary.get("Failures")
        successes = summary.get("Successes")
        if isinstance(failures, bool) or not isinstance(failures, int) or failures < 0:
            raise GateError(f"trivy result {target} has a malformed failure count")
        if isinstance(successes, bool) or not isinstance(successes, int) or successes < 0:
            raise GateError(f"trivy result {target} has a malformed success count")
        misconfigurations = result.get("Misconfigurations") or []
        if not isinstance(misconfigurations, list):
            raise GateError(f"trivy result {target} misconfigurations are malformed")
        fail_count = 0
        for item in misconfigurations:
            if not isinstance(item, dict):
                raise GateError(f"trivy result {target} has a malformed finding")
            status = item.get("Status")
            if status == "PASS":
                continue
            if status != "FAIL":
                raise GateError(f"trivy result {target} has an unexpected status: {status!r}")
            fail_count += 1
            identity = _identity_from_misconfiguration(target, item)
            findings.append(
                Finding(
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
                    fingerprint=fingerprint_for(identity),
                )
            )
        if fail_count != failures:
            raise GateError(
                f"trivy result {target} reported {failures} failures and {fail_count} findings"
            )
        targets.add(target)
    assert_scope(targets, root)
    return findings


def _validate_exception(index: int, item: object) -> None:
    if not isinstance(item, dict):
        raise GateError(f"baseline exception {index} must be an object")
    extra = set(item) - _EXCEPTION_KEYS
    if extra:
        raise GateError(f"baseline exception {index} has unknown fields: {sorted(extra)}")
    missing = _EXCEPTION_KEYS - set(item)
    if missing:
        raise GateError(f"baseline exception {index} is missing {sorted(missing)}")
    rule_id = _reject_wildcard(item["rule_id"], f"baseline exception {index} rule_id")
    if _RULE_ID.fullmatch(rule_id) is None:
        raise GateError(f"baseline exception {index} rule_id is malformed")
    severity = _reject_wildcard(item["severity"], f"baseline exception {index} severity")
    if severity not in SEVERITIES:
        raise GateError(f"baseline exception {index} severity is not a Trivy rank")
    title = _reject_wildcard(item["title"], f"baseline exception {index} title")
    path = _reject_wildcard(item["path"], f"baseline exception {index} path")
    if not path.startswith(f"{SCAN_RELATIVE}/") or not path.endswith(".tf"):
        raise GateError(f"baseline exception {index} path is outside {SCOPE}")
    caller_path = _reject_wildcard(item["caller_path"], f"baseline exception {index} caller_path")
    if not caller_path.startswith(f"{SCAN_RELATIVE}/") or not caller_path.endswith(".tf"):
        raise GateError(f"baseline exception {index} caller_path is outside {SCOPE}")
    resource = _reject_wildcard(item["resource"], f"baseline exception {index} resource")
    caller_resource = _reject_wildcard(
        item["caller_resource"], f"baseline exception {index} caller_resource"
    )
    namespace = _reject_wildcard(item["namespace"], f"baseline exception {index} namespace")
    if not namespace.startswith("builtin."):
        raise GateError(f"baseline exception {index} namespace is not a Trivy built-in check")
    start_line = _exact_line(item["start_line"], f"baseline exception {index} start_line")
    end_line = _exact_line(item["end_line"], f"baseline exception {index} end_line")
    if end_line < start_line:
        raise GateError(f"baseline exception {index} has a reversed line range")
    digest = item["fingerprint"]
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise GateError(f"baseline exception {index} fingerprint must be one sha256 hex digest")
    identity = {
        "rule_id": rule_id,
        "severity": severity,
        "title": title,
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
        "resource": resource,
        "caller_path": caller_path,
        "caller_resource": caller_resource,
        "namespace": namespace,
    }
    if digest != fingerprint_for(identity):
        raise GateError(f"baseline exception {index} fingerprint does not match its identity")
    rationale = item["rationale"]
    if rationale not in RATIONALES:
        raise GateError(f"baseline exception {index} rationale is not an allowed value")
    reason = item["reason"]
    if not isinstance(reason, str) or not reason.strip() or "\n" in reason or len(reason) > 300:
        raise GateError(f"baseline exception {index} reason must be one short line")
    if "*" in reason or "?" in reason or reason.strip().lower() in {"*", "all", "any", "ignore"}:
        raise GateError(f"baseline exception {index} reason must describe this finding")


def load_baseline(path: Path) -> dict:
    if not path.is_file():
        raise GateError(f"missing IaC security baseline at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"IaC security baseline is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError("IaC security baseline must be a JSON object")
    extra = set(data) - _BASELINE_KEYS
    if extra:
        raise GateError(f"IaC security baseline has unknown fields: {sorted(extra)}")
    if data.get("version") != 1:
        raise GateError("IaC security baseline version must be 1")
    if data.get("scanner") != SCANNER:
        raise GateError("IaC security baseline scanner must be trivy")
    if data.get("scanner_version") != TRIVY_VERSION:
        raise GateError(f"IaC security baseline scanner_version must be {TRIVY_VERSION}")
    if data.get("scope") != SCOPE:
        raise GateError(f"IaC security baseline scope must be {SCOPE}")
    if data.get("checks") != CHECKS:
        raise GateError("IaC security baseline checks must be the embedded Trivy bundle")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        raise GateError("IaC security baseline exceptions must be a list")
    for index, item in enumerate(exceptions):
        _validate_exception(index, item)
    return data


def exception_matches(finding: Finding, exception: dict) -> bool:
    return all(getattr(finding, key) == exception[key] for key in _IDENTITY_KEYS) and (
        finding.fingerprint == exception["fingerprint"]
    )


def compare(findings: list[Finding], exceptions: list[dict]) -> list[str]:
    """Return regressions. One exception can match only one finding."""
    unmatched = list(findings)
    regressions: list[str] = []
    for index, exception in enumerate(exceptions):
        match_at = next(
            (pos for pos, finding in enumerate(unmatched) if exception_matches(finding, exception)),
            None,
        )
        identity = (
            f"{exception['path']}:{exception['start_line']} {exception['rule_id']} "
            f"{exception['severity']} resource={exception['resource']} "
            f"sha256={exception['fingerprint']}"
        )
        if match_at is None:
            kind = (
                "excess baseline exception"
                if any(exception_matches(finding, exception) for finding in findings)
                else "stale baseline exception"
            )
            regressions.append(f"{kind} {index}: {identity}")
        else:
            del unmatched[match_at]
    ordered = sorted(
        unmatched,
        key=lambda item: (
            item.path,
            item.start_line,
            item.rule_id,
            item.caller_path,
            item.resource,
        ),
    )
    regressions.extend(f"unbaselined IaC finding: {finding.label()}" for finding in ordered)
    return regressions


def installed_trivy_version(executable: str) -> str:
    try:
        proc = subprocess.run(
            [executable, "--version"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise GateError("trivy version timed out") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "trivy --version failed").strip()
        raise GateError(detail)
    version = parse_version_text(proc.stdout or "")
    require_scanner_version(version)
    return version


def run_trivy() -> list[Finding]:
    executable = shutil.which("trivy")
    if executable is None:
        raise GateError("trivy is not installed; run scripts/security/install_trivy.sh")
    installed_trivy_version(executable)
    assert_no_scanner_ignores(ROOT)
    with tempfile.TemporaryDirectory(prefix="trivy-iac-") as directory:
        report_path = Path(directory) / "trivy.json"
        cache_dir = Path(directory) / "cache"
        cache_dir.mkdir()
        try:
            proc = subprocess.run(
                scanner_command(report_path, cache_dir, executable),
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            raise GateError("trivy timed out") from exc
        assert_scanner_stderr(proc.stderr or "")
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            tail = detail[-1][:200] if detail else "no output"
            raise GateError(f"trivy failed with exit {proc.returncode}: {tail}")
        if not report_path.is_file():
            raise GateError("trivy did not write the JSON report")
        text = report_path.read_text(encoding="utf-8")
    if not text.strip():
        raise GateError("trivy returned no JSON")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GateError(f"trivy JSON did not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError("trivy JSON was not an object")
    return parse_trivy_document(data, ROOT)


def format_summary(
    findings: list[Finding],
    exceptions: list[dict],
    *,
    status: str,
) -> str:
    counts = severity_counts(findings)
    return "\n".join(
        (
            f"iac_security_gate: {status}",
            f"scanner={SCANNER}",
            f"scanner_version={TRIVY_VERSION}",
            f"scope={SCOPE}",
            f"checks={CHECKS}",
            f"sha256={TRIVY_LINUX_AMD64_SHA256}",
            f"terraform_files={len(terraform_files())}",
            f"findings={len(findings)}",
            f"exceptions={len(exceptions)}",
            f"critical={counts['CRITICAL']}",
            f"high={counts['HIGH']}",
            f"medium={counts['MEDIUM']}",
            f"low={counts['LOW']}",
            f"unknown={counts['UNKNOWN']}",
        )
    )


def run(
    baseline_path: Path = BASELINE_PATH,
    scan: Callable[[], list[Finding]] = run_trivy,
) -> int:
    baseline = load_baseline(baseline_path)
    findings = scan()
    regressions = compare(findings, baseline["exceptions"])
    status = "FAIL" if regressions else "OK"
    print(format_summary(findings, baseline["exceptions"], status=status))
    if regressions:
        print("FAIL: IaC findings are outside the explicit baseline:", file=sys.stderr)
        for line in regressions:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print("OK: no unbaselined IaC findings")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    args = parser.parse_args(argv)
    try:
        return run(args.baseline)
    except GateError as exc:
        print(f"FAIL: IaC security gate did not complete: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
