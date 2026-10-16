#!/usr/bin/env python3
"""Local Grype gate for the DealBrain runtime image.

The scan target is one local Docker image, passed as ``docker:<reference>``.
The gate checks the pinned Grype version, updates and validates the
vulnerability database, parses Grype JSON itself, and compares every finding
with ``tests/security/baselines/grype-image.baseline.json``. Grype's process
exit code is not the verdict. A non-zero exit, invalid JSON, a stale or
unchecked database, a registry pull, or a finding outside the baseline fails
closed.

The vulnerability database is refreshed on purpose. Determinism here is the
pinned scanner, the verified binary, the explicit local-image scope, and the
exact baseline comparison. The database is not committed.

Usage:
    uv run python scripts/check_container_vuln_baseline.py --image docker:dealbrain:ci-local
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "security" / "baselines" / "grype-image.baseline.json"
POLICY_PATH = ROOT / "scripts" / "security" / "grype.yaml"
GRYPE_VERSION = "0.120.1"
GRYPE_LINUX_AMD64_SHA256 = "0a9ee97ef5ae2ee953b0a80098105052e846cdbe319a57d808b519c33cd1343d"
GRYPE_LINUX_AMD64_ASSET = "grype_0.120.1_linux_amd64.tar.gz"
SCANNER = "grype"
TARGET_TYPE = "local_docker_image"
DB_MAX_AGE = timedelta(hours=120)
DB_MAX_AGE_LABEL = "120h"
SEVERITIES = ("Critical", "High", "Medium", "Low", "Negligible", "Unknown")
BLOCKING_SEVERITIES = {"Critical": "CRITICAL", "High": "HIGH"}
FIX_STATES = ("fixed", "not-fixed", "wont-fix", "unknown")
RATIONALES = ("false_positive", "not_applicable", "metadata_mismatch")
_BASELINE_KEYS = {
    "version",
    "scanner",
    "scanner_version",
    "target_type",
    "max_allowed_db_built_age",
    "exceptions",
}
_EXCEPTION_KEYS = {
    "id",
    "vulnerability_id",
    "package_name",
    "package_version",
    "package_type",
    "package_purl",
    "severity",
    "fix_state",
    "fixed_versions",
    "fingerprint",
    "rationale",
    "reason",
}
_POLICY_VALUES = {
    "check-for-app-update": "false",
    "only-fixed": "false",
    "only-notfixed": "false",
    "fail-on-severity": "",
    "default-image-pull-source": "docker",
    "ignore": "[]",
    "auto-update": "true",
    "validate-by-hash-on-start": "true",
    "validate-age": "true",
    "max-allowed-built-age": DB_MAX_AGE_LABEL,
    "require-update-check": "true",
    "max-update-check-frequency": "0s",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_XXH64 = re.compile(r"^xxh64:[0-9a-f]+$")
_ARCHIVE_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_EXCEPTION_ID = re.compile(r"^GRYPE-[0-9]{3,}$")
_VERSION_LINE = re.compile(r"^Version:\s+(\S+)\s*$", re.MULTILINE)
_SECRET_TEXT = re.compile(r"token|password|secret|authorization|ghp_|gho_", re.IGNORECASE)


class GateError(Exception):
    """The scan did not finish. CI must fail closed."""


@dataclass(frozen=True)
class Finding:
    vulnerability_id: str
    package_name: str
    package_version: str
    package_type: str
    package_purl: str
    severity: str
    fix_state: str
    fixed_versions: tuple[str, ...]

    def identity(self) -> dict[str, object]:
        return {
            "fix_state": self.fix_state,
            "fixed_versions": list(self.fixed_versions),
            "package_name": self.package_name,
            "package_purl": self.package_purl,
            "package_type": self.package_type,
            "package_version": self.package_version,
            "severity": self.severity,
            "vulnerability_id": self.vulnerability_id,
        }

    def fingerprint(self) -> str:
        payload = json.dumps(self.identity(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def key(self) -> tuple[object, ...]:
        return (
            self.vulnerability_id,
            self.package_name,
            self.package_version,
            self.package_type,
            self.package_purl,
            self.severity,
            self.fix_state,
            self.fixed_versions,
        )

    def label(self) -> str:
        return (
            f"{self.vulnerability_id} {self.package_name}@{self.package_version} "
            f"{self.package_type} {self.severity} fix={self.fix_state} "
            f"sha256={self.fingerprint()}"
        )


# Grype 0.120.1 ships these indirect kernel-header ignores. Any other ignore is rejected.
_BUILTIN_IGNORE_PACKAGES = frozenset(
    {
        "kernel-headers",
        "linux(-.*)?-headers-.*",
        "linux-libc-dev",
        "linux-kbuild-.*",
    }
)


def scanner_command(
    executable: str, reference: str, output_path: Path, config_path: Path
) -> list[str]:
    """Scan one image already present in the local Docker daemon.

    ``--from docker`` is the pinned version's local-daemon source. The
    ``docker:`` scheme is not repeated on the reference: Grype 0.120.1 then
    tries to parse that scheme as part of the Docker tag.
    """
    return [
        executable,
        "--config",
        str(config_path),
        "--verbose",
        "--from",
        "docker",
        "--output",
        "json",
        "--file",
        str(output_path),
        reference,
    ]


def db_update_command(executable: str, config_path: Path) -> list[str]:
    return [executable, "--config", str(config_path), "db", "update"]


def db_status_command(executable: str, config_path: Path) -> list[str]:
    return [executable, "--config", str(config_path), "db", "status", "--output", "json"]


def version_command(executable: str) -> list[str]:
    return [executable, "version"]


def gate_environment() -> dict[str, str]:
    """Force the pinned policy even if the caller exported a weaker Grype setting."""
    env = os.environ.copy()
    env.update(
        {
            "GRYPE_CHECK_FOR_APP_UPDATE": "false",
            "GRYPE_ONLY_FIXED": "false",
            "GRYPE_ONLY_NOTFIXED": "false",
            "GRYPE_DB_AUTO_UPDATE": "true",
            "GRYPE_DB_VALIDATE_BY_HASH_ON_START": "true",
            "GRYPE_DB_VALIDATE_AGE": "true",
            "GRYPE_DB_MAX_ALLOWED_BUILT_AGE": DB_MAX_AGE_LABEL,
            "GRYPE_DB_REQUIRE_UPDATE_CHECK": "true",
            "GRYPE_DB_MAX_UPDATE_CHECK_FREQUENCY": "0s",
        }
    )
    return env


def require_executable() -> str:
    path = shutil.which("grype")
    if not path:
        raise GateError("missing Grype executable")
    return path


def parse_version(output: str) -> str:
    if not output.strip():
        raise GateError("grype version returned no output")
    match = _VERSION_LINE.search(output)
    if match is None:
        first = next((line.strip() for line in output.splitlines() if line.strip()), "")
        raise GateError(f"unexpected grype version output: {first}")
    return match.group(1)


def require_version(output: str) -> None:
    version = parse_version(output)
    if version != GRYPE_VERSION:
        raise GateError(f"installed grype is {version}; this gate requires {GRYPE_VERSION}")


def assert_grype_policy(text: str) -> None:
    found: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        found[key.strip()] = value.strip().strip("\"'")
    for key, expected in _POLICY_VALUES.items():
        if found.get(key) != expected:
            raise GateError(f"grype policy {key} must be {expected}")
    if "only-fixed: true" in text or "only-notfixed: true" in text:
        raise GateError("grype policy must not hide fixed or unfixed vulnerabilities")


def load_policy(path: Path = POLICY_PATH) -> None:
    if not path.is_file():
        raise GateError(f"missing grype policy at {path}")
    assert_grype_policy(path.read_text(encoding="utf-8"))


def local_reference(image: str) -> str:
    if not isinstance(image, str) or not image.startswith("docker:"):
        raise GateError("scan target must use the grype docker: local source")
    reference = image.removeprefix("docker:")
    if (
        not reference
        or reference.startswith("registry:")
        or any(char.isspace() for char in reference)
        or "*" in reference
        or "?" in reference
    ):
        raise GateError("scan target is not one local docker image reference")
    return reference


def parse_json_document(text: str, label: str) -> dict:
    if not text.strip():
        raise GateError(f"{label} returned no JSON")
    try:
        data, end = json.JSONDecoder().raw_decode(text)
    except json.JSONDecodeError as exc:
        raise GateError(f"{label} JSON did not parse: {exc}") from exc
    if text[end:].strip():
        raise GateError(f"{label} JSON is truncated or has trailing data")
    if not isinstance(data, dict):
        raise GateError(f"{label} JSON was not an object")
    return data


def parse_built(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise GateError("vulnerability database built timestamp is missing")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        built = datetime.fromisoformat(text)
    except ValueError as exc:
        raise GateError("vulnerability database built timestamp is not RFC3339") from exc
    if built.tzinfo is None:
        raise GateError("vulnerability database built timestamp must include a timezone")
    return built.astimezone(UTC)


def assert_db_fresh(built: datetime, *, now: datetime | None = None) -> None:
    current = now if now is not None else datetime.now(UTC)
    if built - current > timedelta(hours=1):
        raise GateError("vulnerability database built timestamp is implausibly in the future")
    age = current - built
    if age > DB_MAX_AGE:
        raise GateError(
            f"vulnerability database is older than {DB_MAX_AGE_LABEL}: built {built.isoformat()}"
        )


def published_archive_checksum(source: object) -> str:
    if not isinstance(source, str) or not source:
        return ""
    query = urllib.parse.parse_qs(urllib.parse.urlparse(source).query)
    values = query.get("checksum") or []
    if not values:
        return ""
    checksum = values[0]
    if _ARCHIVE_SHA256.fullmatch(checksum) is None:
        raise GateError("vulnerability database source exposed a malformed checksum")
    return checksum


def integrity_checksum(status: dict) -> str:
    path = status.get("path")
    if not isinstance(path, str) or not path.endswith("/vulnerability.db"):
        raise GateError("vulnerability database status did not expose its database path")
    db_path = Path(path)
    if not db_path.is_file():
        raise GateError("vulnerability database status path is not a file")
    metadata_path = db_path.with_name("import.json")
    if not metadata_path.is_file():
        raise GateError("vulnerability database integrity metadata is missing")
    metadata = parse_json_document(metadata_path.read_text(encoding="utf-8"), "database integrity")
    digest = metadata.get("digest")
    if not isinstance(digest, str) or _XXH64.fullmatch(digest) is None:
        raise GateError("vulnerability database integrity checksum is missing")
    return digest


def parse_db_status(
    data: dict,
    *,
    now: datetime | None = None,
    read_integrity: Callable[[dict], str] | None = None,
) -> dict[str, str]:
    if data.get("valid") is not True:
        raise GateError("vulnerability database status is not valid")
    error = data.get("error")
    if isinstance(error, str) and error.strip():
        raise GateError("vulnerability database status reported an error")
    schema = data.get("schemaVersion")
    if not isinstance(schema, str) or not schema.strip():
        raise GateError("vulnerability database schema version is missing")
    built = parse_built(data.get("built"))
    assert_db_fresh(built, now=now)
    archive = published_archive_checksum(data.get("from"))
    reader = read_integrity or integrity_checksum
    integrity = reader(data)
    if _XXH64.fullmatch(integrity) is None:
        raise GateError("vulnerability database integrity checksum is missing")
    if not archive and not integrity:
        raise GateError("vulnerability database checksum was not exposed")
    return {
        "schema": schema,
        "built": built.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "archive_checksum": archive,
        "integrity_checksum": integrity,
    }


def _reject_wildcard(value: object, label: str, *, allow_query: bool = False) -> str:
    if not isinstance(value, str):
        raise GateError(f"{label} must be a string")
    if "*" in value or (not allow_query and "?" in value):
        raise GateError(f"{label} contains a wildcard")
    return value


def _fixed_versions(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise GateError(f"{label} must be a list")
    versions: list[str] = []
    for item in value:
        version = _reject_wildcard(item, label)
        if not version or any(char.isspace() for char in version):
            raise GateError(f"{label} contains an empty version")
        versions.append(version)
    return tuple(sorted(versions))


def finding_from_match(match: object) -> Finding:
    if not isinstance(match, dict):
        raise GateError("grype match is not an object")
    vulnerability = match.get("vulnerability")
    artifact = match.get("artifact")
    if not isinstance(vulnerability, dict) or not isinstance(artifact, dict):
        raise GateError("grype match is missing vulnerability or artifact")
    vulnerability_id = _reject_wildcard(vulnerability.get("id"), "vulnerability id")
    if not vulnerability_id:
        raise GateError("grype match is missing a vulnerability id")
    severity = vulnerability.get("severity")
    if severity not in SEVERITIES:
        raise GateError(f"grype match has an unexpected severity: {severity!r}")
    fix = vulnerability.get("fix")
    if not isinstance(fix, dict):
        raise GateError(f"grype match {vulnerability_id} is missing fix metadata")
    fix_state = fix.get("state")
    if fix_state not in FIX_STATES:
        raise GateError(f"grype match {vulnerability_id} has an unexpected fix state")
    package_name = _reject_wildcard(artifact.get("name"), "package name")
    package_version = _reject_wildcard(artifact.get("version"), "package version")
    package_type = _reject_wildcard(artifact.get("type"), "package type")
    if not package_name or not package_version or not package_type:
        raise GateError(f"grype match {vulnerability_id} is missing package identity")
    purl_value = artifact.get("purl", "")
    if purl_value in (None, ""):
        package_purl = ""
    else:
        package_purl = _reject_wildcard(purl_value, "package purl", allow_query=True)
        if not package_purl.startswith("pkg:"):
            raise GateError(f"grype match {vulnerability_id} has a malformed package purl")
    return Finding(
        vulnerability_id=vulnerability_id,
        package_name=package_name,
        package_version=package_version,
        package_type=package_type,
        package_purl=package_purl,
        severity=severity,
        fix_state=fix_state,
        fixed_versions=_fixed_versions(fix.get("versions"), "fixed version"),
    )


def package_count(logs: str) -> int:
    counts: list[int] = []
    for line in logs.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and "gathered packages" in stripped:
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError:
                item = None
            if isinstance(item, dict) and item.get("msg") == "gathered packages":
                value = item.get("packages")
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise GateError("grype package count is not a number")
                counts.append(value)
            continue
        if "gathered packages" not in line:
            continue
        match = re.search(r"\bpackages=(\d+)\b", line)
        if match:
            counts.append(int(match.group(1)))
    if len(counts) != 1:
        raise GateError("grype did not report exactly one package count")
    return counts[0]


def _duration_is_120h(value: object) -> bool:
    if value in {DB_MAX_AGE_LABEL, "120h0m0s"}:
        return True
    return value in {120 * 60 * 60 * 1_000_000_000, float(120 * 60 * 60 * 1_000_000_000)}


def assert_report_ignores(ignore: object) -> None:
    if ignore in (None, []):
        return
    if not isinstance(ignore, list):
        raise GateError("grype report ignore rules are malformed")
    seen: set[str] = set()
    for rule in ignore:
        if not isinstance(rule, dict):
            raise GateError("grype report contains a custom ignore rule")
        if rule.get("vulnerability") or rule.get("fix-state"):
            raise GateError("grype report contains a vulnerability ignore rule")
        package = rule.get("package")
        name = package.get("name") if isinstance(package, dict) else None
        if name not in _BUILTIN_IGNORE_PACKAGES or name in seen:
            raise GateError("grype report contains a custom ignore rule")
        seen.add(name)


def assert_report_configuration(configuration: object) -> None:
    if not isinstance(configuration, dict):
        raise GateError("grype report configuration is incomplete")
    if configuration.get("check-for-app-update") is not False:
        raise GateError("grype application update checking is not disabled")
    if configuration.get("only-fixed") is True or configuration.get("only-notfixed") is True:
        raise GateError("grype report ignored vulnerabilities by fix availability")
    if configuration.get("from") != ["docker"]:
        raise GateError("grype report did not restrict the source to the local docker daemon")
    if configuration.get("default-image-pull-source") != "docker":
        raise GateError("grype report default image source is not the local docker daemon")
    assert_report_ignores(configuration.get("ignore"))
    database = configuration.get("db")
    if not isinstance(database, dict):
        raise GateError("grype report is missing database policy")
    if database.get("validate-age") is not True:
        raise GateError("grype report does not validate vulnerability database age")
    if database.get("validate-by-hash-on-start") is not True:
        raise GateError("grype report does not validate the vulnerability database hash")
    if database.get("require-update-check") is not True:
        raise GateError("grype report does not fail closed on a database update check")
    if database.get("auto-update") is not True:
        raise GateError("grype report does not update the vulnerability database")
    if not _duration_is_120h(database.get("max-allowed-built-age")):
        raise GateError("grype report database age limit is not 120h")


def assert_local_target(report: dict, image: str, repo_digests: tuple[str, ...]) -> None:
    source = report.get("source")
    if not isinstance(source, dict):
        raise GateError("scan result is missing its source")
    if source.get("type") != "image":
        raise GateError(f"wrong target type: {source.get('type')!r}")
    target = source.get("target")
    if not isinstance(target, dict):
        raise GateError("scan target is incomplete")
    reference = local_reference(image)
    user_input = target.get("userInput")
    if not isinstance(user_input, str) or user_input.startswith("registry:"):
        raise GateError("unexpected registry fallback")
    if user_input != reference:
        raise GateError(f"scan target does not match the requested local image: {user_input}")
    tags = target.get("tags")
    if not isinstance(tags, list) or reference not in tags:
        raise GateError("scan target is not the requested local image tag")
    reported = target.get("repoDigests")
    if repo_digests and (not isinstance(reported, list) or set(repo_digests).isdisjoint(reported)):
        raise GateError("scan target digest does not match the local docker image")


def parse_report(
    data: dict,
    image: str,
    repo_digests: tuple[str, ...] = (),
    *,
    read_integrity: Callable[[dict], str] | None = None,
    now: datetime | None = None,
) -> tuple[list[Finding], dict[str, str]]:
    for key in ("matches", "source", "descriptor"):
        if key not in data:
            raise GateError(f"grype JSON is missing {key}")
    matches = data["matches"]
    if not isinstance(matches, list):
        raise GateError("grype JSON matches is not a list")
    ignored = data.get("ignoredMatches", [])
    if ignored not in (None, []):
        raise GateError("grype JSON suppressed matches; the gate does not accept ignore rules")
    descriptor = data["descriptor"]
    if not isinstance(descriptor, dict):
        raise GateError("grype JSON descriptor is incomplete")
    if descriptor.get("name") != SCANNER:
        raise GateError("grype JSON was not produced by grype")
    if descriptor.get("version") != GRYPE_VERSION:
        raise GateError(f"grype JSON scanner version is not {GRYPE_VERSION}")
    if "configuration" not in descriptor:
        raise GateError("grype JSON is missing its configuration")
    assert_report_configuration(descriptor["configuration"])
    database = descriptor.get("db")
    if not isinstance(database, dict) or not isinstance(database.get("status"), dict):
        raise GateError("grype JSON is missing vulnerability database status")
    reader = read_integrity or integrity_checksum
    db_meta = parse_db_status(database["status"], now=now, read_integrity=reader)
    assert_local_target(data, image, repo_digests)
    findings = [finding_from_match(match) for match in matches]
    return findings, db_meta


def _validate_exception(index: int, item: object) -> Finding:
    if not isinstance(item, dict):
        raise GateError(f"baseline exception {index} must be an object")
    extra = set(item) - _EXCEPTION_KEYS
    missing = _EXCEPTION_KEYS - set(item)
    if extra or missing:
        raise GateError(f"baseline exception {index} fields are not the exact identity")
    exception_id = item["id"]
    if not isinstance(exception_id, str) or _EXCEPTION_ID.fullmatch(exception_id) is None:
        raise GateError(f"baseline exception {index} id must be GRYPE-001 style")
    vulnerability_id = _reject_wildcard(item["vulnerability_id"], f"baseline exception {index}")
    package_name = _reject_wildcard(item["package_name"], f"baseline exception {index} package")
    package_version = _reject_wildcard(
        item["package_version"], f"baseline exception {index} version"
    )
    package_type = _reject_wildcard(item["package_type"], f"baseline exception {index} type")
    if not vulnerability_id or not package_name or not package_version or not package_type:
        raise GateError(f"baseline exception {index} identity is incomplete")
    purl = item["package_purl"]
    if purl == "":
        package_purl = ""
    else:
        package_purl = _reject_wildcard(purl, f"baseline exception {index} purl", allow_query=True)
        if not package_purl.startswith("pkg:"):
            raise GateError(f"baseline exception {index} purl must be empty or a package URL")
    if item["severity"] not in SEVERITIES:
        raise GateError(f"baseline exception {index} severity is not a Grype severity")
    if item["fix_state"] not in FIX_STATES:
        raise GateError(f"baseline exception {index} fix_state is not a Grype fix state")
    fixed_versions = _fixed_versions(item["fixed_versions"], f"baseline exception {index}")
    if item["fixed_versions"] != list(fixed_versions):
        raise GateError(f"baseline exception {index} fixed_versions must be sorted")
    finding = Finding(
        vulnerability_id=vulnerability_id,
        package_name=package_name,
        package_version=package_version,
        package_type=package_type,
        package_purl=package_purl,
        severity=item["severity"],
        fix_state=item["fix_state"],
        fixed_versions=fixed_versions,
    )
    fingerprint = item["fingerprint"]
    if not isinstance(fingerprint, str) or _SHA256.fullmatch(fingerprint) is None:
        raise GateError(f"baseline exception {index} fingerprint must be one sha256 hex digest")
    if fingerprint != finding.fingerprint():
        raise GateError(f"baseline exception {index} fingerprint does not match its identity")
    if item["rationale"] not in RATIONALES:
        raise GateError(f"baseline exception {index} rationale is not an allowed value")
    reason = item["reason"]
    if not isinstance(reason, str) or not reason.strip() or "\n" in reason or len(reason) > 400:
        raise GateError(f"baseline exception {index} reason must be one short line")
    if reason.strip().lower() in {"*", "all", "any", "ignore", "accepted risk", "risk acceptance"}:
        raise GateError(f"baseline exception {index} reason must describe this finding")
    return finding


def load_baseline(path: Path) -> dict:
    if not path.is_file():
        raise GateError(f"missing container vulnerability baseline at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"container vulnerability baseline is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError("container vulnerability baseline must be a JSON object")
    extra = set(data) - _BASELINE_KEYS
    if extra:
        raise GateError(f"container vulnerability baseline has unknown fields: {sorted(extra)}")
    if data.get("version") != 1:
        raise GateError("container vulnerability baseline version must be 1")
    if data.get("scanner") != SCANNER:
        raise GateError("container vulnerability baseline scanner must be grype")
    if data.get("scanner_version") != GRYPE_VERSION:
        raise GateError(f"container vulnerability baseline scanner_version must be {GRYPE_VERSION}")
    if data.get("target_type") != TARGET_TYPE:
        raise GateError("container vulnerability baseline target_type must be local_docker_image")
    if data.get("max_allowed_db_built_age") != DB_MAX_AGE_LABEL:
        raise GateError("container vulnerability baseline database age limit must be 120h")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        raise GateError("container vulnerability baseline exceptions must be a list")
    seen: set[str] = set()
    for index, item in enumerate(exceptions):
        _validate_exception(index, item)
        exception_id = item["id"]
        if exception_id in seen:
            raise GateError(f"baseline exception id {exception_id} is duplicated")
        seen.add(exception_id)
    return data


def exception_finding(item: dict) -> Finding:
    return _validate_exception(0, item)


def compare(findings: list[Finding], exceptions: list[dict]) -> list[str]:
    """Return regressions. One exception covers one current finding."""
    finding_counts: Counter[tuple[object, ...]] = Counter(item.key() for item in findings)
    exception_findings = [exception_finding(item) for item in exceptions]
    exception_counts: Counter[tuple[object, ...]] = Counter(
        item.key() for item in exception_findings
    )
    labels = {item.key(): item.label() for item in [*findings, *exception_findings]}
    regressions: list[str] = []
    for key, count in sorted(exception_counts.items(), key=lambda item: labels[item[0]]):
        found = finding_counts.get(key, 0)
        if found == 0:
            regressions.append(f"stale baseline exception: {labels[key]}")
        elif count > found:
            regressions.append(
                f"duplicate excess exception: {labels[key]} ({count} exceptions, {found} findings)"
            )
    for key, count in sorted(finding_counts.items(), key=lambda item: labels[item[0]]):
        allowed = exception_counts.get(key, 0)
        if count <= allowed:
            continue
        sample = next(item for item in findings if item.key() == key)
        blocking = BLOCKING_SEVERITIES.get(sample.severity)
        if blocking:
            regressions.append(f"unresolved {blocking} finding: {labels[key]}")
        regressions.append(f"unbaselined container finding: {labels[key]}")
    return regressions


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        counts[finding.severity] += 1
    return counts


def summary_text(
    *,
    image: str,
    packages: int,
    findings: list[Finding],
    exceptions: list[dict],
    db_meta: dict[str, str],
) -> str:
    counts = severity_counts(findings)
    checksum = db_meta["archive_checksum"] or db_meta["integrity_checksum"]
    lines = [
        "container_vuln_gate: OK",
        f"scanner={SCANNER}",
        f"scanner_version={GRYPE_VERSION}",
        f"target={image}",
        f"packages={packages}",
        f"findings={len(findings)}",
        f"exceptions={len(exceptions)}",
        f"critical={counts['Critical']}",
        f"high={counts['High']}",
        f"medium={counts['Medium']}",
        f"low={counts['Low']}",
        f"negligible={counts['Negligible']}",
        f"db_built={db_meta['built']}",
        f"db_schema={db_meta['schema']}",
        f"db_checksum={checksum}",
    ]
    return "\n".join(lines)


def _safe_detail(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("{") or stripped.startswith("["):
            continue
        if _SECRET_TEXT.search(stripped):
            continue
        kept.append(stripped)
    return "\n".join(kept[-20:])[:2000]


def _run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, env=env, check=False)


def require_success(label: str, completed: subprocess.CompletedProcess[str]) -> None:
    if completed.returncode != 0:
        detail = _safe_detail((completed.stderr or "") + "\n" + (completed.stdout or ""))
        suffix = f": {detail}" if detail else ""
        raise GateError(f"{label} failed{suffix}")


def local_image_identity(reference: str) -> tuple[str, tuple[str, ...]]:
    completed = subprocess.run(
        ["docker", "image", "inspect", reference],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise GateError(f"requested local image is missing: {reference}")
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise GateError("docker image inspect did not return JSON") from exc
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise GateError("docker image inspect did not return the local image")
    image = data[0]
    image_id = image.get("Id")
    if not isinstance(image_id, str) or _IMAGE_ID.fullmatch(image_id) is None:
        raise GateError("docker image inspect did not return a sha256 image id")
    digests = image.get("RepoDigests") or []
    if not isinstance(digests, list) or any(not isinstance(item, str) for item in digests):
        raise GateError("docker image inspect returned malformed repo digests")
    return image_id, tuple(digests)


def run_gate(
    image: str,
    baseline_path: Path = BASELINE_PATH,
    policy_path: Path = POLICY_PATH,
) -> str:
    reference = local_reference(image)
    load_policy(policy_path)
    baseline = load_baseline(baseline_path)
    executable = require_executable()
    env = gate_environment()
    version = _run(version_command(executable), env)
    require_success("grype version", version)
    require_version((version.stdout or "") + "\n" + (version.stderr or ""))
    image_id, repo_digests = local_image_identity(reference)
    updated = _run(db_update_command(executable, policy_path), env)
    require_success("vulnerability database update", updated)
    status = _run(db_status_command(executable, policy_path), env)
    require_success("vulnerability database status", status)
    parse_db_status(parse_json_document(status.stdout, "vulnerability database status"))
    with tempfile.TemporaryDirectory(prefix="grype-report-") as directory:
        report_path = Path(directory) / "grype.json"
        scanned = _run(scanner_command(executable, reference, report_path, policy_path), env)
        require_success("grype scan", scanned)
        after_id, _after_digests = local_image_identity(reference)
        if after_id != image_id:
            raise GateError("unexpected registry fallback")
        try:
            report_text = report_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise GateError("grype did not write the JSON report") from exc
        except UnicodeError as exc:
            raise GateError("grype JSON report is not UTF-8") from exc
        report = parse_json_document(report_text, "grype")
        findings, db_meta = parse_report(report, image, repo_digests)
        packages = package_count((scanned.stderr or "") + "\n" + (scanned.stdout or ""))
    regressions = compare(findings, baseline["exceptions"])
    if regressions:
        print(
            summary_text(
                image=image,
                packages=packages,
                findings=findings,
                exceptions=baseline["exceptions"],
                db_meta=db_meta,
            ).replace("container_vuln_gate: OK", "container_vuln_gate: FAIL", 1),
            file=sys.stderr,
        )
        print("FAIL: container findings are outside the explicit baseline:", file=sys.stderr)
        for line in regressions:
            print(line, file=sys.stderr)
        raise GateError("unreviewed container finding")
    text = summary_text(
        image=image,
        packages=packages,
        findings=findings,
        exceptions=baseline["exceptions"],
        db_meta=db_meta,
    )
    print(text)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare a local image Grype scan to the baseline."
    )
    parser.add_argument("--image", required=True, help="Local image as docker:<reference>")
    parser.add_argument("--baseline", default=str(BASELINE_PATH))
    args = parser.parse_args(argv)
    try:
        run_gate(args.image, Path(args.baseline))
    except GateError as exc:
        print(f"FAIL: container vulnerability gate did not complete: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
