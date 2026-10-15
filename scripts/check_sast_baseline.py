#!/usr/bin/env python3
"""Local Bandit SAST gate for application Python code.

The scan target is ``app/``. The gate runs the pinned Bandit module, parses
its JSON, and compares every result with
``tests/security/baselines/bandit.baseline.json``. Bandit's process exit code
is not the verdict: exit 1 means findings were found, and those findings are
accepted only when each one has one exact baseline exception. Exit values
other than 0 or 1, invalid JSON, a version or scope mismatch, a missing
file, or a scanner error fail closed.

A baseline exception names one reviewed finding by relative path, test id,
severity, confidence, and a SHA-256 of the normalized source Bandit
associated with that finding. Line numbers are not part of the identity.
``# nosec``, skipped tests, wildcard paths, and wildcard test ids are
rejected. The gate does not upload source or findings.

Usage:
    uv run python scripts/check_sast_baseline.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "security" / "baselines" / "bandit.baseline.json"
BANDIT_VERSION = "1.9.4"
SCANNER = "bandit"
SCOPE = "app/**/*.py"
SCAN_TARGET = "app"
CONTEXT_LINES = "400"
SEVERITIES = ("UNDEFINED", "LOW", "MEDIUM", "HIGH")
RATIONALES = (
    "false_positive",
    "safe_constant",
    "test_only_behavior",
    "framework_managed",
)
_TEST_ID = re.compile(r"^B[0-9]{3}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".bzr",
        ".eggs",
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        "CVS",
        "__pycache__",
    }
)
# Bandit's own default excludes, plus cache directories that are not source.
# `*.egg` is an artifact suffix, not a baseline wildcard.
BANDIT_EXCLUDES = ",".join(
    (
        ".svn",
        "CVS",
        ".bzr",
        ".hg",
        ".git",
        "__pycache__",
        ".tox",
        ".eggs",
        "*.egg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    )
)
_BASELINE_KEYS = {"version", "scanner", "scanner_version", "scope", "exceptions"}
_EXCEPTION_KEYS = {
    "path",
    "test_id",
    "severity",
    "confidence",
    "code_sha256",
    "rationale",
    "reason",
}
_TOTAL_KEYS = (
    "SEVERITY.UNDEFINED",
    "SEVERITY.LOW",
    "SEVERITY.MEDIUM",
    "SEVERITY.HIGH",
    "CONFIDENCE.UNDEFINED",
    "CONFIDENCE.LOW",
    "CONFIDENCE.MEDIUM",
    "CONFIDENCE.HIGH",
    "nosec",
    "skipped_tests",
)


class GateError(Exception):
    """The scan did not finish. CI must fail closed."""


@dataclass(frozen=True)
class Finding:
    path: str
    test_id: str
    severity: str
    confidence: str
    code_sha256: str
    line_number: int

    def label(self) -> str:
        return (
            f"{self.path}:{self.line_number} {self.test_id} "
            f"{self.severity} {self.confidence} sha256={self.code_sha256}"
        )


def scanner_command(output_path: Path) -> list[str]:
    """Pinned Bandit module. No config file, skip list, or hosted upload."""
    return [
        sys.executable,
        "-m",
        "bandit",
        "--quiet",
        "--recursive",
        SCAN_TARGET,
        "--format",
        "json",
        "--output",
        str(output_path),
        "--severity-level",
        "all",
        "--confidence-level",
        "all",
        "--ignore-nosec",
        "--number",
        CONTEXT_LINES,
        "--exclude",
        BANDIT_EXCLUDES,
    ]


def application_python_files(root: Path = ROOT) -> set[str]:
    app = root / SCAN_TARGET
    if not app.is_dir():
        raise GateError("missing scan scope: app/ is not a directory")
    if any(app.rglob(".bandit")):
        raise GateError("app/ contains a .bandit file; the gate does not accept scanner config")
    found: set[str] = set()
    for path in app.rglob("*.py"):
        if _excluded_source(path):
            continue
        found.add(path.relative_to(root).as_posix())
    if not found:
        raise GateError("missing scan scope: app/ contains no Python files")
    return found


def _excluded_source(path: Path) -> bool:
    return any(part in _EXCLUDED_DIR_NAMES or part.endswith(".egg") for part in path.parts)


def relative_python_path(filename: str, root: Path = ROOT) -> str:
    raw = filename.replace("\\", "/")
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        candidate = Path(filename)
        try:
            raw = candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise GateError(f"Bandit reported a file outside the repository: {filename}") from exc
    if raw.startswith("./"):
        raw = raw[2:]
    if (
        not raw.startswith(f"{SCAN_TARGET}/")
        or not raw.endswith(".py")
        or ".." in raw.split("/")
        or "*" in raw
        or "?" in raw
    ):
        raise GateError(f"Bandit reported a path outside app/**/*.py: {filename}")
    return raw


def parse_code_lines(code: str) -> dict[int, str]:
    """Map snippet line numbers to source text. The number prefix is discarded."""
    if not isinstance(code, str) or not code.strip():
        raise GateError("Bandit finding is missing its source snippet")
    parsed: dict[int, str] = {}
    for raw in code.splitlines():
        number, separator, source = raw.partition(" ")
        if separator != " " or not number.isdigit():
            raise GateError("Bandit source snippet is not line-numbered")
        lineno = int(number)
        if lineno in parsed:
            raise GateError(f"Bandit source snippet repeats line {lineno}")
        parsed[lineno] = source.rstrip()
    return parsed


def normalized_source(code: str, line_range: list[int]) -> str:
    parsed = parse_code_lines(code)
    missing = [str(number) for number in line_range if number not in parsed]
    if missing:
        raise GateError("Bandit source snippet does not cover line_range " + ",".join(missing))
    return "\n".join(parsed[number] for number in line_range)


def code_fingerprint(code: str, line_range: list[int], issue_text: str) -> str:
    """Hash the finding's source and Bandit's message, not the line numbers.

    ``issue_text`` keeps two findings that share one AST node distinct. The
    text is not stored in the baseline.
    """
    if not isinstance(issue_text, str) or not issue_text.strip():
        raise GateError("Bandit finding is missing issue_text")
    payload = normalized_source(code, line_range) + "\n---\n" + issue_text.strip()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _line_range(value: object) -> list[int]:
    if not isinstance(value, list) or not value:
        raise GateError("Bandit finding is missing line_range")
    lines: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise GateError("Bandit finding line_range is not a list of line numbers")
        lines.append(item)
    if len(set(lines)) != len(lines):
        raise GateError("Bandit finding line_range repeats a line")
    return sorted(lines)


def finding_from_result(result: dict) -> Finding:
    if not isinstance(result, dict):
        raise GateError("Bandit result is not an object")
    path = relative_python_path(str(result.get("filename", "")))
    test_id = result.get("test_id")
    if not isinstance(test_id, str) or _TEST_ID.fullmatch(test_id) is None:
        raise GateError(f"Bandit result has an unexpected test id: {test_id!r}")
    severity = result.get("issue_severity")
    confidence = result.get("issue_confidence")
    if severity not in SEVERITIES or confidence not in SEVERITIES:
        raise GateError(f"Bandit result has an unexpected severity or confidence: {path}")
    line_number = result.get("line_number")
    if isinstance(line_number, bool) or not isinstance(line_number, int) or line_number < 1:
        raise GateError(f"Bandit result is missing a line number: {path}")
    line_range = _line_range(result.get("line_range"))
    code = result.get("code")
    issue_text = result.get("issue_text")
    fingerprint = code_fingerprint(
        code if isinstance(code, str) else "",
        line_range,
        issue_text if isinstance(issue_text, str) else "",
    )
    return Finding(
        path=path,
        test_id=test_id,
        severity=severity,
        confidence=confidence,
        code_sha256=fingerprint,
        line_number=line_number,
    )


def _reject_wildcard(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise GateError(f"baseline exception {label} must be one exact string")
    if value.strip().lower() in {"", "*", "all", "any"} or "*" in value or "?" in value:
        raise GateError(f"baseline exception {label} must be one exact value, not a wildcard")
    return value


def _validate_exception(index: int, item: object) -> None:
    if not isinstance(item, dict):
        raise GateError(f"baseline exception {index} must be an object")
    extra = set(item) - _EXCEPTION_KEYS
    if extra:
        raise GateError(f"baseline exception {index} has unknown fields: {sorted(extra)}")
    missing = _EXCEPTION_KEYS - set(item)
    if missing:
        raise GateError(f"baseline exception {index} is missing {sorted(missing)}")
    path = _reject_wildcard(item["path"], f"{index}.path")
    outside = (
        not path.startswith(f"{SCAN_TARGET}/")
        or not path.endswith(".py")
        or ".." in path.split("/")
    )
    if outside:
        raise GateError(f"baseline exception {index} path is outside {SCOPE}")
    test_id = _reject_wildcard(item["test_id"], f"{index}.test_id")
    if _TEST_ID.fullmatch(test_id) is None:
        raise GateError(f"baseline exception {index} test_id must be one Bandit id")
    for field in ("severity", "confidence"):
        value = _reject_wildcard(item[field], f"{index}.{field}")
        if value not in SEVERITIES:
            raise GateError(f"baseline exception {index} {field} is not a Bandit rank")
    digest = item["code_sha256"]
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise GateError(f"baseline exception {index} code_sha256 must be one sha256 hex digest")
    rationale = item["rationale"]
    if rationale not in RATIONALES:
        raise GateError(f"baseline exception {index} rationale is not an allowed value")
    reason = item["reason"]
    if not isinstance(reason, str) or not reason.strip() or "\n" in reason or len(reason) > 300:
        raise GateError(f"baseline exception {index} reason must be one short line")
    if reason.strip().lower() in {"*", "all", "any", "ignore"}:
        raise GateError(f"baseline exception {index} reason must describe this finding")


def load_baseline(path: Path) -> dict:
    if not path.is_file():
        raise GateError(f"missing SAST baseline at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"SAST baseline is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError("SAST baseline must be a JSON object")
    extra = set(data) - _BASELINE_KEYS
    if extra:
        raise GateError(f"SAST baseline has unknown fields: {sorted(extra)}")
    if data.get("version") != 1:
        raise GateError("SAST baseline version must be 1")
    if data.get("scanner") != SCANNER:
        raise GateError("SAST baseline scanner must be bandit")
    if data.get("scanner_version") != BANDIT_VERSION:
        raise GateError(f"SAST baseline scanner_version must be {BANDIT_VERSION}")
    if data.get("scope") != SCOPE:
        raise GateError(f"SAST baseline scope must be {SCOPE}")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        raise GateError("SAST baseline exceptions must be a list")
    for index, item in enumerate(exceptions):
        _validate_exception(index, item)
    return data


def exception_matches(finding: Finding, exception: dict) -> bool:
    return (
        exception["path"] == finding.path
        and exception["test_id"] == finding.test_id
        and exception["severity"] == finding.severity
        and exception["confidence"] == finding.confidence
        and exception["code_sha256"] == finding.code_sha256
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
        if match_at is None:
            regressions.append(
                "stale baseline exception "
                f"{index}: {exception['path']} {exception['test_id']} "
                f"{exception['severity']} {exception['confidence']} "
                f"sha256={exception['code_sha256']}"
            )
        else:
            del unmatched[match_at]
    ordered = sorted(
        unmatched,
        key=lambda item: (item.path, item.test_id, item.line_number, item.code_sha256),
    )
    regressions.extend(f"unbaselined SAST finding: {finding.label()}" for finding in ordered)
    return regressions


def require_scanner_version(installed: str) -> None:
    if installed != BANDIT_VERSION:
        raise GateError(f"installed bandit is {installed}; this gate requires {BANDIT_VERSION}")


def installed_bandit_version() -> str:
    import bandit

    module_version = getattr(bandit, "__version__", "")
    proc = subprocess.run(
        [sys.executable, "-m", "bandit", "--version"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "bandit --version failed").strip()
        raise GateError(detail)
    first = (proc.stdout or "").splitlines()
    token = first[0].split() if first else []
    if len(token) < 2:
        raise GateError(f"unexpected bandit version output: {proc.stdout!r}")
    cli_version = token[-1]
    if module_version != cli_version:
        raise GateError(
            f"bandit module version {module_version} does not match CLI version {cli_version}"
        )
    require_scanner_version(cli_version)
    return cli_version


def interpret_scanner_output(returncode: int, text: str) -> dict:
    """Accept Bandit's findings-found exit. Reject crashes and unreadable JSON."""
    if returncode not in (0, 1):
        raise GateError(f"bandit failed with exit {returncode}")
    if not text.strip():
        raise GateError("bandit returned no JSON")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GateError(f"bandit JSON did not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise GateError("bandit JSON was not an object")
    return data


def parse_bandit_payload(data: dict, expected_files: set[str]) -> list[Finding]:
    for key in ("errors", "generated_at", "metrics", "results"):
        if key not in data:
            raise GateError(f"bandit JSON is missing {key}")
    if not isinstance(data["generated_at"], str) or not data["generated_at"]:
        raise GateError("bandit JSON generated_at is incomplete")
    errors = data["errors"]
    if not isinstance(errors, list):
        raise GateError("bandit JSON errors is not a list")
    if errors:
        first = errors[0]
        raise GateError(f"bandit reported a scan error: {first!r}")
    results = data["results"]
    if not isinstance(results, list):
        raise GateError("bandit JSON results is not a list")
    metrics = data["metrics"]
    if not isinstance(metrics, dict) or "_totals" not in metrics:
        raise GateError("bandit JSON metrics are incomplete")
    totals = metrics["_totals"]
    if not isinstance(totals, dict):
        raise GateError("bandit JSON metric totals are incomplete")
    for key in _TOTAL_KEYS:
        if not isinstance(totals.get(key), int):
            raise GateError(f"bandit JSON metric totals are missing {key}")
    if totals["nosec"] != 0:
        raise GateError("bandit found # nosec comments; suppressions belong in the baseline")
    if totals["skipped_tests"] != 0:
        raise GateError("bandit skipped tests; this gate runs the full test set")
    severity_total = sum(totals[f"SEVERITY.{name}"] for name in SEVERITIES)
    confidence_total = sum(totals[f"CONFIDENCE.{name}"] for name in SEVERITIES)
    if severity_total != len(results) or confidence_total != len(results):
        raise GateError("bandit JSON results do not match its metric totals")
    scanned = {relative_python_path(key) for key in metrics if key != "_totals"}
    missing = sorted(expected_files - scanned)
    extra = sorted(scanned - expected_files)
    if missing or extra:
        raise GateError(
            "bandit did not scan exactly app/**/*.py: "
            f"missing={missing[:5] or '[]'} extra={extra[:5] or '[]'}"
        )
    return [finding_from_result(result) for result in results]


def run_bandit(expected_files: set[str]) -> list[Finding]:
    installed_bandit_version()
    with tempfile.TemporaryDirectory(prefix="bandit-sast-") as tmp:
        output = Path(tmp) / "bandit.json"
        try:
            proc = subprocess.run(
                scanner_command(output),
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            raise GateError("bandit timed out") from exc
        text = output.read_text(encoding="utf-8") if output.is_file() else ""
        if proc.returncode not in (0, 1):
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            tail = detail[-1][:200] if detail else "no output"
            raise GateError(f"bandit failed with exit {proc.returncode}: {tail}")
        payload = interpret_scanner_output(proc.returncode, text)
    return parse_bandit_payload(payload, expected_files)


def run(
    baseline_path: Path = BASELINE_PATH,
    scan: Callable[[set[str]], list[Finding]] = run_bandit,
) -> int:
    baseline = load_baseline(baseline_path)
    expected = application_python_files()
    findings = scan(expected)
    regressions = compare(findings, baseline["exceptions"])
    print(
        "SAST baseline gate: "
        f"scanner={SCANNER} scanner_version={BANDIT_VERSION} scope={SCOPE} "
        f"files={len(expected)} findings={len(findings)} "
        f"exceptions={len(baseline['exceptions'])}"
    )
    if regressions:
        print("FAIL: SAST findings are outside the explicit baseline:", file=sys.stderr)
        for line in regressions:
            print(f"  - {line}", file=sys.stderr)
        print(
            "Fix the finding, or add one exact path+test+severity+confidence+"
            f"fingerprint exception to {baseline_path}.",
            file=sys.stderr,
        )
        return 1
    print("OK: no unbaselined SAST findings")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    args = parser.parse_args(argv)
    try:
        return run(args.baseline)
    except GateError as exc:
        print(f"FAIL: SAST gate did not complete: {exc}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print("FAIL: SAST gate did not complete: bandit timed out", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
