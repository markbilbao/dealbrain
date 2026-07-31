"""Sprint 25b.4a — pre-live repository refinements (no live AWS actions)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import pytest
from scripts.deploy.alb_target_health import (
    AlbTargetHealthError,
    evaluate_target_health,
    evaluate_target_health_json,
)
from scripts.deploy.verify_staging_bundle import BundleVerifyError, verify_bundle

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
HOST_SCRIPTS = ROOT / "scripts/deploy/host"
DEPLOY_ROLE = ROOT / "infra/terraform/modules/github_deploy_role"
IAM_MODULE = ROOT / "infra/terraform/modules/iam"
STAGING_TG = (
    "arn:aws:elasticloadbalancing:us-east-1:123456789012:"
    "targetgroup/dealbrain-staging-api/abcdef0123456789"
)
PROD_TG = (
    "arn:aws:elasticloadbalancing:us-east-1:123456789012:"
    "targetgroup/dealbrain-production-api/abcdef0123456789"
)
INSTANCE = "i-0123456789abcdef0"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _health_payload(targets: list[tuple[str, str]]) -> dict:
    return {
        "TargetHealthDescriptions": [
            {
                "Target": {"Id": tid, "Port": 8000},
                "TargetHealth": {"State": state},
            }
            for tid, state in targets
        ]
    }


# ---------------------------------------------------------------------------
# A. head-bucket removed; ListBucket not broadened
# ---------------------------------------------------------------------------


def test_head_bucket_absent_from_deploy_workflow() -> None:
    text = _read(DEPLOY_WF)
    assert "head-bucket" not in text
    assert "s3api head-bucket" not in text


def test_list_bucket_remains_prefix_conditioned() -> None:
    deploy_main = _read(DEPLOY_ROLE / "main.tf")
    # Prefix-conditioned ListBucket for release/evidence remains.
    assert "ReleaseArtifactsListBucket" in deploy_main
    assert "s3:ListBucket" in deploy_main
    assert 'variable = "s3:prefix"' in deploy_main
    assert '"releases/*"' in deploy_main
    assert '"evidence/*"' in deploy_main
    # No unconditional bucket existence preflight grant was added.
    assert "head-bucket" not in deploy_main
    # Every ListBucket statement in deploy_allow must sit with a prefix condition.
    allow = deploy_main.split('data "aws_iam_policy_document" "deploy_allow"')[1].split(
        'data "aws_iam_policy_document" "deploy_deny"'
    )[0]
    # Split on ListBucket occurrences and require nearby StringLike/s3:prefix.
    for match in re.finditer(r"s3:ListBucket", allow):
        window = allow[match.start() : match.start() + 500]
        assert "s3:prefix" in window


def test_exact_release_and_evidence_object_ops_remain_fail_closed() -> None:
    text = _read(DEPLOY_WF)
    assert "aws s3 cp" in text
    assert "aws s3api head-object" in text
    assert "authoritative host evidence missing" in text
    assert "Refusing to fabricate staging_ok" in text
    assert "releases/" in text
    assert "evidence/" in text


# ---------------------------------------------------------------------------
# B. Strict ALB target health
# ---------------------------------------------------------------------------


def test_alb_verify_script_has_one_structured_path_no_grep_fallback() -> None:
    verify = _read(HOST_SCRIPTS / "verify-staging.sh")
    assert "alb_target_health.py" in verify
    assert "--instance-id" in verify
    assert "ALB_TIMEOUT=300" in verify
    # No generic substring healthy acceptance.
    assert "grep -qw healthy" not in verify
    assert "grep -w healthy" not in verify
    assert not re.search(r"grep\s+[^\n]*healthy", verify)


def test_alb_one_expected_target_healthy() -> None:
    evaluate_target_health(
        _health_payload([(INSTANCE, "healthy")]),
        expected_instance_id=INSTANCE,
        target_group_arn=STAGING_TG,
    )


@pytest.mark.parametrize("state", ["unhealthy", "initial", "draining", "unavailable", "unused"])
def test_alb_expected_target_non_healthy_rejected(state: str) -> None:
    with pytest.raises(AlbTargetHealthError, match="healthy"):
        evaluate_target_health(
            _health_payload([(INSTANCE, state)]),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_expected_target_absent() -> None:
    with pytest.raises(AlbTargetHealthError, match="absent"):
        evaluate_target_health(
            _health_payload([]),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_unexpected_second_target() -> None:
    with pytest.raises(AlbTargetHealthError, match="unexpected target count"):
        evaluate_target_health(
            _health_payload(
                [
                    (INSTANCE, "healthy"),
                    ("i-0deadbeefcafebabe", "healthy"),
                ]
            ),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_mixed_healthy_unhealthy_rejected() -> None:
    with pytest.raises(AlbTargetHealthError, match="unexpected target count"):
        evaluate_target_health(
            _health_payload(
                [
                    (INSTANCE, "healthy"),
                    ("i-0deadbeefcafebabe", "unhealthy"),
                ]
            ),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_wrong_instance_rejected() -> None:
    with pytest.raises(AlbTargetHealthError, match="unexpected target"):
        evaluate_target_health(
            _health_payload([("i-0deadbeefcafebabe", "healthy")]),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_malformed_output_rejected() -> None:
    with pytest.raises(AlbTargetHealthError, match="malformed"):
        evaluate_target_health_json(
            "not-json{",
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )
    with pytest.raises(AlbTargetHealthError, match="malformed"):
        evaluate_target_health(
            {"oops": []},
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_production_target_group_arn_rejected() -> None:
    with pytest.raises(AlbTargetHealthError, match="production"):
        evaluate_target_health(
            _health_payload([(INSTANCE, "healthy")]),
            expected_instance_id=INSTANCE,
            target_group_arn=PROD_TG,
        )


def test_alb_empty_and_non_staging_tg_arn_rejected() -> None:
    with pytest.raises(AlbTargetHealthError, match="empty"):
        evaluate_target_health(
            _health_payload([(INSTANCE, "healthy")]),
            expected_instance_id=INSTANCE,
            target_group_arn="",
        )
    other = (
        "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/other-api/abcdef0123456789"
    )
    with pytest.raises(AlbTargetHealthError, match="staging"):
        evaluate_target_health(
            _health_payload([(INSTANCE, "healthy")]),
            expected_instance_id=INSTANCE,
            target_group_arn=other,
        )


def test_alb_cli_accepts_and_rejects(tmp_path: Path) -> None:
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_health_payload([(INSTANCE, "healthy")])), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(_health_payload([(INSTANCE, "initial")])), encoding="utf-8")
    script = ROOT / "scripts/deploy/alb_target_health.py"
    ok = subprocess.run(
        [
            sys.executable,
            str(script),
            "--target-group-arn",
            STAGING_TG,
            "--instance-id",
            INSTANCE,
            "--input",
            str(good),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0
    fail = subprocess.run(
        [
            sys.executable,
            str(script),
            "--target-group-arn",
            STAGING_TG,
            "--instance-id",
            INSTANCE,
            "--input",
            str(bad),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert fail.returncode != 0


# ---------------------------------------------------------------------------
# C. Evidence writer fail-closed import
# ---------------------------------------------------------------------------


def test_evidence_writer_has_no_fallback_implementation() -> None:
    text = _read(HOST_SCRIPTS / "write-staging-evidence.py")
    assert "fall back" not in text.lower()
    assert "inline minimal" not in text.lower()
    assert "def create_evidence" not in text
    assert "def write_evidence" not in text
    assert "_load_evidence_api" in text
    assert "canonical evidence module unavailable" in text


def test_evidence_import_failure_exits_nonzero_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = HOST_SCRIPTS / "write-staging-evidence.py"
    spec = importlib.util.spec_from_file_location("write_staging_evidence_25b4a", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    out = tmp_path / "staging-deploy-evidence.json"

    def boom():
        print(
            "ERROR: canonical evidence module unavailable; refusing to write deployment evidence",
            file=sys.stderr,
        )
        raise SystemExit(1)

    monkeypatch.setattr(mod, "_load_evidence_api", boom)
    monkeypatch.setenv("DEALBRAIN_EVIDENCE_OUT", str(out))
    monkeypatch.setenv("DEALBRAIN_RELEASE_ID", "rel-test")
    monkeypatch.setenv("DEALBRAIN_GIT_SHA", "a" * 40)
    monkeypatch.setenv("DEALBRAIN_IMAGE_REPOSITORY", "ghcr.io/example/dealbrain")
    monkeypatch.setenv("DEALBRAIN_IMAGE_DIGEST", "sha256:" + ("b" * 64))
    monkeypatch.setenv("DEALBRAIN_DEPLOY_RUN_ID", "1")
    monkeypatch.setenv("DEALBRAIN_STARTED_AT", "2026-07-31T12:00:00Z")
    monkeypatch.setenv("DEALBRAIN_FINISHED_AT", "2026-07-31T12:01:00Z")
    monkeypatch.setenv("DEALBRAIN_DURATION", "60")
    monkeypatch.setenv("DEALBRAIN_FINAL_STATUS", "staging_ok")

    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    assert not out.exists()


def test_evidence_import_failure_subprocess_isolated(tmp_path: Path) -> None:
    """Broken evidence sibling must fail closed without writing success evidence."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    writer_src = _read(HOST_SCRIPTS / "write-staging-evidence.py")
    # Force only local imports; strip scripts.deploy package fallback for isolation.
    isolated = writer_src.replace(
        "from scripts.deploy.evidence import create_evidence, write_evidence",
        "raise ImportError('blocked package import')",
    )
    (bin_dir / "write-staging-evidence.py").write_text(isolated, encoding="utf-8")
    # Broken evidence.py that cannot supply API.
    (bin_dir / "evidence.py").write_text("raise ImportError('broken')\n", encoding="utf-8")
    out = tmp_path / "staging-deploy-evidence.json"
    env = {
        **os.environ,
        "PYTHONPATH": "",
        "DEALBRAIN_EVIDENCE_OUT": str(out),
        "DEALBRAIN_RELEASE_ID": "rel-test",
        "DEALBRAIN_GIT_SHA": "a" * 40,
        "DEALBRAIN_IMAGE_REPOSITORY": "ghcr.io/example/dealbrain",
        "DEALBRAIN_IMAGE_DIGEST": "sha256:" + ("b" * 64),
        "DEALBRAIN_DEPLOY_RUN_ID": "1",
        "DEALBRAIN_STARTED_AT": "2026-07-31T12:00:00Z",
        "DEALBRAIN_FINISHED_AT": "2026-07-31T12:01:00Z",
        "DEALBRAIN_DURATION": "60",
        "DEALBRAIN_FINAL_STATUS": "staging_ok",
    }
    proc = subprocess.run(
        [sys.executable, str(bin_dir / "write-staging-evidence.py")],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode != 0
    assert "canonical evidence module unavailable" in proc.stderr
    assert not out.exists()


# ---------------------------------------------------------------------------
# D. IAM hygiene
# ---------------------------------------------------------------------------


def test_iam_variable_docs_match_evidence_permissions() -> None:
    desc = _read(IAM_MODULE / "variables.tf")
    assert "releases/*" in desc
    assert "evidence/*" in desc
    assert "command-ID" in desc or "command-id" in desc.lower() or "SSM command" in desc
    assert "write host-authored" in desc or "deployment evidence" in desc
    host_iam = _read(IAM_MODULE / "main.tf")
    assert "ReadReleaseBundles" in host_iam
    assert "PutStagingEvidence" in host_iam
    assert "ReadEvidenceBinderObjects" in host_iam


def test_unused_ssm_list_permissions_absent() -> None:
    deploy_main = _read(DEPLOY_ROLE / "main.tf")
    assert "ssm:GetCommandInvocation" in deploy_main
    assert "ssm:SendCommand" in deploy_main
    assert "ssm:ListCommands" not in deploy_main
    assert "ssm:ListCommandInvocations" not in deploy_main
    wf = _read(DEPLOY_WF)
    assert "get-command-invocation" in wf
    assert "list-commands" not in wf
    assert "list-command-invocations" not in wf


# ---------------------------------------------------------------------------
# E. Archive device / FIFO / link coverage
# ---------------------------------------------------------------------------


def _special_member_tarball(
    tmp: Path,
    member_name: str,
    *,
    tar_type: bytes,
    linkname: str = "",
) -> Path:
    tar_path = tmp / "special.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        info = tarfile.TarInfo(name=member_name)
        info.type = tar_type
        if tar_type in (tarfile.CHRTYPE, tarfile.BLKTYPE):
            info.devmajor = 1
            info.devminor = 3
        if tar_type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            info.linkname = linkname or "/etc/passwd"
        if tar_type == tarfile.LNKTYPE:
            data = b"x"
            base = tarfile.TarInfo(name="bin/harmless.txt")
            base.size = len(data)
            tar.addfile(base, fileobj=io.BytesIO(data))
            info.linkname = "bin/harmless.txt"
        tar.addfile(info)
    return tar_path


def test_archive_device_entries_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(BundleVerifyError, match="special file"):
            verify_bundle(_special_member_tarball(root, "bin/evil-chr", tar_type=tarfile.CHRTYPE))
        with pytest.raises(BundleVerifyError, match="special file"):
            verify_bundle(_special_member_tarball(root, "bin/evil-blk", tar_type=tarfile.BLKTYPE))


def test_archive_fifo_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(BundleVerifyError, match="special file"):
            verify_bundle(_special_member_tarball(root, "bin/evil-fifo", tar_type=tarfile.FIFOTYPE))


def test_archive_symlink_and_hardlink_still_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(BundleVerifyError, match="symlink|hardlink"):
            verify_bundle(
                _special_member_tarball(
                    root, "bin/link", tar_type=tarfile.SYMTYPE, linkname="/etc/passwd"
                )
            )
        with pytest.raises(BundleVerifyError, match="symlink|hardlink"):
            verify_bundle(_special_member_tarball(root, "bin/hard", tar_type=tarfile.LNKTYPE))


# ---------------------------------------------------------------------------
# Invariants: no production path / no TF apply / no snapshot
# ---------------------------------------------------------------------------


def test_no_production_workflow_snapshot_or_terraform_apply() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").is_file()
    assert not (WORKFLOWS / "rollback.yml").is_file()
    text = _read(DEPLOY_WF)
    assert "terraform apply" not in text
    assert "CreateDBSnapshot" not in text
    assert "create-db-snapshot" not in text.lower()
    assert "environment: production" not in text


def test_deploy_passes_instance_id_to_verify() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert '--instance-id "$INSTANCE_ID"' in host or '--instance-id "$INSTANCE_ID"' in host


def test_alb_helper_bundled() -> None:
    from scripts.deploy.build_staging_bundle import INCLUDE_FILES

    assert ("scripts/deploy/alb_target_health.py", "bin/alb_target_health.py") in INCLUDE_FILES
