#!/usr/bin/env python3
"""Deterministic secret scan for infrastructure, examples, scripts, workflows, and app.

The gate reads the committed baseline at
``tests/security/baselines/secret-scan.baseline.json``. High-confidence
regex rules still cover AWS keys, private-key markers, AWS secret
assignments, plaintext password assignments, and forbidden Terraform
password inputs. Application Python additionally uses ``ast.parse`` to
find a non-empty string literal assigned to a credential-sensitive name.

Findings are identified by rule, relative path, symbol, and a SHA-256 of
normalized source. The literal credential is not printed and is not stored
in the baseline. One exception matches one finding. The process exits 1
when a finding is unbaselined, an exception is stale, or the scan cannot
finish.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "security" / "baselines" / "secret-scan.baseline.json"
BASELINE_VERSION = 1
SCANNER = "secret_scan_25a"

RULE_AWS_ACCESS_KEY = "aws_access_key_id"
RULE_PRIVATE_KEY = "private_key_pem"
RULE_AWS_SECRET = "aws_secret_access_key_assignment"
RULE_PASSWORD = "plaintext_password_assignment"
RULE_PYTHON_LITERAL = "python_credential_literal"
RULE_TERRAFORM_PASSWORD = "forbidden_credential_input_name"

RULE_IDS = (
    RULE_AWS_ACCESS_KEY,
    RULE_PRIVATE_KEY,
    RULE_AWS_SECRET,
    RULE_PASSWORD,
    RULE_PYTHON_LITERAL,
    RULE_TERRAFORM_PASSWORD,
)
RATIONALES = (
    "safe_demo_constant",
    "documented_placeholder",
    "false_positive",
)
_BASELINE_KEYS = {"version", "scanner", "scope", "exceptions"}
_EXCEPTION_KEYS = {
    "path",
    "rule_id",
    "symbol",
    "source_fingerprint",
    "rationale",
    "reason",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
_ASSIGN_SYMBOL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=\n]+)?=")

# Fragmented so this file itself is not a false positive for name checks.
_DB_PASSWORD = "db" + "_password"
_TF_VAR_DB_PASSWORD = "TF_VAR_" + _DB_PASSWORD

_PATTERN_SPECS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (RULE_AWS_ACCESS_KEY, re.compile(r"AKIA[0-9A-Z]{16}")),
    (RULE_PRIVATE_KEY, re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----")),
    (
        RULE_AWS_SECRET,
        re.compile(r"aws_secret_access_key\s*=\s*[\"'][^\"']+[\"']", re.I),
    ),
    (
        RULE_PASSWORD,
        re.compile(
            r"password\s*=\s*\"(?!CHANGE_ME|REPLACE_ME|use-a-strong)[^\"]{8,}\"",
            re.I,
        ),
    ),
)

SCAN_GLOBS = (
    "infra/**/*",
    ".env*.example",
    "scripts/**/*",
    ".github/workflows/**/*",
    "app/**/*.py",
)
APPLICATION_GLOB = "app/**/*.py"
SKIP_PARTS = {".git", ".venv", ".terraform", "__pycache__", "node_modules"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".pyc"}
# This scanner's own source may contain pattern text. The skip is this path
# only and does not exclude other files under scripts/.
SKIP_FILES = {Path("scripts/secret_scan_25a.py")}

_SENSITIVE_SEGMENTS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "secret",
        "credential",
        "credentials",
    }
)
_SENSITIVE_COMPACT = frozenset({"apikey", "privatekey", "accesskey"})
_SENSITIVE_PAIRS = frozenset(
    {
        ("api", "key"),
        ("private", "key"),
        ("access", "key"),
    }
)
_FIELD_NAMES = frozenset({"Field", "field"})


class ScanError(Exception):
    """The scan did not finish or the baseline cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    path: str
    rule_id: str
    symbol: str
    source_fingerprint: str

    def label(self, prefix: str) -> str:
        symbol = self.symbol or "-"
        return (
            f"{prefix} rule={self.rule_id} path={self.path} "
            f"symbol={symbol} source_fingerprint={self.source_fingerprint}"
        )


