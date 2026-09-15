"""Production ALB evaluator must accept the production target-group ARN.

Regresses the predeploy audit of PR #140: verify-production.sh invoked the
shared alb_target_health.py evaluator, whose default staging identity check
permanently rejects any ARN containing ``production``.

Terraform names the production TG ``dealbrain-production-api``, so the live
ARN always contains that token. Without ``--environment production``, ALB
verification would fail closed after /live and /ready succeeded.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.deploy.alb_target_health import (
    EXIT_OK,
    EXIT_PERMANENT,
    PermanentAlbTargetHealthError,
    evaluate_target_health,
)
from scripts.deploy.alb_target_health import main as alb_main

ROOT = Path(__file__).resolve().parents[2]
VERIFY_PROD = ROOT / "scripts/deploy/host/verify-production.sh"
VERIFY_STAGING = ROOT / "scripts/deploy/host/verify-staging.sh"

PROD_TG = (
    "arn:aws:elasticloadbalancing:us-east-1:123456789012:"
    "targetgroup/dealbrain-production-api/abcdef0123456789"
)
STAGING_TG = (
    "arn:aws:elasticloadbalancing:us-east-1:123456789012:"
    "targetgroup/dealbrain-staging-api/abcdef0123456789"
)
INSTANCE = "i-0e49ddadd4ecc772d"


def _healthy_payload() -> dict:
    return {
        "TargetHealthDescriptions": [
            {
                "Target": {"Id": INSTANCE, "Port": 8000},
                "TargetHealth": {"State": "healthy"},
            }
        ]
    }


def test_default_evaluator_still_rejects_production_arn() -> None:
    with pytest.raises(PermanentAlbTargetHealthError, match="production"):
        evaluate_target_health(
            _healthy_payload(),
            expected_instance_id=INSTANCE,
            target_group_arn=PROD_TG,
        )


def test_production_environment_accepts_production_arn() -> None:
    evaluate_target_health(
        _healthy_payload(),
        expected_instance_id=INSTANCE,
        target_group_arn=PROD_TG,
        environment="production",
    )


def test_production_environment_rejects_staging_arn() -> None:
    with pytest.raises(PermanentAlbTargetHealthError, match="staging"):
        evaluate_target_health(
            _healthy_payload(),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
            environment="production",
        )


def test_production_cli_accepts_production_target_group(tmp_path: Path) -> None:
    path = tmp_path / "healthy.json"
    path.write_text(json.dumps(_healthy_payload()), encoding="utf-8")
    rc = alb_main(
        [
            "--target-group-arn",
            PROD_TG,
            "--instance-id",
            INSTANCE,
            "--environment",
            "production",
            "--input",
            str(path),
        ]
    )
    assert rc == EXIT_OK


def test_production_cli_rejects_staging_target_group(tmp_path: Path) -> None:
    path = tmp_path / "healthy.json"
    path.write_text(json.dumps(_healthy_payload()), encoding="utf-8")
    rc = alb_main(
        [
            "--target-group-arn",
            STAGING_TG,
            "--instance-id",
            INSTANCE,
            "--environment",
            "production",
            "--input",
            str(path),
        ]
    )
    assert rc == EXIT_PERMANENT


def test_verify_production_passes_environment_production() -> None:
    text = VERIFY_PROD.read_text(encoding="utf-8")
    assert "alb_target_health.py" in text
    assert "--environment production" in text
    assert "--environment staging" not in text


def test_verify_staging_does_not_switch_to_production() -> None:
    text = VERIFY_STAGING.read_text(encoding="utf-8")
    assert "alb_target_health.py" in text
    assert "--environment production" not in text
