"""Sprint 31 connector reliability contract tests.

These types are exported for Sprints 32–36. They do not perform HTTP.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.domain.entities.connector_reliability import (
    BoundedRetryPolicy,
    CircuitBreakerSnapshot,
    CircuitBreakerState,
    ConnectorFailureKind,
    CredentialFailure,
    ExponentialBackoffPolicy,
    KillSwitch,
    PartialFailure,
    QuotaFailure,
    TimeoutPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
RELIABILITY = ROOT / "app/domain/entities/connector_reliability.py"


def test_timeout_retry_and_backoff_contracts_are_declarative() -> None:
    timeout = TimeoutPolicy(timeout_ms=1500)
    retry = BoundedRetryPolicy(max_attempts=3, retry_on=("timeout",))
    backoff = ExponentialBackoffPolicy(initial_delay_ms=50, multiplier=2.0, max_delay_ms=400)
    assert timeout.to_dict()["timeout_ms"] == 1500
    assert retry.to_dict()["max_attempts"] == 3
    assert backoff.to_dict()["max_delay_ms"] == 400


def test_failure_result_types_do_not_carry_secrets() -> None:
    quota = QuotaFailure(retry_after_ms=1000)
    credential = CredentialFailure(message="credential rejected")
    partial = PartialFailure(
        completed_capabilities=("current_pricing",),
        missing_capabilities=("shipping",),
    )
    assert "password" not in credential.to_dict()["message"]
    assert credential.retryable is False
    assert quota.kind is ConnectorFailureKind.QUOTA
    assert partial.missing_capabilities == ("shipping",)


def test_kill_switch_and_open_circuit_block_execution() -> None:
    engaged = KillSwitch(engaged=True, reason="operator_disabled")
    open_breaker = CircuitBreakerSnapshot(state=CircuitBreakerState.OPEN)
    closed = CircuitBreakerSnapshot()
    assert engaged.engaged is True
    assert open_breaker.allows_execution is False
    assert closed.allows_execution is True


def test_invalid_policies_fail_closed() -> None:
    with pytest.raises(ValueError):
        TimeoutPolicy(timeout_ms=0)
    with pytest.raises(ValueError):
        BoundedRetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        ExponentialBackoffPolicy(initial_delay_ms=100, max_delay_ms=10)


def test_reliability_module_has_no_network_clients() -> None:
    source = RELIABILITY.read_text(encoding="utf-8")
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "urllib.request" not in source
    assert "aiohttp" not in source