@dataclass(frozen=True)
class ScanResult:
    files: int
    application_python: int
    findings: tuple[Finding, ...]


def is_credential_name(name: str) -> bool:
    """Return True when ``name`` is a credential-sensitive identifier.

    Matching uses identifier segments, not a search of ordinary prose. A name
    matches when a segment is ``password``, ``passwd``, ``token``, ``secret``,
    or ``credential``, or when adjacent segments are ``api``/``key``,
    ``private``/``key``, or ``access``/``key``.
    """
    segments = _identifier_segments(name)
    if any(segment in _SENSITIVE_SEGMENTS or segment in _SENSITIVE_COMPACT for segment in segments):
        return True
    return any(
        (segments[index], segments[index + 1]) in _SENSITIVE_PAIRS
        for index in range(len(segments) - 1)
    )


def scan_tree(root: Path) -> ScanResult:
    """Scan ``root`` with the committed globs. Parse failures fail closed."""
    files = _iter_files(root)
    findings: list[Finding] = []
    application_python = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = _read_required(path, rel)
        if _is_application_python(rel):
            application_python += 1
            findings.extend(_scan_application_python(rel, text))
        else:
            findings.extend(_regex_findings(rel, text))
            findings.extend(_terraform_findings(path, rel, text))
    findings.sort(key=lambda item: (item.path, item.rule_id, item.symbol, item.source_fingerprint))
    return ScanResult(
        files=len(files),
        application_python=application_python,
        findings=tuple(findings),
    )


