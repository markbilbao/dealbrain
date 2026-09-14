"""Production Compose CloudWatch awslogs contract (Docker-native options only).

Regresses Deploy Production run 34909112181 / SSM command
302fc54a-9541-4c74-bab5-498cd81894a2:

  Error response from daemon:
  unknown log opt 'awslogs-stream-prefix' for awslogs log driver

``awslogs-stream-prefix`` is an ECS task-definition option. Docker's native
awslogs driver rejects it while creating the one-off migration container.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE_COMPOSE = ROOT / "infra/compose/docker-compose.base.yml"
PROD_COMPOSE = ROOT / "infra/compose/docker-compose.production.yml"
STAGING_COMPOSE = ROOT / "infra/compose/docker-compose.staging.yml"
HOST_DEPLOY = ROOT / "scripts/deploy/host/dealbrain-production-deploy.sh"

# Docker-native awslogs options documented at:
# https://docs.docker.com/engine/logging/drivers/awslogs/
DOCKER_AWSLOGS_ALLOWED_OPTIONS: frozenset[str] = frozenset(
    {
        "awslogs-region",
        "awslogs-endpoint",
        "awslogs-group",
        "awslogs-stream",
        "awslogs-create-group",
        "awslogs-create-stream",
        "awslogs-datetime-format",
        "awslogs-multiline-pattern",
        "awslogs-force-flush-interval-seconds",
        "awslogs-max-buffered-events",
        "tag",
    }
)

# ECS-only / non-Docker options that must never appear in Compose.
DOCKER_AWSLOGS_FORBIDDEN_OPTIONS: frozenset[str] = frozenset(
    {
        "awslogs-stream-prefix",
    }
)

REQUIRED_AWSLOGS_OPTIONS: frozenset[str] = frozenset(
    {
        "awslogs-region",
        "awslogs-group",
        "awslogs-create-group",
        "tag",
    }
)

COMPOSE_CONFIG_ENV: dict[str, str] = {
    "DEALBRAIN_IMAGE": (
        "ghcr.io/example-org/dealbrain@sha256:"
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ),
    "DATABASE_URL": "postgresql+asyncpg://ci:CiStrongPass12@db.example:5432/dealbrain",
    "CORS_ORIGINS": "https://example.com",
    "APP_ENV": "production",
    "AWS_REGION": "us-east-1",
}

_HAS_DOCKER_COMPOSE = shutil.which("docker") is not None


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _overlay_logging(service: str) -> dict[str, Any]:
    overlay = _load_yaml(PROD_COMPOSE)
    logging_cfg = overlay["services"][service]["logging"]
    assert isinstance(logging_cfg, dict)
    return logging_cfg


def _assert_valid_awslogs(logging_cfg: dict[str, Any], *, service: str) -> None:
    assert logging_cfg.get("driver") == "awslogs", f"{service} must use awslogs"
    options = logging_cfg.get("options")
    assert isinstance(options, dict), f"{service} awslogs options missing"
    keys = set(options)
    assert "awslogs-stream-prefix" not in keys, f"{service} uses ECS-only awslogs-stream-prefix"
    forbidden = keys & DOCKER_AWSLOGS_FORBIDDEN_OPTIONS
    assert not forbidden, f"{service} has unsupported awslogs options: {sorted(forbidden)}"
    unknown = keys - DOCKER_AWSLOGS_ALLOWED_OPTIONS
    assert not unknown, f"{service} has non-Docker awslogs options: {sorted(unknown)}"
    missing = REQUIRED_AWSLOGS_OPTIONS - keys
    assert not missing, f"{service} missing required awslogs options: {sorted(missing)}"
    assert options["awslogs-create-group"] in {False, "false"}
    group = str(options["awslogs-group"])
    assert group == f"/dealbrain/production/{service}"
    assert "awslogs-stream" not in keys, (
        f"{service} sets a static awslogs-stream; concurrent containers would share it"
    )
    tag = str(options["tag"])
    assert "{{.Name}}" in tag, f"{service} tag must use the Docker container-name template"
    assert "{{.ImageName}}" not in tag, "ImageName tags can include ':' which CloudWatch rejects"


def _compose_config(*, profile: str | None = None) -> dict[str, Any]:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(BASE_COMPOSE),
        "-f",
        str(PROD_COMPOSE),
    ]
    if profile:
        cmd.extend(["--profile", profile])
    cmd.append("config")
    env = os.environ.copy()
    env.update(COMPOSE_CONFIG_ENV)
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
    )
    assert result.returncode == 0, (
        f"docker compose config failed:\n{result.stdout}\n{result.stderr}"
    )
    payload = yaml.safe_load(result.stdout)
    assert isinstance(payload, dict)
    return payload


def test_production_overlay_has_no_awslogs_stream_prefix() -> None:
    overlay = _load_yaml(PROD_COMPOSE)
    for service in ("api", "migrate"):
        options = overlay["services"][service]["logging"]["options"]
        assert "awslogs-stream-prefix" not in options
    text = PROD_COMPOSE.read_text(encoding="utf-8")
    assert re.search(r"(?m)^\s*awslogs-stream-prefix\s*:", text) is None


def test_production_api_awslogs_is_docker_native() -> None:
    _assert_valid_awslogs(_overlay_logging("api"), service="api")


def test_production_migrate_awslogs_is_docker_native() -> None:
    _assert_valid_awslogs(_overlay_logging("migrate"), service="migrate")


def test_production_cloudwatch_logging_remains_enabled() -> None:
    overlay = _load_yaml(PROD_COMPOSE)
    for service in ("api", "migrate"):
        logging_cfg = overlay["services"][service]["logging"]
        assert logging_cfg["driver"] == "awslogs"
        assert logging_cfg["options"]["awslogs-group"] == f"/dealbrain/production/{service}"
        assert logging_cfg["options"]["awslogs-region"]
    staging = STAGING_COMPOSE.read_text(encoding="utf-8")
    assert "awslogs" not in staging


def test_stream_naming_is_unique_per_container() -> None:
    api = _overlay_logging("api")["options"]
    migrate = _overlay_logging("migrate")["options"]
    assert api["awslogs-group"] != migrate["awslogs-group"]
    assert api["tag"] == "{{.Name}}"
    assert migrate["tag"] == "{{.Name}}"
    # Static stream names are unsafe for compose run --rm one-offs that can
    # overlap with a previous container or a scaled replica.
    assert "awslogs-stream" not in api
    assert "awslogs-stream" not in migrate


def test_awslogs_option_contract_rejects_ecs_only_keys() -> None:
    assert "awslogs-stream-prefix" in DOCKER_AWSLOGS_FORBIDDEN_OPTIONS
    assert "awslogs-stream-prefix" not in DOCKER_AWSLOGS_ALLOWED_OPTIONS
    assert "tag" in DOCKER_AWSLOGS_ALLOWED_OPTIONS
    overlay = _load_yaml(PROD_COMPOSE)
    used: set[str] = set()
    for service in overlay["services"].values():
        options = service.get("logging", {}).get("options", {})
        used.update(options)
    assert used <= DOCKER_AWSLOGS_ALLOWED_OPTIONS
    assert not (used & DOCKER_AWSLOGS_FORBIDDEN_OPTIONS)


def test_deploy_script_does_not_override_compose_logging() -> None:
    text = HOST_DEPLOY.read_text(encoding="utf-8")
    assert "awslogs-stream-prefix" not in text
    assert "--log-opt" not in text
    assert "--log-driver" not in text
    assert "logging:" not in text


def test_base_compose_does_not_introduce_awslogs() -> None:
    base = _load_yaml(BASE_COMPOSE)
    for name, service in base["services"].items():
        assert "logging" not in service, f"base {name} unexpectedly sets logging"


@pytest.mark.skipif(not _HAS_DOCKER_COMPOSE, reason="docker compose is not installed")
def test_docker_compose_config_succeeds_for_production() -> None:
    resolved = _compose_config()
    services = resolved["services"]
    assert "api" in services
    _assert_valid_awslogs(services["api"]["logging"], service="api")


@pytest.mark.skipif(not _HAS_DOCKER_COMPOSE, reason="docker compose is not installed")
def test_resolved_migrate_profile_has_valid_awslogs() -> None:
    resolved = _compose_config(profile="migrate")
    services = resolved["services"]
    assert "migrate" in services
    _assert_valid_awslogs(services["migrate"]["logging"], service="migrate")
    _assert_valid_awslogs(services["api"]["logging"], service="api")
    rendered = yaml.safe_dump(resolved)
    assert "awslogs-stream-prefix" not in rendered


@pytest.mark.skipif(not _HAS_DOCKER_COMPOSE, reason="docker compose is not installed")
def test_daemon_rejects_awslogs_stream_prefix_but_accepts_tag() -> None:
    """Prove the live failure mode and that our replacement is daemon-valid.

    Option validation happens at container create, before AWS is contacted.
    """
    bad = subprocess.run(
        [
            "docker",
            "create",
            "--name",
            "dealbrain-awslogs-prefix-probe",
            "--log-driver",
            "awslogs",
            "--log-opt",
            "awslogs-region=us-east-1",
            "--log-opt",
            "awslogs-group=/dealbrain/production/migrate",
            "--log-opt",
            "awslogs-stream-prefix=migrate",
            "alpine:3.20",
            "true",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["docker", "rm", "-f", "dealbrain-awslogs-prefix-probe"],
        check=False,
        capture_output=True,
        text=True,
    )
    combined = f"{bad.stdout}\n{bad.stderr}"
    assert bad.returncode != 0
    assert re.search(r"unknown log opt ['\"]awslogs-stream-prefix['\"]", combined)

    good = subprocess.run(
        [
            "docker",
            "create",
            "--name",
            "dealbrain-awslogs-tag-probe",
            "--log-driver",
            "awslogs",
            "--log-opt",
            "awslogs-region=us-east-1",
            "--log-opt",
            "awslogs-group=/dealbrain/production/migrate",
            "--log-opt",
            "awslogs-create-group=false",
            "--log-opt",
            "tag={{.Name}}",
            "alpine:3.20",
            "true",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["docker", "rm", "-f", "dealbrain-awslogs-tag-probe"],
        check=False,
        capture_output=True,
        text=True,
    )
    combined_good = f"{good.stdout}\n{good.stderr}"
    assert "unknown log opt" not in combined_good
    assert "awslogs-stream-prefix" not in combined_good
