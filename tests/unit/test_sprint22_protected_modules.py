"""Guard: Sprint 22 must not modify DealScore / recommendation ranking modules."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_sprint21_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

PROTECTED_DIGESTS = dict(PRIOR)

RANKING_MODULES = (
    "app/intelligence/dealscore/engine.py",
    "app/intelligence/recommendation/engine.py",
    "app/intelligence/shopping_assistant/recommendation.py",
)

RANKING_FORBIDDEN = (
    "commission",
    "payout",
    "adsense",
    "sponsored",
    "stripe",
    "paypal",
)


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_ranking_modules_have_no_monetization_bias() -> None:
    for relative in RANKING_MODULES:
        lowered = (ROOT / relative).read_text(encoding="utf-8").lower()
        for token in RANKING_FORBIDDEN:
            assert token not in lowered, f"{relative} references forbidden token {token!r}"


def test_launch_package_avoids_real_vendors() -> None:
    package_root = ROOT / "app/launch"
    assert package_root.is_dir()
    forbidden = ("stripe", "paypal", "adsense", "twilio", "sendgrid", "celery")
    for path in package_root.rglob("*.py"):
        lowered = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in lowered, f"{path} references forbidden token {token!r}"


def test_launch_docs_exist() -> None:
    for name in (
        "LAUNCH_CHECKLIST.md",
        "DEPLOYMENT.md",
        "PRODUCTION.md",
        "SECURITY.md",
        "OPERATIONS.md",
        "MONITORING.md",
        "BACKUP_RESTORE.md",
        "LAUNCH_READINESS.md",
    ):
        assert (ROOT / "docs" / name).is_file(), name
