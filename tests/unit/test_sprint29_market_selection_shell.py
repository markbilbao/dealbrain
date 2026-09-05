"""Sprint 29 market-selection UI shell. Domain policy remains Sprint 37."""

from __future__ import annotations

import pytest
from app.consumer.shopping_market import SHOPPING_MARKET_COOKIE
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_results_include_market_selection_shell(client: AsyncClient) -> None:
    page = await client.get("/results/headphones-standard")
    assert 'class="market-shell"' in page.text
    assert 'action="/consumer/shopping-market"' in page.text
    assert 'name="country_code"' in page.text
    assert 'value="PH"' in page.text
    assert "does not certify live shopping coverage" in page.text
    assert "Sprint 37" in page.text
    assert "United States" not in page.text


@pytest.mark.asyncio
async def test_market_shell_form_post_sets_cookie(client: AsyncClient) -> None:
    response = await client.post(
        "/consumer/shopping-market",
        data={
            "country_code": "PH",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/results/headphones-standard"
    assert SHOPPING_MARKET_COOKIE in response.cookies