def load_baseline(path: Path) -> dict:
    """Load one exact-exception baseline. Malformed input fails closed."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScanError("malformed baseline") from exc
    if not isinstance(payload, dict) or set(payload) != _BASELINE_KEYS:
        raise ScanError("malformed baseline")
    version = payload["version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise ScanError("malformed baseline")
    if version != BASELINE_VERSION:
        raise ScanError(f"unsupported baseline version: {version}")
    if payload["scanner"] != SCANNER:
        raise ScanError("malformed baseline")
    scope = payload["scope"]
    if not isinstance(scope, list) or not all(isinstance(item, str) for item in scope):
        raise ScanError("malformed baseline")
    if APPLICATION_GLOB not in scope or APPLICATION_GLOB not in SCAN_GLOBS:
        raise ScanError("missing application scan scope")
    if scope != list(SCAN_GLOBS):
        raise ScanError("baseline scope does not match the scanner")
    exceptions = payload["exceptions"]
    if not isinstance(exceptions, list):
        raise ScanError("malformed baseline")
    for item in exceptions:
        _validate_exception(item)
    return payload


def compare_findings(findings: Sequence[Finding], exceptions: Sequence[dict]) -> list[str]:
    """Return fail-closed problem lines. An empty list means the sets match.

    Comparison is a multiset of path, rule, symbol, and source fingerprint.
    One exception consumes one finding. Extra copies on either side fail.
    """
    found: Counter[tuple[str, str, str, str]] = Counter(_identity(item) for item in findings)
    allowed: Counter[tuple[str, str, str, str]] = Counter(
        (
            item["path"],
            item["rule_id"],
            item["symbol"],
            item["source_fingerprint"],
        )
        for item in exceptions
    )
    problems: list[str] = []
    for key in sorted(set(found) | set(allowed)):
        extra_findings = found[key] - allowed[key]
        extra_exceptions = allowed[key] - found[key]
        path, rule_id, symbol, fingerprint = key
        label = (
            f"rule={rule_id} path={path} symbol={symbol or '-'} source_fingerprint={fingerprint}"
        )
        problems.extend(f"unbaselined finding {label}" for _ in range(extra_findings))
        if extra_exceptions and found[key] == 0:
            problems.extend(f"stale baseline exception {label}" for _ in range(extra_exceptions))
        elif extra_exceptions:
            problems.extend(
                f"duplicate exception exceeds finding multiplicity {label}"
                for _ in range(extra_exceptions)
            )
    return problems


def main() -> int:
    try:
        baseline = load_baseline(BASELINE_PATH)
        result = scan_tree(ROOT)
        if result.application_python < 1:
            raise ScanError("missing application scan scope")
        problems = compare_findings(result.findings, baseline["exceptions"])
    except ScanError as exc:
        print(f"secret_scan_25a: FAILED {exc}", file=sys.stderr)
        return 1
    if problems:
        for line in problems:
            print(line)
        print("secret_scan_25a: FAILED", file=sys.stderr)
        return 1
    exception_count = len(baseline["exceptions"])
    print("secret_scan_25a: OK")
    print(
        "secret_scan_25a: "
        f"files={result.files} application_python={result.application_python} "
        f"findings={len(result.findings)} exceptions={exception_count}"
    )
    return 0


def _identity(finding: Finding) -> tuple[str, str, str, str]:
    return (finding.path, finding.rule_id, finding.symbol, finding.source_fingerprint)


def _identifier_segments(name: str) -> tuple[str, ...]:
    segments: list[str] = []
    for chunk in name.split("_"):
        if not chunk:
            continue
        pieces = _CAMEL.findall(chunk)
        segments.extend(piece.lower() for piece in (pieces or [chunk]))
    return tuple(segments)


def _is_application_python(rel: str) -> bool:
    return rel.startswith("app/") and rel.endswith(".py") and ".." not in rel.split("/")


def _iter_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root)
            except ValueError as exc:
                raise ScanError(f"path outside repository: {path}") from exc
            if rel in SKIP_FILES:
                continue
            if any(part in SKIP_PARTS for part in rel.parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            files.append(path)
    return sorted(files)


def _read_required(path: Path, rel: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ScanError(f"unable to read required scanned file: {rel}") from exc


def _scan_application_python(rel: str, text: str) -> list[Finding]:
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as exc:
        raise ScanError(f"Python syntax parse failure: {rel}:{exc.lineno or 0}") from exc
    findings = _regex_findings(rel, text)
    visitor = _CredentialVisitor(rel)
    visitor.visit(tree)
    findings.extend(visitor.findings)
    return findings


def _regex_findings(rel: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for rule_id, pattern in _PATTERN_SPECS:
        for match in pattern.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            local_start = match.start() - line_start
            local_end = match.end() - line_start
            symbol = _assignment_symbol(line, local_start, local_end)
            digest = _sha256(match.group(0))
            normalized = f"{line[:local_start]}<sha256:{digest}>{line[local_end:]}".strip()
            findings.append(
                Finding(
                    path=rel,
                    rule_id=rule_id,
                    symbol=symbol,
                    source_fingerprint=_fingerprint(rel, rule_id, symbol, normalized),
                )
            )
    return findings


def _assignment_symbol(line: str, match_start: int, match_end: int) -> str:
    found = _ASSIGN_SYMBOL.match(line)
    if found is None or match_end <= found.start(1):
        return ""
    return found.group(1)


def _terraform_findings(path: Path, rel: str, text: str) -> list[Finding]:
    if path.suffix != ".tf" and "tfvars" not in path.name:
        return []
    findings: list[Finding] = []
    for symbol in (_DB_PASSWORD, _TF_VAR_DB_PASSWORD):
        if symbol not in text:
            continue
        findings.append(
            Finding(
                path=rel,
                rule_id=RULE_TERRAFORM_PASSWORD,
                symbol=symbol,
                source_fingerprint=_fingerprint(rel, RULE_TERRAFORM_PASSWORD, symbol, symbol),
            )
        )
    return findings


def _fingerprint(path: str, rule_id: str, symbol: str, normalized: str) -> str:
    material = "\n".join((rule_id, path, symbol, normalized))
    return _sha256(material)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_statement(statement: ast.AST) -> str:
    redacted = _Redactor().visit(copy.deepcopy(statement))
    return ast.dump(redacted, include_attributes=False)


class _Redactor(ast.NodeTransformer):
    """Replace non-empty string literals with a one-way hash."""

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        if isinstance(node.value, str) and node.value != "":
            return ast.Constant(value=f"sha256:{_sha256(node.value)}")
        return node


class _CredentialVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.findings: list[Finding] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        self._assign(node, node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._assign(node, [node.target], node.value)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._defaults(node.args)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._defaults(node.args)
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._defaults(node.args)
        self.generic_visit(node)

    def _defaults(self, args: ast.arguments) -> None:
        if args.defaults:
            positional = [*args.posonlyargs, *args.args]
            paired = positional[-len(args.defaults) :]
            for arg, default in zip(paired, args.defaults, strict=True):
                self._bind(default, arg.arg, default)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            if default is not None:
                self._bind(default, arg.arg, default)

    def _assign(self, statement: ast.AST, targets: Sequence[ast.expr], value: ast.expr) -> None:
        if len(targets) == 1 and isinstance(targets[0], ast.Tuple | ast.List):
            target = targets[0]
            if isinstance(value, ast.Tuple | ast.List) and len(target.elts) == len(value.elts):
                for element, subvalue in zip(target.elts, value.elts, strict=True):
                    symbol = _target_symbol(element)
                    if symbol is not None:
                        self._bind(subvalue, symbol, subvalue)
                return
        for target in targets:
            symbol = _target_symbol(target)
            if symbol is not None:
                self._bind(statement, symbol, value)

    def _bind(self, statement: ast.AST, symbol: str, value: ast.AST) -> None:
        if not is_credential_name(symbol):
            return
        literal = _configured_literal(value)
        if literal is None or literal == "":
            return
        self.findings.append(
            Finding(
                path=self.path,
                rule_id=RULE_PYTHON_LITERAL,
                symbol=symbol,
                source_fingerprint=_fingerprint(
                    self.path,
                    RULE_PYTHON_LITERAL,
                    symbol,
                    _normalize_statement(statement),
                ),
            )
        )


def _target_symbol(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _configured_literal(value: ast.AST) -> str | None:
    direct = _string_literal(value)
    if direct is not None:
        return direct
    if not isinstance(value, ast.Call):
        return None
    for keyword in value.keywords:
        if keyword.arg == "default":
            return _string_literal(keyword.value)
    if _call_name(value) in _FIELD_NAMES and value.args:
        return _string_literal(value.args[0])
    return None


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            parts.append(value.value)
        return "".join(parts)
    return None


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _validate_exception(item: object) -> None:
    if not isinstance(item, dict) or set(item) != _EXCEPTION_KEYS:
        raise ScanError("malformed baseline")
    path = item["path"]
    rule_id = item["rule_id"]
    symbol = item["symbol"]
    fingerprint = item["source_fingerprint"]
    rationale = item["rationale"]
    reason = item["reason"]
    values = (path, rule_id, symbol, fingerprint, rationale, reason)
    if not all(isinstance(value, str) for value in values):
        raise ScanError("malformed baseline")
    _reject_outside_path(path)
    _reject_wildcard("path", path)
    _reject_wildcard("rule", rule_id)
    _reject_wildcard("symbol", symbol)
    if rule_id not in RULE_IDS:
        raise ScanError("malformed baseline")
    if symbol != "" and _SYMBOL.fullmatch(symbol) is None:
        raise ScanError("malformed baseline")
    if _SHA256.fullmatch(fingerprint) is None:
        raise ScanError("malformed baseline")
    if rationale not in RATIONALES:
        raise ScanError(f"unknown rationale: {rationale}")
    if reason.strip() == "" or "\n" in reason or len(reason) > 400:
        raise ScanError("malformed baseline")


def _reject_outside_path(path: str) -> None:
    if path.startswith("/") or path.startswith("\\") or re.match(r"^[A-Za-z]:", path):
        raise ScanError(f"path outside repository: {path}")
    parts = path.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ScanError(f"path outside repository: {path}")


def _reject_wildcard(label: str, value: str) -> None:
    if any(token in value for token in ("*", "?", "[")):
        raise ScanError(f"wildcard {label} exception")


if __name__ == "__main__":
    raise SystemExit(main())
