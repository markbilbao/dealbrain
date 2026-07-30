#!/usr/bin/env python3
"""Deterministic Sprint 25a secret / forbidden-credential scan.

Scans infra, env examples, and scripts for high-confidence secret patterns and
forbidden Terraform password inputs. Exits 1 on the first class of findings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Fragmented so this file itself is not a false positive for name checks.
_DB_PASSWORD = "db" + "_password"
_TF_VAR_DB_PASSWORD = "TF_VAR_" + _DB_PASSWORD

PATTERN_SPECS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "private_key_pem",
        re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "aws_secret_access_key_assignment",
        re.compile(r"aws_secret_access_key\s*=\s*[\"'][^\"']+[\"']", re.I),
    ),
    (
        "plaintext_password_assignment",
        re.compile(
            r"password\s*=\s*\"(?!CHANGE_ME|REPLACE_ME|use-a-strong)[^\"]{8,}\"",
            re.I,
        ),
    ),
]

SCAN_GLOBS = (
    "infra/**/*",
    ".env*.example",
    "scripts/**/*",
    ".github/workflows/**/*",
)

SKIP_PARTS = {".git", ".venv", ".terraform", "__pycache__", "node_modules"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".pyc"}
# This scanner may mention forbidden names; do not flag itself.
SKIP_FILES = {Path("scripts/secret_scan_25a.py")}


def _iter_files() -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in SCAN_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if rel in SKIP_FILES or path.name == Path(__file__).name:
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


def main() -> int:
    bad = False
    for path in _iter_files():
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Forbidden Terraform password inputs — config files only.
        if (path.suffix == ".tf" or "tfvars" in path.name) and (
            _DB_PASSWORD in text or _TF_VAR_DB_PASSWORD in text
        ):
            print(f"forbidden credential input name in {rel}")
            bad = True
        for label, pattern in PATTERN_SPECS:
            if pattern.search(text):
                print(f"{label} pattern in {rel}")
                bad = True
    if bad:
        print("secret_scan_25a: FAILED", file=sys.stderr)
        return 1
    print("secret_scan_25a: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
