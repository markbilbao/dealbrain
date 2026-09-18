"""Deploy Staging must select canonical RDS ``dealbrain-staging-postgres`` only.

Broad ``contains(DBInstanceIdentifier, …)`` discovery and ``[0]`` selection
from a list of matching staging databases are unsafe while a recovery copy
(``dealbrain-staging-postgres-recovery``) exists. Fail closed unless the
canonical instance is available, private, named ``dealbrain``, listening on
5432, and has an active master-user secret.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.deploy.select_canonical_staging_rds import (
    CANONICAL_STAGING_DB_INSTANCE_IDENTIFIER,
    EXPECTED_DB_INSTANCE_STATUS,
    EXPECTED_DB_NAME,
    EXPECTED_ENDPOINT_PORT,
    EXPECTED_MASTER_USER_SECRET_STATUS,
    RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER,
    CanonicalStagingRdsError,
    select_canonical_staging_rds,
)
from scripts.deploy.select_canonical_staging_rds import (
    main as select_main,
)

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
PRODUCTION_WF = WORKFLOWS / "deploy-production.yml"
ROLLBACK_WF = WORKFLOWS / "rollback.yml"
SELECTOR = ROOT / "scripts/deploy/select_canonical_staging_rds.py"

CANONICAL_ENDPOINT = "dealbrain-staging-postgres.c4fm2y4uucmx.example.rds.amazonaws.com"
CANONICAL_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds!db-canonical-AbCd"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _targets_step(text: str) -> str:
    marker = "Resolve staging targets from AWS"
    assert marker in text
    after = text.split(marker, 1)[1]
    next_step = re.search(r"\n      - name:", after)
    assert next_step is not None
    return after[: next_step.start()]


def _canonical_instance(**overrides: object) -> dict:
    instance: dict = {
        "DBInstanceIdentifier": CANONICAL_STAGING_DB_INSTANCE_IDENTIFIER,
        "DBInstanceStatus": EXPECTED_DB_INSTANCE_STATUS,
        "DBName": EXPECTED_DB_NAME,
        "PubliclyAccessible": False,
        "Endpoint": {
            "Address": CANONICAL_ENDPOINT,
            "Port": EXPECTED_ENDPOINT_PORT,
        },
        "MasterUserSecret": {
            "SecretArn": CANONICAL_SECRET_ARN,
            "SecretStatus": EXPECTED_MASTER_USER_SECRET_STATUS,
        },
    }
    for key, value in overrides.items():
        if key in {"Endpoint", "MasterUserSecret"} and isinstance(value, dict):
            merged = copy.deepcopy(instance[key])
            merged.update(value)
            instance[key] = merged
        else:
            instance[key] = value
    return instance


def _describe(*instances: dict) -> dict:
    return {"DBInstances": list(instances)}


def _nonsecret(payload: dict | None = None) -> dict:
    if payload is None:
        payload = _describe(_canonical_instance())
    return select_canonical_staging_rds(payload)


# ---------------------------------------------------------------------------
# 1. Exact identifier CLI
# ---------------------------------------------------------------------------


def test_deploy_staging_uses_exact_canonical_db_instance_identifier() -> None:
    step = _targets_step(_read(DEPLOY_WF))
    assert "--db-instance-identifier dealbrain-staging-postgres" in step
    assert "aws rds describe-db-instances" in step
    assert step.count("aws rds describe-db-instances") == 1
    assert step.count("--db-instance-identifier dealbrain-staging-postgres") == 1
    assert "python -m scripts.deploy.select_canonical_staging_rds" in step
    assert "--out .deploy-work/rds-nonsecret.json" in step
    assert "--input .deploy-work/rds-describe.json" in step
    rds_cli = step.split("aws rds describe-db-instances", 1)[1].split(
        "python -m scripts.deploy.select_canonical_staging_rds", 1
    )[0]
    assert "--query" not in rds_cli
    assert "contains(" not in rds_cli


# ---------------------------------------------------------------------------
# 2. No broad contains() staging query
# ---------------------------------------------------------------------------


def test_no_contains_dbinstanceidentifier_broad_staging_query() -> None:
    text = _read(DEPLOY_WF)
    step = _targets_step(text)
    assert "contains(DBInstanceIdentifier" not in text
    assert "contains(DBInstanceIdentifier, 'dealbrain-staging')" not in step
    assert "contains(DBInstanceIdentifier, 'staging')" not in step
    assert "contains(DBInstanceIdentifier" not in step
    selector = _read(SELECTOR)
    assert "contains(DBInstanceIdentifier" not in selector
    assert "contains(DBInstanceIdentifier, 'staging')" not in selector


# ---------------------------------------------------------------------------
# 3. No [0] selection from a matching staging DB list
# ---------------------------------------------------------------------------


def _active_lines(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")
    )


def test_no_first_match_selection_from_staging_db_list() -> None:
    step = _active_lines(_targets_step(_read(DEPLOY_WF)))
    assert "| [0]" not in step
    assert "|[0]" not in step
    assert "DBInstances[0]" not in step
    assert "[0]" not in step
    selector = _read(SELECTOR)
    assert "| [0]" not in selector
    assert "DBInstances[0]" not in selector
    assert "[0]" not in selector


def test_multiple_staging_instances_fail_closed_no_first_match() -> None:
    recovery = _canonical_instance(
        DBInstanceIdentifier=RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER,
    )
    with pytest.raises(CanonicalStagingRdsError, match="exactly one DB instance"):
        select_canonical_staging_rds(_describe(_canonical_instance(), recovery))


# ---------------------------------------------------------------------------
# 4. Recovery DB is never a deployment target
# ---------------------------------------------------------------------------


def test_recovery_db_name_never_used_as_deployment_target() -> None:
    text = _read(DEPLOY_WF)
    assert f"--db-instance-identifier {RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER}" not in text
    assert f"--db-instance-identifier {CANONICAL_STAGING_DB_INSTANCE_IDENTIFIER}" in text
    for line in text.splitlines():
        if RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER not in line:
            continue
        stripped = line.strip()
        assert stripped.startswith("#"), line
        assert "not a deploy target" in stripped
    with pytest.raises(CanonicalStagingRdsError, match="recovery copy"):
        select_canonical_staging_rds(
            _describe(
                _canonical_instance(
                    DBInstanceIdentifier=RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER,
                )
            )
        )


def test_selector_does_not_fall_back_to_recovery_or_other_names() -> None:
    for ident in (
        "dealbrain-staging",
        "dealbrain-staging-postgres-old",
        "staging",
        "dealbrain-production-postgres",
    ):
        with pytest.raises(CanonicalStagingRdsError, match="DBInstanceIdentifier"):
            select_canonical_staging_rds(_describe(_canonical_instance(DBInstanceIdentifier=ident)))


# ---------------------------------------------------------------------------
# 5–10. Fail-closed canonical validations
# ---------------------------------------------------------------------------


def test_canonical_instance_must_be_available() -> None:
    for status in ("creating", "backing-up", "modifying", "failed", "stopped", ""):
        with pytest.raises(CanonicalStagingRdsError, match="DBInstanceStatus"):
            select_canonical_staging_rds(_describe(_canonical_instance(DBInstanceStatus=status)))
    assert _nonsecret()["endpoint"] == CANONICAL_ENDPOINT


def test_canonical_master_user_secret_status_must_be_active() -> None:
    for status in ("creating", "rotating", "inaccessible-encryption-credentials", ""):
        with pytest.raises(CanonicalStagingRdsError, match="MasterUserSecret.SecretStatus"):
            select_canonical_staging_rds(
                _describe(_canonical_instance(MasterUserSecret={"SecretStatus": status}))
            )
    with pytest.raises(CanonicalStagingRdsError, match="MasterUserSecret.SecretArn"):
        select_canonical_staging_rds(
            _describe(_canonical_instance(MasterUserSecret={"SecretArn": ""}))
        )
    with pytest.raises(CanonicalStagingRdsError, match="MasterUserSecret.SecretArn"):
        select_canonical_staging_rds(
            _describe(_canonical_instance(MasterUserSecret={"SecretArn": "   "}))
        )
    with pytest.raises(CanonicalStagingRdsError, match="MasterUserSecret"):
        select_canonical_staging_rds(_describe(_canonical_instance(MasterUserSecret=None)))


def test_endpoint_must_be_non_empty() -> None:
    for address in ("", "   ", None):
        with pytest.raises(CanonicalStagingRdsError, match="Endpoint.Address"):
            select_canonical_staging_rds(
                _describe(_canonical_instance(Endpoint={"Address": address}))
            )
    with pytest.raises(CanonicalStagingRdsError, match="Endpoint"):
        select_canonical_staging_rds(_describe(_canonical_instance(Endpoint=None)))
    with pytest.raises(CanonicalStagingRdsError, match="Endpoint"):
        select_canonical_staging_rds(_describe(_canonical_instance(Endpoint="missing")))


def test_port_must_equal_5432() -> None:
    for port in (5433, 0, 80, "5432", 5432.0, True, None):
        with pytest.raises(CanonicalStagingRdsError, match="Endpoint.Port"):
            select_canonical_staging_rds(_describe(_canonical_instance(Endpoint={"Port": port})))
    assert _nonsecret()["port"] == 5432


def test_dbname_must_equal_dealbrain() -> None:
    for name in ("postgres", "dealbrain_staging", "rdsadmin", "", None):
        with pytest.raises(CanonicalStagingRdsError, match="DBName"):
            select_canonical_staging_rds(_describe(_canonical_instance(DBName=name)))
    assert _nonsecret()["db_name"] == "dealbrain"


def test_publicly_accessible_must_be_false() -> None:
    for value in (True, None, "false", 0, "False"):
        with pytest.raises(CanonicalStagingRdsError, match="PubliclyAccessible"):
            select_canonical_staging_rds(_describe(_canonical_instance(PubliclyAccessible=value)))
    healthy = _nonsecret()
    assert set(healthy) == {
        "endpoint",
        "port",
        "db_name",
        "master_user_secret_arn",
    }
    assert healthy["master_user_secret_arn"] == CANONICAL_SECRET_ARN
    assert "password" not in json.dumps(healthy).lower()
    assert "secretstring" not in json.dumps(healthy).lower()


def test_empty_or_missing_payload_fails_closed() -> None:
    with pytest.raises(CanonicalStagingRdsError, match="malformed"):
        select_canonical_staging_rds([])
    with pytest.raises(CanonicalStagingRdsError, match="DBInstances"):
        select_canonical_staging_rds({})
    with pytest.raises(CanonicalStagingRdsError, match="exactly one"):
        select_canonical_staging_rds(_describe())


def test_cli_writes_rds_nonsecret_and_rejects_recovery(tmp_path: Path) -> None:
    describe_path = tmp_path / "rds-describe.json"
    out_path = tmp_path / "rds-nonsecret.json"
    describe_path.write_text(json.dumps(_describe(_canonical_instance())), encoding="utf-8")
    assert select_main(["--input", str(describe_path), "--out", str(out_path)]) == 0
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written == {
        "db_name": "dealbrain",
        "endpoint": CANONICAL_ENDPOINT,
        "master_user_secret_arn": CANONICAL_SECRET_ARN,
        "port": 5432,
    }

    describe_path.write_text(
        json.dumps(
            _describe(
                _canonical_instance(
                    DBInstanceIdentifier=RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER,
                )
            )
        ),
        encoding="utf-8",
    )
    out_bad = tmp_path / "rds-nonsecret-bad.json"
    assert select_main(["--input", str(describe_path), "--out", str(out_bad)]) == 1
    assert not out_bad.exists()


def test_module_invocation_from_repository_root(tmp_path: Path) -> None:
    describe_path = tmp_path / "rds-describe.json"
    out_path = tmp_path / "rds-nonsecret.json"
    describe_path.write_text(json.dumps(_describe(_canonical_instance())), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.deploy.select_canonical_staging_rds",
            "--input",
            str(describe_path),
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "dealbrain-staging-postgres" in proc.stdout
    assert json.loads(out_path.read_text(encoding="utf-8"))["port"] == 5432


# ---------------------------------------------------------------------------
# 11. Production-negative safeguards remain
# ---------------------------------------------------------------------------


def test_production_negative_safeguards_remain() -> None:
    text = _read(DEPLOY_WF)
    assert re.search(r"(?m)^\s+environment:\s+staging\s*$", text)
    assert "environment: production" not in text
    assert "grep -q 'dealbrain-staging-gha-deploy'" in text
    assert "grep -qv 'dealbrain-production-gha-deploy'" in text
    assert "grep -qv 'production'" in text
    step = _targets_step(text)
    assert 'test "$COUNT" = "1"' in step
    assert "Name=tag:Environment,Values=staging" in step
    assert "Name=tag:Role,Values=api-compose-host" in step
    assert 'echo "$INSTANCE_ID" | grep -qv production' in step
    assert 'echo "$TG_ARN" | grep -qv production' in step
    assert 'echo "$TG_ARN" | grep -q staging' in step
    assert "DealBrain-StagingDeploy" in text
    assert "--document-name AWS-RunShellScript" not in text
    assert "python -m scripts.deploy.validate_staging_release" in text
    assert "imagetools inspect" in text
    assert "authoritative host evidence missing" in text
    assert "Refusing to fabricate staging_ok" in text
    assert "group: staging-release-mutation" in text
    assert "cancel-in-progress: false" in text
    assert "role-to-assume: ${{ vars.AWS_ROLE_ARN }}" in text
    assert "allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}" in text
    assert "terraform apply" not in text
    assert "AWS_ACCESS_KEY_ID" not in text
    assert "secrets.DATABASE" not in text


def test_production_deploy_workflow_untouched_by_staging_rds_hardening() -> None:
    prod = _read(PRODUCTION_WF)
    assert "dealbrain-staging-postgres" not in prod
    assert "select_canonical_staging_rds" not in prod
    assert "dealbrain-staging-postgres-recovery" not in prod
    assert "contains(DBInstanceIdentifier, 'dealbrain-production')" in prod
    rollback = _read(ROLLBACK_WF)
    assert "describe-db-instances" not in rollback
    assert "select_canonical_staging_rds" not in rollback


# ---------------------------------------------------------------------------
# 12. Existing staging deploy architecture contracts still referenced
# ---------------------------------------------------------------------------


def test_existing_staging_deploy_architecture_hooks_remain() -> None:
    text = _read(DEPLOY_WF)
    host = _read(ROOT / "scripts/deploy/host/dealbrain-staging-deploy.sh")
    assert "fetch_release_artifact.py" in text
    assert "build_staging_bundle.py" in text
    assert "verify_staging_bundle.py" in text
    assert "--rds-nonsecret .deploy-work/rds-nonsecret.json" in text
    assert "run --rm migrate" in host
    assert "force-recreate" in host
    assert host.index("run --rm migrate") < host.index("force-recreate")
    assert "STAGING_TARGET_GROUP_ARN" in text
    assert "aws s3 cp .deploy-work/bundle/bundle.tar.gz" in text
    assert "--document-name DealBrain-StagingDeploy" in text
    assert "python -m scripts.deploy.write_gha_staging_evidence" in text
    assert "python -m scripts.deploy.validate_staging_evidence" in text
