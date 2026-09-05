"""Sprint 29 account, auth, export/delete, and support document routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_JS = (ROOT / "app/static/consumer/js/account.js").read_text(encoding="utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ("/login", "/register", "/reset-password", "/verify-email", "/account", "/support"),
)
async def test_account_document_routes_are_noindex(client: AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 200
    assert response.headers.get("X-Robots-Tag") == "noindex, nofollow"
    assert 'name="robots" content="noindex, nofollow"' in response.text
    assert "PiqSavi" in response.text
    assert "DealBrain" not in response.text


@pytest.mark.asyncio
async def test_login_and_register_forms_wire_existing_auth_apis(client: AsyncClient) -> None:
    login = await client.get("/login")
    register = await client.get("/register")
    assert 'data-account-form="login"' in login.text
    assert 'data-account-form="register"' in register.text
    assert "Forgot password" in login.text
    assert "/reset-password" in login.text
    assert "terms_accepted" in register.text
    assert "privacy_acknowledged" in register.text
    assert "not published yet" in register.text
    assert "/api/v1/auth/login" in ACCOUNT_JS
    assert "/api/v1/auth/register" in ACCOUNT_JS
    assert "/api/v1/auth/account/export" in ACCOUNT_JS
    assert "/api/v1/auth/account/delete" in ACCOUNT_JS
    assert "piqsavi.account_owned_export.v1" in (await client.get("/account")).text


@pytest.mark.asyncio
async def test_password_recovery_and_verification_presentation(client: AsyncClient) -> None:
    reset = await client.get("/reset-password")
    reset_token = await client.get("/reset-password", params={"token": "sample-token"})
    verify = await client.get("/verify-email")
    verify_token = await client.get("/verify-email", params={"token": "sample-token"})
    assert "does not display demo tokens" in reset.text
    assert 'data-account-form="reset-request"' in reset.text
    assert 'data-account-form="reset-confirm"' in reset_token.text
    assert 'name="token" value="sample-token"' in reset_token.text
    assert 'data-account-form="verify-request"' in verify.text
    assert 'data-account-form="verify-confirm"' in verify_token.text
    assert "/api/v1/auth/password-reset" in ACCOUNT_JS
    assert "/api/v1/auth/verify-email" in ACCOUNT_JS


@pytest.mark.asyncio
async def test_account_settings_expose_export_delete_and_sign_out(client: AsyncClient) -> None:
    page = await client.get("/account")
    assert "Download my data" in page.text
    assert "Delete my account" in page.text
    assert 'data-account-action="sign-out"' in page.text
    assert 'data-account-action="export"' in page.text
    assert 'data-account-form="delete"' in page.text
    assert "Watch is not available yet" in page.text
    assert "does not watch prices" in page.text
    assert "complete legal DSAR" in page.text


@pytest.mark.asyncio
async def test_support_entry_is_honest_about_sprint_39(client: AsyncClient) -> None:
    page = await client.get("/support")
    assert "support@piqsavi.com" in page.text
    assert "privacy@piqsavi.com" in page.text
    assert "Report incorrect information" in page.text
    assert "Sprint 39" in page.text
    assert "does not collect a support ticket" in page.text


@pytest.mark.asyncio
async def test_results_header_points_to_account_journey(client: AsyncClient) -> None:
    page = await client.get("/results/headphones-standard")
    assert 'href="/login?next=/results/headphones-standard"' in page.text
    assert 'href="/register?next=/results/headphones-standard"' in page.text
    assert 'href="/account#saved"' in page.text
    assert 'href="/account#watch"' in page.text
    assert "price-update notifications are not available yet" in page.text
    assert "get price updates" not in page.text
    assert 'href="/support"' in page.text


@pytest.mark.asyncio
async def test_register_login_roundtrip_and_export_delete_ui_path(client: AsyncClient) -> None:
    email = "sprint29-account-ui@example.invalid"
    created = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123",
            "display_name": "Sprint 29 UI",
            "terms_accepted": True,
            "privacy_acknowledged": True,
        },
    )
    assert created.status_code == 201
    token = created.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    export = await client.get("/api/v1/auth/account/export", headers=headers)
    assert export.status_code == 200
    assert export.json()["export_schema"] == "piqsavi.account_owned_export.v1"
    deleted = await client.post(
        "/api/v1/auth/account/delete",
        headers=headers,
        json={"confirmation": "DELETE", "password": "Password123"},
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    gone = await client.get("/api/v1/auth/me", headers=headers)
    assert gone.status_code == 401
