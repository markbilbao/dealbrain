#!/usr/bin/env python3
"""Structural redaction of database URLs and credential assignments in deploy logs.

Used by the staging host orchestrator so migration/container output never
echoes ``DATABASE_URL`` or connection strings into SSM/CloudWatch. Redaction
is pattern-based — never keyed to a specific password.
"""

from __future__ import annotations

import re
import sys

# Keep patterns local so the host bundle copy stays dependency-free.
_DB_URL_RE = re.compile(
    r"(?i)\b(?:postgresql(?:\+\w+)?|postgres(?:\+\w+)?|mysql(?:\+\w+)?"
    r"|mariadb(?:\+\w+)?|sqlite(?:\+\w+)?|mssql(?:\+\w+)?)"
    r"://[^\s\"'<>]+"
)
_DATABASE_URL_ASSIGN_RE = re.compile(r"(?i)\bDATABASE_URL\s*[:=]\s*[\"']?[^\s\"']+")
_PASSWORD_ASSIGN_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api_key|access_key)\s*[:=]\s*\S+"
)


def redact_deploy_text(text: str) -> str:
    """Return text with connection strings and secret assignments redacted."""
    out = _DB_URL_RE.sub("***REDACTED_DATABASE_URL***", text)
    out = _DATABASE_URL_ASSIGN_RE.sub("DATABASE_URL=***REDACTED***", out)
    return _PASSWORD_ASSIGN_RE.sub(r"\1=***REDACTED***", out)


def main(argv: list[str] | None = None) -> int:
    _ = argv
    data = sys.stdin.read()
    sys.stdout.write(redact_deploy_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
