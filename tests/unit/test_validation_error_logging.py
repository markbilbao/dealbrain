"""Privacy-safe shared 422 validation logging (production hardening)."""

from __future__ import annotations

import logging

from app.main import create_app
from fastapi.testclient import TestClient

ERRORS_LOGGER = "app.core.errors"
REQUEST_ID = "req-hardening-422"


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _attach_errors_log_handler() -> tuple[logging.Logger, _ListHandler]:
    handler = _ListHandler()
    handler.setLevel(logging.WARNING)
    logger = logging.getLogger(ERRORS_LOGGER)
    logger.addHandler(handler)
    return logger, handler


def test_early_access_invalid_payload_omits_rejected_values_from_logs() -> None:
    rejected_name = "Ada Lovelace"
    rejected_email = "ada-rejected@example.com"
    rejected_country = "PHILIPPINES"
    logger, handler = _attach_errors_log_handler()
    try:
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/v1/early-access",
                json={
                    "full_name": rejected_name,
                    "email": rejected_email,
                    "country": rejected_country,
                    "shopping_interest": "secret-phones-interest",
                },
                headers={"x-request-id": REQUEST_ID},
            )
    finally:
        logger.removeHandler(handler)
    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "validation_error"
    assert body.get("details")
    assert any(
        isinstance(item, dict) and item.get("input") == rejected_country for item in body["details"]
    )
    log_text = " ".join(handler.messages)
    assert "validation_error" in log_text
    assert "/api/v1/early-access" in log_text
    assert "POST" in log_text
    assert REQUEST_ID in log_text
    assert rejected_name not in log_text
    assert rejected_email not in log_text
    assert "secret-phones-interest" not in log_text
    assert rejected_country not in log_text
    assert "type" in log_text
    assert "loc" in log_text or "country" in log_text


def test_early_access_missing_field_does_not_log_remaining_body() -> None:
    submitted_name = "Grace Hopper"
    submitted_interest = "classified-laptops"
    logger, handler = _attach_errors_log_handler()
    try:
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/v1/early-access",
                json={
                    "full_name": submitted_name,
                    "country": "PH",
                    "shopping_interest": submitted_interest,
                },
                headers={"x-request-id": REQUEST_ID},
            )
    finally:
        logger.removeHandler(handler)
    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "validation_error"
    assert body.get("details")
    dumped = str(body)
    assert submitted_name in dumped or submitted_interest in dumped
    log_text = " ".join(handler.messages)
    assert submitted_name not in log_text
    assert submitted_interest not in log_text
    assert "type" in log_text
    assert "/api/v1/early-access" in log_text
    assert REQUEST_ID in log_text


def test_events_invalid_source_is_not_written_to_validation_log() -> None:
    poisoned = "victim@example.com"
    logger, handler = _attach_errors_log_handler()
    try:
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/v1/early-access/events",
                json={"event": "early_access_cta_clicked", "source": poisoned},
                headers={"x-request-id": REQUEST_ID},
            )
    finally:
        logger.removeHandler(handler)
    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "validation_error"
    assert body.get("details")
    log_text = " ".join(handler.messages)
    assert poisoned not in log_text
    assert "type" in log_text
    assert "/api/v1/early-access/events" in log_text
    assert "POST" in log_text
    assert REQUEST_ID in log_text


def test_auth_login_invalid_payload_is_pii_safe_and_keeps_envelope() -> None:
    login_email = "login-pii@example.com"
    logger, handler = _attach_errors_log_handler()
    try:
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": login_email},
                headers={"x-request-id": REQUEST_ID},
            )
    finally:
        logger.removeHandler(handler)
    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "validation_error"
    assert "detail" in body
    assert body.get("details")
    log_text = " ".join(handler.messages)
    assert login_email not in log_text
    assert "/api/v1/auth/login" in log_text
    assert "POST" in log_text
    assert REQUEST_ID in log_text
    assert "type" in log_text
