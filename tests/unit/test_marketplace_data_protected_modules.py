"""Guard: Sprint 18 Marketplace Data must not modify prior protected modules."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from tests.unit.test_user_platform_protected_modules import PROTECTED_DIGESTS

ROOT = Path(__file__).resolve().parents[2]


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_marketplace_data_service_exists_and_has_no_payments_or_scraping() -> None:
    service_path = ROOT / "app/services/marketplace_data_service.py"
    assert service_path.is_file()
    text = service_path.read_text(encoding="utf-8")
    assert "MarketplaceDataService" in text

    lowered = text.lower()
    assert "import stripe" not in lowered
    assert "import paypal" not in lowered
    assert "from stripe" not in lowered
    assert "from paypal" not in lowered
    assert "scrapy" not in lowered
    assert "beautifulsoup" not in lowered
    assert "selenium" not in lowered
    assert "playwright" not in lowered


def test_marketplace_package_has_no_scraping_or_hardcoded_shopee_secrets() -> None:
    marketplace_root = ROOT / "app/marketplace"
    assert marketplace_root.is_dir()
    secret_patterns = (
        re.compile(r"shopee[_-]?secret\s*=\s*['\"][^'\"]+['\"]", re.I),
        re.compile(r"lazada[_-]?secret\s*=\s*['\"][^'\"]+['\"]", re.I),
        re.compile(r"amazon[_-]?secret\s*=\s*['\"][^'\"]+['\"]", re.I),
        re.compile(r"api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]"),
    )
    for path in marketplace_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "scrapy" not in lowered, f"{path} references scrapy"
        assert "beautifulsoup" not in lowered, f"{path} references beautifulsoup"
        assert "selenium" not in lowered, f"{path} references selenium"
        for pattern in secret_patterns:
            assert pattern.search(text) is None, f"Hardcoded secret-like value in {path}"


def test_no_stripe_paypal_in_marketplace_data_modules() -> None:
    for relative in (
        "app/services/marketplace_data_service.py",
        "app/api/v1/endpoints/marketplace_data.py",
        "app/marketplace/sync/engine.py",
        "app/marketplace/imports/pipeline.py",
        "app/marketplace/connectors/mock_live.py",
    ):
        lowered = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "stripe" not in lowered, f"{relative} references stripe"
        assert "paypal" not in lowered, f"{relative} references paypal"
