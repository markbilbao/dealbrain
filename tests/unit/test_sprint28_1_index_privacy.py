"""Sprint 28.1 private decision URL search-index protection."""

from __future__ import annotations

from app.consumer.robots import NOINDEX_ROBOTS_TAG, is_private_decision_path
from app.main import create_app
from fastapi.testclient import TestClient

PRIVATE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_private_decision_path_helper() -> None:
    assert is_private_decision_path(f"/results/{PRIVATE_UUID}")
    assert is_private_decision_path(f"/compare/{PRIVATE_UUID}")
    assert is_private_decision_path(f"/why-best-piq/{PRIVATE_UUID}")
    assert not is_private_decision_path("/")
    assert not is_private_decision_path("/privacy")


def test_uuid_results_compare_why_are_noindex() -> None:
    client = TestClient(create_app())
    for path in (
        f"/results/{PRIVATE_UUID}",
        f"/compare/{PRIVATE_UUID}",
        f"/why-best-piq/{PRIVATE_UUID}",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers.get("X-Robots-Tag") == NOINDEX_ROBOTS_TAG
        assert 'name="robots" content="noindex, nofollow"' in response.text
        assert "PiqSavi" in response.text


def test_fixture_decision_pages_are_also_noindex() -> None:
    client = TestClient(create_app())
    for path in (
        "/results/headphones-standard",
        "/compare/headphones-standard",
        "/why-best-piq/headphones-standard",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers.get("X-Robots-Tag") == NOINDEX_ROBOTS_TAG


def test_public_landing_remains_indexable() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    robots = response.headers.get("X-Robots-Tag", "")
    assert "noindex" not in robots.lower()
    assert 'name="robots" content="noindex' not in response.text
    assert "Join Early Access" in response.text
