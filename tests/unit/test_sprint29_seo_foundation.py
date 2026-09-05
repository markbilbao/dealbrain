"""Sprint 29 robots, sitemap, staging noindex, and public/private SEO split."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.consumer.seo import canonical_url, robots_txt, sitemap_xml
from app.main import create_app
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_robots_and_sitemap_keep_decision_and_account_paths_private(
    client: AsyncClient,
) -> None:
    robots = await client.get("/robots.txt")
    sitemap = await client.get("/sitemap.xml")
    assert robots.status_code == 200
    assert sitemap.status_code == 200
    assert "Disallow: /results/" in robots.text
    assert "Disallow: /compare/" in robots.text
    assert "Disallow: /why-best-piq/" in robots.text
    assert "Disallow: /account" in robots.text
    assert "Allow: /" in robots.text
    assert "Sitemap:" in robots.text
    assert "<loc>https://piqsavi.com/</loc>" in sitemap.text
    assert "/results/" not in sitemap.text
    assert "/account" not in sitemap.text


def test_staging_robots_disallow_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.consumer.seo.get_settings",
        lambda: SimpleNamespace(is_staging=True, public_app_base_url=""),
    )
    text = robots_txt()
    assert "Disallow: /" in text
    assert "Allow: /" not in text


def test_staging_landing_is_noindex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.consumer.seo.get_settings",
        lambda: SimpleNamespace(is_staging=True, public_app_base_url=""),
    )
    monkeypatch.setattr(
        "app.api.early_access_page.get_settings",
        lambda: SimpleNamespace(is_staging=True, public_app_base_url=""),
    )
    with TestClient(create_app()) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Robots-Tag") == "noindex, nofollow"
    assert 'name="robots" content="noindex, nofollow"' in response.text
    assert "Join Early Access" in response.text


def test_development_landing_keeps_canonical_and_json_ld() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "noindex" not in response.headers.get("X-Robots-Tag", "").lower()
    assert 'rel="canonical" href="https://piqsavi.com/"' in response.text
    assert 'type="application/ld+json"' in response.text
    assert '"@type":"Organization"' in response.text
    assert "PiqSavi" in response.text


def test_canonical_url_uses_piqsavi_origin() -> None:
    assert canonical_url("/") == "https://piqsavi.com/"
    assert canonical_url("/sitemap.xml") == "https://piqsavi.com/sitemap.xml"
    assert "/results/" not in sitemap_xml()
