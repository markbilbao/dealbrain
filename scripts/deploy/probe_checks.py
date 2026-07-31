"""HTTP probe response content checks (Sprint 22 schemas; no endpoint changes)."""

from __future__ import annotations

import json
from typing import Any


class ProbeCheckError(ValueError):
    """Raised when a probe response fails content validation."""


def validate_live_response(payload: Any) -> None:
    """Require Sprint 22 LiveResponse semantics (not HTTP status alone)."""
    if not isinstance(payload, dict):
        raise ProbeCheckError("live response must be a JSON object")
    if payload.get("live") is not True:
        raise ProbeCheckError("live response requires live == true")
    if not isinstance(payload.get("status"), str) or not payload["status"]:
        raise ProbeCheckError("live response requires non-empty status string")
    if not isinstance(payload.get("service"), str) or not payload["service"]:
        raise ProbeCheckError("live response requires non-empty service string")


def validate_ready_response(payload: Any) -> None:
    """Require Sprint 22 ReadyResponse ready == true."""
    if not isinstance(payload, dict):
        raise ProbeCheckError("ready response must be a JSON object")
    if payload.get("ready") is not True:
        raise ProbeCheckError("ready response requires ready == true")
    if not isinstance(payload.get("status"), str) or not payload["status"]:
        raise ProbeCheckError("ready response requires non-empty status string")


def validate_live_json_text(text: str) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProbeCheckError(f"live response is not valid JSON: {exc}") from exc
    validate_live_response(payload)


def validate_ready_json_text(text: str) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProbeCheckError(f"ready response is not valid JSON: {exc}") from exc
    validate_ready_response(payload)
