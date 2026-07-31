#!/usr/bin/env python3
"""Strict ALB target-health evaluation for staging deploy (Sprint 25b.4a).

Accepts only when the expected staging EC2 instance is the sole target and its
TargetHealth.State is exactly ``healthy``. Rejects mixed, unexpected, empty,
malformed, and non-staging/production target-group identities.
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


class AlbTargetHealthError(ValueError):
    """Raised when staging ALB target health is not strictly acceptable."""


def validate_target_group_arn(target_group_arn: str) -> None:
    if not target_group_arn or not str(target_group_arn).strip():
        raise AlbTargetHealthError("target group ARN is empty")
    arn = str(target_group_arn).strip()
    if arn in ("null", "None"):
        raise AlbTargetHealthError("target group ARN is empty")
    if not TG_ARN_RE.fullmatch(arn):
        raise AlbTargetHealthError("target group ARN is malformed")
    lowered = arn.lower()
    if "production" in lowered:
        raise AlbTargetHealthError("production target group ARN rejected")
    if "staging" not in lowered and "dealbrain-staging" not in lowered:
        raise AlbTargetHealthError("target group ARN must identify staging")


def validate_instance_id(instance_id: str) -> None:
    if not instance_id or not INSTANCE_ID_RE.fullmatch(instance_id.strip()):
        raise AlbTargetHealthError("expected instance id is missing or malformed")


def evaluate_target_health(
    payload: Any,
    *,
    expected_instance_id: str,
    target_group_arn: str,
) -> None:
    """Fail closed unless the expected instance is the only target and healthy."""
    validate_target_group_arn(target_group_arn)
    validate_instance_id(expected_instance_id)
    expected = expected_instance_id.strip()

    if isinstance(payload, list):
        descriptions = payload
    elif isinstance(payload, dict):
        if "TargetHealthDescriptions" not in payload:
            raise AlbTargetHealthError("malformed describe-target-health payload")
        descriptions = payload.get("TargetHealthDescriptions")
    else:
        raise AlbTargetHealthError("malformed describe-target-health payload")

    if not isinstance(descriptions, list):
        raise AlbTargetHealthError("malformed TargetHealthDescriptions")
    if len(descriptions) == 0:
        raise AlbTargetHealthError("expected target absent")
    if len(descriptions) != 1:
        raise AlbTargetHealthError(f"unexpected target count: {len(descriptions)} (want exactly 1)")

    desc = descriptions[0]
    if not isinstance(desc, dict):
        raise AlbTargetHealthError("malformed target health description")

    target = desc.get("Target")
    if not isinstance(target, dict):
        raise AlbTargetHealthError("malformed target identity")
    target_id = target.get("Id")
    if target_id != expected:
        raise AlbTargetHealthError(f"unexpected target id: {target_id!r} (want {expected})")

    health = desc.get("TargetHealth")
    if not isinstance(health, dict):
        raise AlbTargetHealthError("malformed TargetHealth")
    state = health.get("State")
    if state != "healthy":
        raise AlbTargetHealthError(f"expected target state is {state!r}, want exactly 'healthy'")


def evaluate_target_health_json(
    text: str,
    *,
    expected_instance_id: str,
    target_group_arn: str,
) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AlbTargetHealthError(f"malformed JSON: {exc}") from exc
    evaluate_target_health(
        payload,
        expected_instance_id=expected_instance_id,
        target_group_arn=target_group_arn,
    )


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
        print(f"ERROR: ALB target health rejected ({exc})", file=sys.stderr)
        return 1
    print("ok: expected staging target healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
