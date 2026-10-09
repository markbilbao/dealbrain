#!/usr/bin/env python3
"""Sprint 40.2 dependency gate: pinned pip-audit against the frozen uv lock.

The audited set is every third-party distribution in ``uv.lock`` reached by
``uv export --frozen --extra dev`` (runtime dependencies plus the dev extra).
Environment markers are stripped so Linux CI still audits Windows-only pins.
``pip-audit --no-deps`` does not re-resolve those pins.

``tests/security/baselines/pip-audit.baseline.json`` is an allowlist of
package + locked version + advisory id. An empty list fails every advisory.
The pip-audit process is not given an ignore flag. Wildcard exceptions are
rejected.

Usage:
    uv run python scripts/check_pip_audit_baseline.py
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "security" / "baselines" / "pip-audit.baseline.json"
PIP_AUDIT_VERSION = "2.10.1"
VULNERABILITY_SERVICE = "osv"
PROJECT_NAME = "dealbrain"

_EXPORT_COMMAND = (
    "uv",
    "export",
    "--frozen",
    "--extra",
    "dev",
    "--no-emit-project",
    "--no-hashes",
    "--no-annotate",
    "--no-header",
)
_REQUIREMENT_LINE = re.compile(r"^([A-Za-z0-9_.-]+)==([^;\s]+)\s*(?:;.*)?$")
_WILDCARDS = {"", "*", "all", "any"}


class GateError(Exception):
    """The audit did not finish. CI must fail closed."""


@dataclass(frozen=True)
class Finding:
    package: str
    version: str
    advisory_id: str
    aliases: tuple[str, ...]
    fix_versions: tuple[str, ...]
    dependency_class: str
    origin: str
    via: tuple[str, ...]

    def label(self) -> str:
        alias = f" aliases={','.join(self.aliases)}" if self.aliases else ""
        fixes = ",".join(self.fix_versions) if self.fix_versions else "none"
        via = ",".join(self.via) if self.via else "none"
        return (
            f"{self.package}=={self.version} {self.advisory_id}{alias} "
            f"class={self.dependency_class} origin={self.origin} "
            f"via={via} fix_versions={fixes}"
        )


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def requirement_name(specifier: str) -> str:
    base = specifier.split("[", 1)[0]
    name = re.split(r"[<>=!~;\s]", base, maxsplit=1)[0]
    return normalize_name(name)


def parse_export(text: str) -> dict[str, str]:
    """Return normalized name -> exact version from a marker-stripped export."""
    pins: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-", "--")):
            raise GateError(f"export line {lineno} is not an exact pin: {line}")
        match = _REQUIREMENT_LINE.match(line)
        if match is None:
            raise GateError(f"export line {lineno} is not an exact pin: {line}")
        name = normalize_name(match.group(1))
        version = match.group(2)
        if name in pins:
            raise GateError(f"duplicate export pin for {name}")
        pins[name] = version
    if not pins:
        raise GateError("uv export produced no third-party pins")
    return pins


def locked_distributions(lock: dict) -> dict[str, str]:
    """Third-party lockfile distributions. The local project is not audited."""
    pins: dict[str, str] = {}
    for package in lock.get("package", []):
        source = package.get("source") or {}
        if "editable" in source or source.get("virtual") or source.get("directory"):
            continue
        name = normalize_name(str(package.get("name", "")))
        version = package.get("version")
        if not name or not isinstance(version, str) or not version:
            raise GateError(f"lockfile package is missing a name or version: {package!r}")
        if name in pins:
            raise GateError(f"duplicate lockfile package {name}")
        pins[name] = version
    return pins


def ensure_same_closure(exported: dict[str, str], locked: dict[str, str]) -> None:
    missing = sorted(set(locked) - set(exported))
    extra = sorted(set(exported) - set(locked))
    if missing or extra:
        raise GateError(
            "uv export does not match uv.lock third-party packages: "
            f"missing={missing or '[]'} extra={extra or '[]'}"
        )
    mismatched = sorted(name for name, version in exported.items() if locked[name] != version)
    if mismatched:
        detail = ", ".join(
            f"{name} export={exported[name]} lock={locked[name]}" for name in mismatched
        )
        raise GateError(f"uv export versions disagree with uv.lock: {detail}")


def direct_names(pyproject: dict) -> tuple[set[str], set[str]]:
    project = pyproject.get("project") or {}
    runtime = {requirement_name(spec) for spec in project.get("dependencies") or []}
    extras = (project.get("optional-dependencies") or {}).get("dev") or []
    dev = {requirement_name(spec) for spec in extras}
    return runtime, dev


def dependency_class(name: str, runtime: set[str], dev: set[str]) -> str:
    if name in runtime or name in dev:
        return "direct"
    return "transitive"


def dependency_origin(name: str, runtime: set[str], dev: set[str]) -> str:
    if name in runtime:
        return "project.dependencies"
    if name in dev:
        return "project.optional-dependencies.dev"
    return "transitive"


def parent_index(lock: dict) -> dict[str, tuple[str, ...]]:
    parents: dict[str, set[str]] = {}
    for package in lock.get("package", []):
        parent = normalize_name(str(package.get("name", "")))
        if not parent:
            continue
        for dep in package.get("dependencies") or []:
            child = normalize_name(str(dep.get("name", "")))
            if not child:
                continue
            parents.setdefault(child, set()).add(parent)
    return {name: tuple(sorted(values)) for name, values in parents.items()}


def via_for(name: str, parents: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(parent for parent in parents.get(name, ()) if parent != PROJECT_NAME)


def load_baseline(path: Path) -> dict:
    if not path.is_file():
        raise GateError(f"missing pip-audit baseline at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"pip-audit baseline is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError("pip-audit baseline must be a JSON object")
    if data.get("version") != 1:
        raise GateError("pip-audit baseline version must be 1")
    if data.get("scanner") != "pip-audit":
        raise GateError("pip-audit baseline scanner must be pip-audit")
    if data.get("scanner_version") != PIP_AUDIT_VERSION:
        raise GateError(f"pip-audit baseline scanner_version must be {PIP_AUDIT_VERSION}")
    if data.get("vulnerability_service") != VULNERABILITY_SERVICE:
        raise GateError(f"pip-audit baseline vulnerability_service must be {VULNERABILITY_SERVICE}")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        raise GateError("pip-audit baseline exceptions must be a list")
    for index, item in enumerate(exceptions):
        _validate_exception(index, item)
    return data


def _reject_wildcard(value: str, label: str) -> None:
    if not isinstance(value, str) or value.strip().lower() in _WILDCARDS or "*" in value:
        raise GateError(f"baseline exception {label} must be one exact value, not a wildcard")


def _validate_exception(index: int, item: object) -> None:
    if not isinstance(item, dict):
        raise GateError(f"baseline exception {index} must be an object")
    for field in ("package", "version", "advisory_id"):
        _reject_wildcard(item.get(field), f"{index}.{field}")
    aliases = item.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
        raise GateError(f"baseline exception {index} aliases must be a list of strings")
    for alias in aliases:
        _reject_wildcard(alias, f"{index}.aliases")


def _ids(finding: Finding, exception: dict) -> bool:
    expected = {exception["advisory_id"], *exception.get("aliases", [])}
    observed = {finding.advisory_id, *finding.aliases}
    return bool(expected & observed)


def exception_matches(finding: Finding, exception: dict) -> bool:
    if normalize_name(exception["package"]) != finding.package:
        return False
    if exception["version"] != finding.version:
        return False
    return _ids(finding, exception)


def compare(findings: list[Finding], exceptions: list[dict]) -> list[str]:
    """Return regressions. Empty means the allowlist matches the audit exactly."""
    regressions: list[str] = []
    ordered = sorted(findings, key=lambda item: (item.package, item.version, item.advisory_id))
    for finding in ordered:
        if not any(exception_matches(finding, exception) for exception in exceptions):
            regressions.append(f"unbaselined advisory: {finding.label()}")
    for index, exception in enumerate(exceptions):
        if not any(exception_matches(finding, exception) for finding in findings):
            regressions.append(
                "stale baseline exception "
                f"{index}: {exception['package']}=={exception['version']} "
                f"{exception['advisory_id']}"
            )
    return regressions


def parse_audit_payload(
    data: dict,
    exported: dict[str, str],
    runtime: set[str],
    dev: set[str],
    parents: dict[str, tuple[str, ...]],
) -> list[Finding]:
    dependencies = data.get("dependencies")
    if not isinstance(dependencies, list):
        raise GateError("pip-audit JSON is missing a dependencies list")
    reported: dict[str, str] = {}
    findings: list[Finding] = []
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise GateError("pip-audit dependency entry is not an object")
        name = normalize_name(str(dependency.get("name", "")))
        version = dependency.get("version")
        if not name or not isinstance(version, str):
            raise GateError(f"pip-audit dependency is missing a name or version: {dependency!r}")
        skip_reason = dependency.get("skip_reason")
        if skip_reason:
            raise GateError(f"pip-audit skipped {name}=={version}: {skip_reason}")
        if name in reported:
            raise GateError(f"pip-audit reported {name} more than once")
        reported[name] = version
        for vuln in dependency.get("vulns") or []:
            if not isinstance(vuln, dict) or not isinstance(vuln.get("id"), str):
                raise GateError(f"pip-audit vulnerability for {name}=={version} has no id")
            aliases = tuple(str(alias) for alias in vuln.get("aliases") or [])
            fixes = tuple(str(fix) for fix in vuln.get("fix_versions") or [])
            findings.append(
                Finding(
                    package=name,
                    version=version,
                    advisory_id=vuln["id"],
                    aliases=aliases,
                    fix_versions=fixes,
                    dependency_class=dependency_class(name, runtime, dev),
                    origin=dependency_origin(name, runtime, dev),
                    via=via_for(name, parents),
                )
            )
    ensure_same_closure(reported, exported)
    return findings


def export_locked_requirements() -> str:
    proc = subprocess.run(
        _EXPORT_COMMAND,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "uv export failed").strip()
        raise GateError(detail)
    return proc.stdout


def _pip_audit_version() -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "pip_audit", "--version"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "pip-audit --version failed").strip()
        raise GateError(detail)
    token = (proc.stdout or "").strip().split()
    if len(token) < 2:
        raise GateError(f"unexpected pip-audit version output: {proc.stdout!r}")
    return token[-1]


def run_pip_audit(requirements_path: Path) -> dict:
    version = _pip_audit_version()
    if version != PIP_AUDIT_VERSION:
        raise GateError(f"installed pip-audit is {version}; this gate requires {PIP_AUDIT_VERSION}")
    last_error = "pip-audit did not return JSON"
    for attempt in range(1, 4):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--requirement",
                str(requirements_path),
                "--no-deps",
                "--disable-pip",
                "--format",
                "json",
                "--vulnerability-service",
                VULNERABILITY_SERVICE,
                "--progress-spinner",
                "off",
                "--timeout",
                "60",
                "--strict",
                "--output",
                str(requirements_path.with_suffix(".json")),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        output_path = requirements_path.with_suffix(".json")
        text = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
        if proc.returncode in (0, 1) and text.strip():
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                last_error = f"attempt {attempt}: pip-audit JSON did not parse"
            else:
                if isinstance(data, dict):
                    return data
                last_error = f"attempt {attempt}: pip-audit JSON was not an object"
        else:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            tail = detail[-1] if detail else "no output"
            last_error = f"attempt {attempt}: exit {proc.returncode}: {tail}"
        if attempt < 3:
            time.sleep(attempt)
    raise GateError(last_error)


def audit_export(
    exported: dict[str, str],
    runtime: set[str],
    dev: set[str],
    parents: dict[str, tuple[str, ...]],
) -> list[Finding]:
    lines = [f"{name}=={version}" for name, version in sorted(exported.items())]
    with tempfile.TemporaryDirectory(prefix="pip-audit-") as tmp:
        requirements = Path(tmp) / "requirements.txt"
        requirements.write_text("\n".join(lines) + "\n", encoding="utf-8")
        payload = run_pip_audit(requirements)
    return parse_audit_payload(payload, exported, runtime, dev, parents)


def load_project_files() -> tuple[dict, dict]:
    with (ROOT / "uv.lock").open("rb") as handle:
        lock = tomllib.load(handle)
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    return lock, pyproject


def run(baseline_path: Path = BASELINE_PATH) -> int:
    baseline = load_baseline(baseline_path)
    exported = parse_export(export_locked_requirements())
    lock, pyproject = load_project_files()
    locked = locked_distributions(lock)
    ensure_same_closure(exported, locked)
    runtime, dev = direct_names(pyproject)
    findings = audit_export(exported, runtime, dev, parent_index(lock))
    regressions = compare(findings, baseline["exceptions"])
    print(
        "pip-audit baseline gate: "
        f"packages={len(exported)} vulnerabilities={len(findings)} "
        f"exceptions={len(baseline['exceptions'])} "
        f"scanner={PIP_AUDIT_VERSION} service={VULNERABILITY_SERVICE}"
    )
    if regressions:
        print("FAIL: pip-audit findings are outside the explicit baseline:", file=sys.stderr)
        for line in regressions:
            print(f"  - {line}", file=sys.stderr)
        print(
            "Fix the dependency, or add one package+version+advisory exception "
            f"to {baseline_path}.",
            file=sys.stderr,
        )
        return 1
    print("OK: no unbaselined pip-audit advisories")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    args = parser.parse_args(argv)
    try:
        return run(args.baseline)
    except GateError as exc:
        print(f"FAIL: pip-audit gate did not complete: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
