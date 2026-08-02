#!/usr/bin/env python3
"""Strict ALB target-health evaluation for staging deploy (Sprint 25b.4a / 25b.5h).

Accepts only when the expected staging EC2 instance is the sole target and its
TargetHealth.State is exactly ``healthy``. Rejects mixed, unexpected, empty,
malformed, and non-staging/production target-group identities.

Exit codes for the host verifier:
  0 — expected target healthy
  2 — explicitly allowlisted transient stabilization state (retry in-window)
  1 — permanent, malformed, unknown, unauthorized, or invalid (fail closed)

Transient classification is an explicit allowlist. Unknown states, unknown
reasons, malformed payloads, and identity mismatches are never retried.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TG_ARN_RE = re.compile(r"^arn:aws:elasticloadbalancing:[a-z0-9-]+:[0-9]{12}:targetgroup/.+")
INSTANCE_ID_RE = re.compile(r"^i-[0-9a-f]{8,}$")

EXIT_OK = 0
EXIT_PERMANENT = 1
EXIT_TRANSIENT = 2

# Staging API container listens on 8000; target registration must match.
EXPECTED_TARGET_PORT = 8000

# Explicit (state, reason) allowlist for exit 2. reason=None means AWS omitted Reason.
# Only combinations reviewed for single-instance staging stabilization belong here.
# draining / unavailable / unknown states are intentionally absent (fail closed).
TRANSIENT_ALLOWLIST: frozenset[tuple[str, str | None]] = frozenset(
    {
        # Initial registration window (reason may be omitted by AWS).
        ("initial", None),
        ("initial", "Elb.RegistrationInProgress"),
        ("initial", "Elb.InitialHealthChecking"),
        # Unhealthy only with recognized startup / first-health-check reasons.
        ("unhealthy", "Elb.RegistrationInProgress"),
        ("unhealthy", "Elb.InitialHealthChecking"),
        ("unhealthy", "Target.FailedHealthChecks"),
        ("unhealthy", "Target.Timeout"),
        ("unhealthy", "Target.ResponseCodeMismatch"),
    }
)


class AlbTargetHealthError(ValueError):
    """Raised when staging ALB target health is not strictly acceptable."""

    retryable: bool = False


class TransientAlbTargetHealthError(AlbTargetHealthError):
    """Retryable within the bounded ALB stabilization window."""

    retryable = True


class PermanentAlbTargetHealthError(AlbTargetHealthError):
    """Configuration / identity / malformed rejection — fail closed immediately."""

    retryable = False


def validate_target_group_arn(target_group_arn: str) -> None:
    if not target_group_arn or not str(target_group_arn).strip():
        raise PermanentAlbTargetHealthError("target group ARN is empty")
    arn = str(target_group_arn).strip()
    if arn in ("null", "None"):
        raise PermanentAlbTargetHealthError("target group ARN is empty")
    if not TG_ARN_RE.fullmatch(arn):
        raise PermanentAlbTargetHealthError("target group ARN is malformed")
    lowered = arn.lower()
    if "production" in lowered:
        raise PermanentAlbTargetHealthError("production target group ARN rejected")
    if "staging" not in lowered and "dealbrain-staging" not in lowered:
        raise PermanentAlbTargetHealthError("target group ARN must identify staging")


def validate_instance_id(instance_id: str) -> None:
    if not instance_id or not INSTANCE_ID_RE.fullmatch(instance_id.strip()):
        raise PermanentAlbTargetHealthError("expected instance id is missing or malformed")


def is_allowlisted_transient(state: str, reason: str | None) -> bool:
    """Return True only for explicitly reviewed (state, reason) pairs."""
    return (state, reason) in TRANSIENT_ALLOWLIST


def _normalize_reason(reason: Any) -> str | None:
    if reason is None:
        return None
    if not isinstance(reason, str):
        raise PermanentAlbTargetHealthError("malformed TargetHealth.Reason")
    stripped = reason.strip()
    return stripped if stripped else None


def _classify_state(state: Any, reason: Any) -> None:
    """Raise transient/permanent based on allowlisted state/reason pairs."""
    if state is None:
        raise PermanentAlbTargetHealthError("TargetHealth.State is null/missing")
    if not isinstance(state, str):
        raise PermanentAlbTargetHealthError("TargetHealth.State is invalid")
    if not state.strip():
        raise PermanentAlbTargetHealthError("TargetHealth.State is empty")

    normalized_reason = _normalize_reason(reason)
    reason_suffix = f" reason={normalized_reason!r}" if normalized_reason else ""

    if state == "healthy":
        return

    if is_allowlisted_transient(state, normalized_reason):
        raise TransientAlbTargetHealthError(
            f"expected target state is {state!r}, want exactly 'healthy'{reason_suffix}"
        )

    # Known AWS states that are not allowlisted for retry, and any unknown state.
    raise PermanentAlbTargetHealthError(
        f"expected target state is {state!r}, want exactly 'healthy'{reason_suffix}"
    )


def evaluate_target_health(
    payload: Any,
    *,
    expected_instance_id: str,
    target_group_arn: str,
    expected_port: int = EXPECTED_TARGET_PORT,
) -> None:
    """Fail closed unless the expected instance is the only target and healthy."""
    validate_target_group_arn(target_group_arn)
    validate_instance_id(expected_instance_id)
    expected = expected_instance_id.strip()

    if not isinstance(payload, dict):
        raise PermanentAlbTargetHealthError("malformed describe-target-health payload")
    if "TargetHealthDescriptions" not in payload:
        raise PermanentAlbTargetHealthError("missing TargetHealthDescriptions")
    descriptions = payload.get("TargetHealthDescriptions")

    if not isinstance(descriptions, list):
        raise PermanentAlbTargetHealthError("malformed TargetHealthDescriptions")
    if len(descriptions) == 0:
        # Initial registration window: no description yet may clear in-window.
        raise TransientAlbTargetHealthError("expected target absent")
    if len(descriptions) != 1:
        # Single-instance staging: unexpected count is permanent (no multi-target churn).
        raise PermanentAlbTargetHealthError(
            f"unexpected target count: {len(descriptions)} (want exactly 1)"
        )

    desc = descriptions[0]
    if not isinstance(desc, dict):
        raise PermanentAlbTargetHealthError("malformed target health description")

    target = desc.get("Target")
    if target is None:
        raise PermanentAlbTargetHealthError("missing Target")
    if not isinstance(target, dict):
        raise PermanentAlbTargetHealthError("malformed target identity")

    target_id = target.get("Id")
    if target_id is None or target_id == "":
        raise PermanentAlbTargetHealthError("missing target Id")
    if not isinstance(target_id, str):
        raise PermanentAlbTargetHealthError("malformed target Id")
    if target_id != expected:
        raise PermanentAlbTargetHealthError(
            f"unexpected target id: {target_id!r} (want {expected})"
        )

    if "Port" not in target:
        raise PermanentAlbTargetHealthError("missing target Port")
    port = target.get("Port")
    if not isinstance(port, int) or isinstance(port, bool):
        raise PermanentAlbTargetHealthError("malformed target Port")
    if port != expected_port:
        raise PermanentAlbTargetHealthError(
            f"unexpected target port: {port!r} (want {expected_port})"
        )

    health = desc.get("TargetHealth")
    if health is None:
        raise PermanentAlbTargetHealthError("missing TargetHealth")
    if not isinstance(health, dict):
        raise PermanentAlbTargetHealthError("malformed TargetHealth")

    _classify_state(health.get("State"), health.get("Reason"))


def evaluate_target_health_json(
    text: str,
    *,
    expected_instance_id: str,
    target_group_arn: str,
    expected_port: int = EXPECTED_TARGET_PORT,
) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PermanentAlbTargetHealthError(f"malformed JSON: {exc}") from exc
    evaluate_target_health(
        payload,
        expected_instance_id=expected_instance_id,
        target_group_arn=target_group_arn,
        expected_port=expected_port,
    )


def classify_alb_rejection(exc: BaseException) -> int:
    """Map an evaluation error to a host verifier exit code."""
    if isinstance(exc, TransientAlbTargetHealthError):
        return EXIT_TRANSIENT
    if isinstance(exc, PermanentAlbTargetHealthError):
        return EXIT_PERMANENT
    if isinstance(exc, AlbTargetHealthError):
        return EXIT_PERMANENT if not getattr(exc, "retryable", False) else EXIT_TRANSIENT
    return EXIT_PERMANENT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-group-arn", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument(
        "--input",
        default="-",
        help="Path to describe-target-health JSON, or '-' for stdin",
    )
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            text = sys.stdin.read()
        else:
            text = Path(args.input).read_text(encoding="utf-8")
        evaluate_target_health_json(
            text,
            expected_instance_id=args.instance_id,
            target_group_arn=args.target_group_arn,
        )
    except AlbTargetHealthError as exc:
        # Redacted: no raw AWS dumps beyond the short reason.
        kind = "transient" if getattr(exc, "retryable", False) else "permanent"
        print(f"ERROR: ALB target health rejected ({kind}: {exc})", file=sys.stderr)
        return classify_alb_rejection(exc)
    print("ok: expected staging target healthy")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
