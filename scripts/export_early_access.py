"""Operator CLI: export Early Access registrations as a private CSV.

The export must be written to a new caller-supplied path outside this
repository. The file is created with mode 0600 and is never written to
stdout. This is not a public HTTP endpoint.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.database.repositories.early_access_repository import (  # noqa: E402
    SqlAlchemyEarlyAccessRepository,
)
from app.infrastructure.persistence.binding import resolve_persistence_default  # noqa: E402

FIELDS = (
    "id",
    "full_name",
    "email",
    "normalized_email",
    "country",
    "shopping_interest",
    "source",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "referrer",
    "email_confirmation_status",
    "email_confirmation_sent_at",
    "created_at",
    "updated_at",
)


_FORMULA_PREFIXES = frozenset("=+-@")
_USER_CONTROLLED_FIELDS = frozenset(
    {
        "full_name",
        "email",
        "normalized_email",
        "shopping_interest",
        "source",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "referrer",
    }
)


def csv_cell(value: object) -> str:
    """Render one CSV cell, neutralizing spreadsheet formula injection.

    Values whose first non-whitespace character is ``=``, ``+``, ``-``, or
    ``@`` are prefixed with a single quote so Excel/Sheets treat them as text.
    Ordinary names, emails, and Unicode are unchanged.
    """
    if value is None:
        return ""
    text = value.isoformat() if hasattr(value, "isoformat") else str(value)
    stripped = text.lstrip(" \t\r\n")
    if stripped[:1] in _FORMULA_PREFIXES:
        return "'" + text
    return text


def _cell(value: object) -> str:
    return csv_cell(value)


def export_rows(out) -> int:  # noqa: ANN001
    if resolve_persistence_default() != "sqlalchemy":
        print(
            "Early Access export requires the SQLAlchemy operational store "
            "(set PERSISTENCE_BACKEND=sqlalchemy).",
            file=sys.stderr,
        )
        return 2
    repo = SqlAlchemyEarlyAccessRepository()
    rows = repo.list_all()
    writer = csv.DictWriter(out, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    for item in rows:
        writer.writerow(
            {
                name: csv_cell(getattr(item, name))
                if name in _USER_CONTROLLED_FIELDS
                else _cell(getattr(item, name))
                for name in FIELDS
            }
        )
    return 0


def _validated_output_path(path: Path) -> Path:
    expanded = path.expanduser()
    resolved = expanded.parent.resolve(strict=False) / expanded.name
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("output must be outside the repository")
    if not resolved.parent.is_dir():
        raise ValueError("output parent directory must already exist")
    if resolved.is_symlink():
        raise ValueError("output path must not be a symlink")
    return resolved


def write_private_export(path: Path) -> int:
    """Write one new owner-only export without stdout or overwrite fallback."""
    destination = _validated_output_path(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(destination, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            fd = -1
            result = export_rows(handle)
            handle.flush()
            os.fsync(handle.fileno())
        if result != 0:
            destination.unlink(missing_ok=True)
        return result
    except Exception:
        if fd >= 0:
            os.close(fd)
        destination.unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export PiqSavi Early Access registrations to CSV."
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New private CSV path outside the repository (created mode 0600).",
    )
    args = parser.parse_args(argv)
    try:
        return write_private_export(args.out)
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"Export refused: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("Export failed; no output was retained.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
