"""Operator CLI: export Early Access registrations as CSV.

Writes to a caller-supplied path (or stdout). Does not write PII into git.
This is not a public HTTP endpoint.
"""

from __future__ import annotations

import argparse
import csv
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export PiqSavi Early Access registrations to CSV."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Destination CSV path. Defaults to stdout. Do not place this file in git.",
    )
    args = parser.parse_args(argv)
    if args.out is None:
        return export_rows(sys.stdout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        return export_rows(handle)


if __name__ == "__main__":
    raise SystemExit(main())
