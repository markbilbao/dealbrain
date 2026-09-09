#!/usr/bin/env python3
"""Print non-PII legal publication and tracking posture.

Does not list consent records, emails, or tokens. Owner-scoped consent
inspection uses GET /api/v1/auth/account/consents after authentication.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.legal.publication import catalog_from_settings  # noqa: E402
from app.privacy.consent_audit import publication_status_payload  # noqa: E402


def main() -> int:
    catalog = catalog_from_settings(Settings())
    payload = publication_status_payload(catalog)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
