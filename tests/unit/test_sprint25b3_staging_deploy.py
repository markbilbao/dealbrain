"""Sprint 25b.3 — staging deployment pipeline repository contract tests."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import stat
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from scripts.deploy.build_staging_bundle import build_bundle
from scripts.deploy.evidence import (
    EvidenceError,
    compute_evidence_sha256,
    create_evidence,
    validate_evidence,
)
from scripts.deploy.validate_staging_release import StagingIngestError, validate_for_staging
from scripts.deploy.verify_staging_bundle import verify_bundle
from scripts.release.manifest import compute_manifest_sha256, create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
STAGING_TF = ROOT / "infra/terraform/environments/staging"
PROD_TF = ROOT / "infra/terraform/environments/production"
HOST_SCRIPTS = ROOT / "scripts/deploy/host"
USER_DATA = ROOT / "infra/ec2/user_data/staging.sh"
SSM_MODULE = ROOT / "infra/terraform/modules/ssm_deploy_document"
ARTIFACTS_MODULE = ROOT / "infra/terraform/modules/release_artifacts"
DEPLOY_ROLE = ROOT / "infra/terraform/modules/github_deploy_role"
IAM_MODULE = ROOT / "infra/terraform/modules/iam"
COMPOSE = ROOT / "infra/compose"
EVIDENCE_SCHEMA = ROOT / "schemas/staging-deploy-evidence.schema.json"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _load_assemble_module():
    path = HOST_SCRIPTS / "assemble-runtime-env.py"
    spec = importlib.util.spec_from_file_location("assemble_runtime_env", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _built_manifest(**overrides: object) -> dict:
    manifest = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-07-31T12:00:00Z",
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
    )
    if overrides:
        manifest = copy.deepcopy(manifest)
        manifest.update(overrides)
        if "manifest_sha256" not in overrides:
            manifest["manifest_sha256"] = compute_manifest_sha256(manifest)
    return manifest


def _sample_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="c" * 64,
        deploy_workflow_run_id="999",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-999-staging",
        ec2_instance_id="i-0123456789abcdef0",
        ssm_command_id="cmd-1",
        migration_revision_before="abc",
        migration_revision_after="def",
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-07-31T11:00:00Z",
        deployment_started_at="2026-07-31T12:00:00Z",
        deployment_finished_at="2026-07-31T12:05:00Z",
        deployment_duration_seconds=300,
        final_status="staging_ok",
        failure_reason=None,
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def test_staging_workflow_exists() -> None:
    assert DEPLOY_WF.is_file()


def test_production_and_rollback_workflows_absent() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").is_file()
    assert not (WORKFLOWS / "rollback.yml").is_file()


def test_workflow_dispatch_only() -> None:
    text = _read(DEPLOY_WF)
    assert "workflow_dispatch:" in text
    assert "build_workflow_run_id:" in text
    # allow_older removed — was echo-only and not enforceable without live state.
    assert "allow_older" not in text
    # No automatic triggers
    assert re.search(r"(?m)^on:\s*$", text) or "on:" in text
    assert "pull_request:" not in text
    assert "workflow_run:" not in text
    # push must not be a trigger key under on:
    assert not re.search(r"(?m)^  push:", text)


def test_environment_exactly_staging() -> None:
    text = _read(DEPLOY_WF)
    assert re.search(r"(?m)^\s+environment:\s+staging\s*$", text)
    assert "AWS_ROLE_ARN_PRODUCTION" not in text
    # May mention production only in negative assertions (grep -qv).
    assert "role-to-assume: ${{ vars.AWS_ROLE_ARN }}" in text
    assert "environment: production" not in text


def test_main_only_assertion() -> None:
    text = _read(DEPLOY_WF)
    assert "refs/heads/main" in text
    assert "fork" in text.lower()


def test_oidc_no_static_keys() -> None:
    text = _read(DEPLOY_WF)
    assert "aws-actions/configure-aws-credentials@v4" in text
    assert "role-to-assume" in text
    assert "id-token: write" in text
    assert "AWS_ACCESS_KEY_ID" not in text
    assert "AWS_SECRET_ACCESS_KEY" not in text


def test_staging_role_only() -> None:
    text = _read(DEPLOY_WF)
    assert "dealbrain-staging-gha-deploy" in text
    assert "vars.AWS_ROLE_ARN" in text
    assert "role-to-assume: ${{ vars.AWS_ROLE_ARN }}" in text
    # Must positively assert staging and reject production assume.
    assert "grep -q 'dealbrain-staging-gha-deploy'" in text
    assert "grep -qv 'dealbrain-production-gha-deploy'" in text


def test_no_image_build_in_deploy_workflow() -> None:
    text = _read(DEPLOY_WF).lower()
    assert "docker/build-push-action" not in text
    assert "build-push-action" not in text
    assert "docker build " not in text
    # imagetools inspect is digest verification, not a rebuild
    assert "imagetools inspect" in text


def test_manifest_validation_required_in_workflow() -> None:
    text = _read(DEPLOY_WF)
    assert "validate_staging_release.py" in text
    assert "fetch_release_artifact.py" in text
    assert "Build Image" in text


def test_upstream_ci_and_build_verification() -> None:
    text = _read(DEPLOY_WF)
    assert "test_workflow_run_id" in text
    assert "imagetools inspect" in text
    assert "headSha" in text


def test_digest_only_deployment() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert 'docker pull "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"' in host
    assert "sha256:" in host


def test_mutable_tags_forbidden() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "latest" in host
    assert "ci-latest" in host
    good = _built_manifest()
    validate_for_staging(good, expected_build_run_id="111", expected_git_sha=SAMPLE_SHA)
    bad = _built_manifest(final_status="staging_ok")
    with pytest.raises(StagingIngestError):
        validate_for_staging(bad, expected_build_run_id="111")


def test_reject_previously_staged_manifest() -> None:
    from scripts.release.manifest import ManifestError

    bad = _built_manifest(staging_deployment_run_id="123")
    with pytest.raises((StagingIngestError, ManifestError)):
        validate_for_staging(bad)


def test_custom_ssm_document_only() -> None:
    text = _read(DEPLOY_WF)
    assert "DealBrain-StagingDeploy" in text
    assert "--document-name DealBrain-StagingDeploy" in text
    assert "--document-name AWS-RunShellScript" not in text
    ssm_vars = _read(SSM_MODULE / "variables.tf")
    ssm_main = _read(SSM_MODULE / "main.tf")
    assert 'default     = "DealBrain-StagingDeploy"' in ssm_vars
    assert "var.document_name" in ssm_main
    assert "ReleaseId" in ssm_main
    assert "BundleBucket" in ssm_main
    assert "2400" in ssm_main or "timeout_seconds" in ssm_vars


def test_no_aws_run_shell_script_staging_allow() -> None:
    staging_main = _read(STAGING_TF / "main.tf")
    assert "allowed_ssm_document_arns" in staging_main
    assert "ssm_deploy_document.document_arn" in staging_main
    # Must not leave the variable unset (empty → managed RunShellScript default).
    assert "[module.ssm_deploy_document.document_arn]" in staging_main
    # Production root must not wire the staging custom document in this sprint.
    assert "ssm_deploy_document" not in _read(PROD_TF / "main.tf")


def test_no_ssh() -> None:
    text = _read(DEPLOY_WF).lower()
    assert "ssh " not in text
    assert "scp " not in text
    assert "openssh" not in text


def test_no_secrets_from_github() -> None:
    text = _read(DEPLOY_WF)
    assert "secrets.AWS_" not in text
    assert "secrets.DATABASE" not in text
    assert "secrets.GHCR" not in text
    assert "secrets.OPENAI" not in text


def test_s3_staging_only_bundle_modeled() -> None:
    assert ARTIFACTS_MODULE.is_dir()
    main = _read(ARTIFACTS_MODULE / "main.tf")
    assert "aws_s3_bucket" in main
    assert "aws_s3_bucket_public_access_block" in main
    assert "versioning" in main.lower()
    staging = _read(STAGING_TF / "main.tf")
    assert 'module "release_artifacts"' in staging
    prod = _read(PROD_TF / "main.tf")
    assert "release_artifacts" not in prod


def test_production_overlay_excluded_from_bundle() -> None:
    manifest = _built_manifest()
    with tempfile.TemporaryDirectory() as tmp:
        man_path = Path(tmp) / "release-manifest.json"
        man_path.write_text(json.dumps(manifest), encoding="utf-8")
        out = Path(tmp) / "out"
        tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=out)
        with tarfile.open(tarball, "r:gz") as archive:
            members = archive.getnames()
        assert "compose/docker-compose.production.yml" not in members
        assert "compose/docker-compose.staging.yml" in members
        assert "compose/docker-compose.base.yml" in members
        checksum = checksum_path.read_text(encoding="utf-8").split()[0]
        verify_bundle(tarball, expected_checksum=checksum, expected_release_id=meta["release_id"])


def test_host_bootstrap_modeled() -> None:
    ud = _read(USER_DATA)
    assert "docker" in ud
    assert "/opt/dealbrain" in ud
    assert "/opt/dealbrain/releases" in ud
    assert "/opt/dealbrain/runtime" in ud
    assert "/opt/dealbrain/locks" in ud
    assert "/var/log/dealbrain" in ud
    assert "bootstrap.ok" in ud
    for needle in ("GITHUB_TOKEN", "DATABASE_URL=", "secret_key"):
        assert needle not in ud
    staging = _read(STAGING_TF / "main.tf")
    assert "staging_user_data" in staging
    assert "user_data" in staging


def test_runtime_secrets_host_side() -> None:
    asm = _read(HOST_SCRIPTS / "assemble-runtime-env.py")
    assert "secretsmanager" in asm
    assert "get-secret-value" in asm
    assert "dealbrain/staging" in asm
    assert "production" in asm
    assert "0o600" in asm
    wf = _read(DEPLOY_WF)
    assert "GetSecretValue" not in wf
    assert "secretsmanager" not in wf.lower()


def test_database_url_encoding_special_characters() -> None:
    mod = _load_assemble_module()
    url = mod.build_database_url(
        username="user@name",
        password="p@ss:/w#ord!",
        host="db.example",
        port=5432,
        database="dealbrain",
    )
    assert url.startswith("postgresql+asyncpg://")
    assert quote_plus("user@name", safe="") in url
    assert quote_plus("p@ss:/w#ord!", safe="") in url
    assert "@db.example:5432/dealbrain" in url
    assert "p@ss:/w#ord!" not in url


def test_env_file_mode_0600() -> None:
    mod = _load_assemble_module()
    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / "staging.env"
        mod._atomic_write_env(
            env_path,
            {"APP_ENV": "staging", "DATABASE_URL": "postgresql+asyncpg://u:p@h:1/db"},
        )
        mode = stat.S_IMODE(env_path.stat().st_mode)
        assert mode == 0o600


def test_ghcr_password_stdin() -> None:
    ghcr = _read(HOST_SCRIPTS / "ghcr-login.sh")
    assert "--password-stdin" in ghcr
    assert "docker login ghcr.io" in ghcr
    assert "dealbrain/staging/ghcr_pull" in ghcr
    assert "production" in ghcr
    assert "0600" in ghcr


def test_pre_post_pull_disk_checks() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "before-pull" in host
    assert "after-pull" in host
    assert "require_disk_gib" in host


def test_one_shot_migration_separate() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "--profile migrate" in host
    assert "run --rm migrate" in host
    assert "dealbrain-staging" in host
    base = _read(COMPOSE / "docker-compose.base.yml")
    assert "migrate" in base
    assert "alembic" in base


def test_api_only_after_migration() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    mig_idx = host.index("run --rm migrate")
    api_idx = host.index("force-recreate")
    assert mig_idx < api_idx
    assert "MIGRATE_RC" in host
    assert "untouched" in host.lower()


def test_no_api_alembic_startup() -> None:
    base = _read(COMPOSE / "docker-compose.base.yml")
    assert 'command: ["alembic", "upgrade", "head"]' in base
    api_block = base.split("\n  api:\n", 1)[1].split("\n  migrate:\n", 1)[0]
    # Strip comments before asserting no alembic command on the API service.
    api_code = "\n".join(
        line for line in api_block.splitlines() if not line.lstrip().startswith("#")
    )
    assert "alembic" not in api_code.lower()
    assert "must NOT run migrations" in base


def test_workflow_concurrency_cancel_false() -> None:
    text = _read(DEPLOY_WF)
    assert "group: deploy-staging" in text
    assert "cancel-in-progress: false" in text
    assert "timeout-minutes: 60" in text


def test_host_flock() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "flock" in host
    assert "staging-deploy.lock" in host
    assert "staging-deploy.lock.info" in host


def test_current_previous_release_retention() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "/opt/dealbrain/releases" in host
    assert "retained" in host.lower() or "keep" in host.lower()
    assert "/opt/dealbrain/releases" in _read(USER_DATA)


def test_deploy_version_marker() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "DEPLOY_VERSION" in host
    assert "release_id" in host
    assert "git_sha" in host
    assert "image_digest" in host
    assert "deployed_at" in host


def test_live_and_ready_gates() -> None:
    verify = _read(HOST_SCRIPTS / "verify-staging.sh")
    assert "/live" in verify
    assert "/ready" in verify
    assert "180" in verify


def test_alb_health_verification() -> None:
    verify = _read(HOST_SCRIPTS / "verify-staging.sh")
    assert "describe-target-health" in verify
    assert "300" in verify
    assert "healthy" in verify


def test_evidence_schema_and_checksum() -> None:
    assert EVIDENCE_SCHEMA.is_file()
    schema = json.loads(_read(EVIDENCE_SCHEMA))
    required = set(schema["required"])
    for field in (
        "deployment_started_at",
        "deployment_finished_at",
        "deployment_duration_seconds",
        "image_id",
        "repo_digest",
        "image_created_at",
        "evidence_sha256",
        "source_manifest_sha256",
    ):
        assert field in required
    validate_evidence(_sample_evidence())


def test_evidence_checksum_tamper_detection() -> None:
    payload = _sample_evidence()
    payload["final_status"] = "failed"
    with pytest.raises(EvidenceError):
        validate_evidence(payload)


def test_deployment_duration_and_image_metadata_fields() -> None:
    payload = _sample_evidence()
    assert isinstance(payload["deployment_duration_seconds"], int)
    assert payload["image_id"]
    assert payload["repo_digest"]
    assert payload["image_created_at"]
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "IMAGE_ID" in host
    assert "REPO_DIGEST" in host
    assert "IMAGE_CREATED_AT" in host


def test_no_production_snapshot_logic() -> None:
    text = _read(DEPLOY_WF) + _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "CreateDBSnapshot" not in text
    assert "create-db-snapshot" not in text.lower()
    assert "rds:CreateDBSnapshot" in _read(DEPLOY_ROLE / "main.tf")


def test_no_terraform_apply_in_workflows() -> None:
    for wf in WORKFLOWS.glob("*.yml"):
        text = _read(wf)
        assert "terraform apply" not in text
        assert "terraform destroy" not in text


def test_staging_iam_s3_and_ssm_wiring() -> None:
    staging = _read(STAGING_TF / "main.tf")
    assert "release_artifacts_bucket_arn" in staging
    assert "allowed_ssm_document_arns" in staging
    assert "s3:GetObject" in _read(IAM_MODULE / "main.tf")
    assert "s3:PutObject" in _read(DEPLOY_ROLE / "main.tf")


def test_permissions_block() -> None:
    text = _read(DEPLOY_WF)
    assert "id-token: write" in text
    assert "contents: read" in text
    assert "actions: read" in text
    assert "packages: read" in text


# ---------------------------------------------------------------------------
# Acceptance-fix coverage (Sprint 25b.3 audit)
# ---------------------------------------------------------------------------


def test_missing_host_evidence_fails_workflow() -> None:
    text = _read(DEPLOY_WF)
    assert "authoritative host evidence missing" in text
    assert "Refusing to fabricate staging_ok" in text
    assert "aws s3api head-object" in text
    evidence_step = text.split("Collect and validate")[1].split("Upload staging evidence")[0]
    assert "|| true" not in evidence_step
    # write_gha script accepts existing evidence only — no --final-status create path.
    gha = _read(ROOT / "scripts/deploy/write_gha_staging_evidence.py")
    assert "never synthesize" in gha.lower() or "refusing to fabricate" in gha.lower()
    assert "create_evidence" not in gha


def test_synthetic_staging_ok_cannot_be_created_by_gha_writer() -> None:
    from scripts.deploy.write_gha_staging_evidence import main as gha_main

    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "staging-deploy-evidence.json"
        rc = gha_main(
            [
                "--evidence",
                str(missing),
                "--release-id",
                f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
                "--git-sha",
                SAMPLE_SHA,
                "--image-repository",
                SAMPLE_REPO,
                "--image-digest",
                SAMPLE_DIGEST,
                "--source-manifest-sha256",
                "c" * 64,
                "--deploy-run-id",
                "999",
                "--aws-account-id",
                "123456789012",
                "--aws-region",
                "us-east-1",
                "--ec2-instance-id",
                "i-0123456789abcdef0",
                "--ssm-command-id",
                "cmd-1",
            ]
        )
        assert rc == 1
        assert not missing.exists()


def test_staging_ok_requires_migration_health_and_image_metadata() -> None:
    with pytest.raises(EvidenceError, match="migration_revision_after"):
        validate_evidence(_sample_evidence(migration_revision_after=None))
    with pytest.raises(EvidenceError, match="image_id"):
        validate_evidence(_sample_evidence(image_id=None))
    with pytest.raises(EvidenceError, match="image_created_at"):
        validate_evidence(_sample_evidence(image_created_at=None))
    with pytest.raises(EvidenceError, match="localhost_live"):
        validate_evidence(_sample_evidence(localhost_live=False))
    # Null migration must be rejected for staging_ok.
    with pytest.raises(EvidenceError):
        validate_evidence(_sample_evidence(migration_revision_after=None, image_id=None))


def test_failure_evidence_cannot_masquerade_as_success() -> None:
    failed = _sample_evidence(
        final_status="failed",
        failure_reason="migration_failed",
        localhost_live=False,
        localhost_ready=False,
        alb_target_healthy=False,
        smoke_ok=False,
        migration_revision_after=None,
        image_id=None,
        repo_digest=None,
        image_created_at=None,
    )
    validate_evidence(failed)
    # Flipping status to staging_ok without fixing gates/metadata must fail.
    with pytest.raises(EvidenceError):
        validate_evidence(
            _sample_evidence(
                final_status="staging_ok",
                failure_reason="migration_failed",
            )
        )
    with pytest.raises(EvidenceError):
        validate_evidence(
            _sample_evidence(
                final_status="failed",
                failure_reason="migration_failed",
                localhost_live=True,
                localhost_ready=True,
                alb_target_healthy=True,
                smoke_ok=True,
            )
        )


def test_evidence_binding_mismatch_fails() -> None:
    from scripts.deploy.evidence import validate_evidence_bindings

    payload = _sample_evidence()
    with pytest.raises(EvidenceError, match="binding mismatch"):
        validate_evidence_bindings(
            payload,
            release_id=payload["release_id"],
            git_sha="f" * 40,
            image_digest=SAMPLE_DIGEST,
            image_repository=SAMPLE_REPO,
            source_manifest_sha256="c" * 64,
            deploy_workflow_run_id="999",
            aws_account_id="123456789012",
            aws_region="us-east-1",
            ec2_instance_id="i-0123456789abcdef0",
            ssm_command_id="cmd-1",
        )
    with pytest.raises(EvidenceError, match="binding mismatch"):
        validate_evidence_bindings(
            payload,
            release_id=payload["release_id"],
            git_sha=SAMPLE_SHA,
            image_digest="sha256:" + ("a" * 64),
            image_repository=SAMPLE_REPO,
            source_manifest_sha256="c" * 64,
            deploy_workflow_run_id="999",
            aws_account_id="123456789012",
            aws_region="us-east-1",
            ec2_instance_id="i-0123456789abcdef0",
            ssm_command_id="cmd-1",
        )


def _malicious_tarball(tmp: Path, member_name: str, *, link_type: str | None = None) -> Path:
    tar_path = tmp / "evil.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        if link_type == "symlink":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        elif link_type == "hardlink":
            # Add a regular file then a hardlink to it.
            data = b"x"
            base = tarfile.TarInfo(name="bin/harmless.txt")
            base.size = len(data)
            tar.addfile(base, fileobj=__import__("io").BytesIO(data))
            link = tarfile.TarInfo(name=member_name)
            link.type = tarfile.LNKTYPE
            link.linkname = "bin/harmless.txt"
            tar.addfile(link)
        else:
            data = b"evil"
            info = tarfile.TarInfo(name=member_name)
            info.size = len(data)
            tar.addfile(info, fileobj=__import__("io").BytesIO(data))
    return tar_path


def test_archive_traversal_and_absolute_paths_rejected() -> None:
    from scripts.deploy.verify_staging_bundle import BundleVerifyError, verify_bundle

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(BundleVerifyError, match="traversal|absolute|unexpected"):
            verify_bundle(_malicious_tarball(root, "../escape"))
        with pytest.raises(BundleVerifyError, match="absolute|unexpected"):
            verify_bundle(_malicious_tarball(root, "/absolute/path"))


def test_archive_symlink_and_hardlink_rejected() -> None:
    from scripts.deploy.verify_staging_bundle import BundleVerifyError, verify_bundle

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(BundleVerifyError, match="symlink|hardlink"):
            verify_bundle(_malicious_tarball(root, "bin/link", link_type="symlink"))
        with pytest.raises(BundleVerifyError, match="symlink|hardlink"):
            verify_bundle(_malicious_tarball(root, "bin/hard", link_type="hardlink"))


def test_archive_unexpected_production_overlay_rejected() -> None:
    from scripts.deploy.verify_staging_bundle import BundleVerifyError, verify_bundle

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(BundleVerifyError, match="forbidden|production"):
            verify_bundle(_malicious_tarball(root, "compose/docker-compose.production.yml"))


def test_migration_timeout_bounds_and_api_order() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "MIGRATE_TIMEOUT_SEC=1200" in host
    assert "timeout --signal=TERM" in host
    assert "migration_timeout" in host
    # timeout wraps migration; force-recreate comes after migrate success check.
    timeout_idx = host.index("timeout --signal=TERM")
    migrate_rc_idx = host.index("MIGRATE_RC")
    api_idx = host.index("force-recreate")
    assert timeout_idx < migrate_rc_idx < api_idx
    assert "API left untouched" in host


def test_live_response_content_verified() -> None:
    from scripts.deploy.probe_checks import ProbeCheckError, validate_live_json_text

    with pytest.raises(ProbeCheckError):
        validate_live_json_text("not-json")
    with pytest.raises(ProbeCheckError):
        validate_live_json_text(
            json.dumps(
                {
                    "status": "up",
                    "service": "DealBrain",
                    "version": "1.0.0",
                    "uptime_seconds": 1.0,
                    "live": False,
                }
            )
        )
    validate_live_json_text(
        json.dumps(
            {
                "status": "up",
                "service": "DealBrain",
                "version": "1.0.0",
                "uptime_seconds": 1.0,
                "live": True,
            }
        )
    )
    verify = _read(HOST_SCRIPTS / "verify-staging.sh")
    assert ".live == true" in verify
    assert "HTTP 200 alone" in verify or "not HTTP 200 alone" in verify


def test_current_symlink_remains_prior_on_migration_failure() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert "PREVIOUS_CURRENT" in host
    assert "restored current symlink to prior release after failure" in host
    # current is updated only after health gates / DEPLOY_VERSION.
    current_idx = host.index('ln -sfn "$RELEASE_DIR" "${ROOT}/current.new"')
    migrate_idx = host.index("MIGRATE_TIMEOUT_SEC")
    assert migrate_idx < current_idx
    assert "force-recreate" in host[:current_idx]


def test_lock_acquired_before_extraction() -> None:
    host = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    ud = _read(USER_DATA)
    flock_idx = host.index("flock -w 30")
    extract_idx = host.index("--extract-to")
    assert flock_idx < extract_idx
    assert "flock -w 30" in ud
    assert "DEALBRAIN_LOCK_HELD=1" in ud
    # Entrypoint must not point current before health gates.
    entry = ud.split("ENTRYPOINT", 1)[1]
    assert "ln -sfn" not in entry or "current" not in entry.split("Do NOT update")[0]


def test_exact_iam_allow_actions_runtime_apis() -> None:
    deploy_main = _read(DEPLOY_ROLE / "main.tf")
    assert "elasticloadbalancing:DescribeTargetHealth" not in deploy_main
    assert "elasticloadbalancing:DescribeTargetGroups" not in deploy_main
    assert "ec2:DescribeInstances" in deploy_main
    assert "rds:DescribeDBInstances" in deploy_main
    host_iam = _read(IAM_MODULE / "main.tf")
    assert "ec2:DescribeTags" in host_iam
    assert "elasticloadbalancing:DescribeTargetHealth" in host_iam
    assert "s3:PutObject" in host_iam
    assert "evidence/*" in host_iam
    wf = _read(DEPLOY_WF)
    assert "STAGING_TARGET_GROUP_ARN" in wf
    assert "describe-target-groups" not in wf


def test_allow_older_absent() -> None:
    assert "allow_older" not in _read(DEPLOY_WF)
    assert "allow_older" not in _read(ROOT / "docs/runbooks/STAGING_DEPLOY.md")


def test_database_url_encoding_edge_characters() -> None:
    mod = _load_assemble_module()
    cases = [
        ("user\nname", "pass"),
        ("user", "pass'word"),
        ("user", "p%ercent"),
        ("user", "p/slash"),
        ("user", "p:colon"),
        ("user@name", "p@ss"),
        ("usér", "päss"),
        ("user", "p$`!;&|"),
    ]
    for username, password in cases:
        url = mod.build_database_url(
            username=username,
            password=password,
            host="db.example",
            port=5432,
            database="dealbrain",
        )
        assert quote_plus(username, safe="") in url
        assert quote_plus(password, safe="") in url
        assert password not in url or password == quote_plus(password, safe="")


def test_bootstrap_no_unsigned_compose_download() -> None:
    ud = _read(USER_DATA)
    # Must never fetch Compose as an unsigned GitHub binary.
    assert "github.com/docker/compose/releases" not in ud
    assert "raw.githubusercontent.com" not in ud
    assert "curl -SL" not in ud
    assert "curl -L https://github.com/docker" not in ud


def test_bootstrap_al2023_compose_unavailable_still_completes() -> None:
    """AL2023 default repos lack docker-compose-plugin; bootstrap must not abort."""
    ud = _read(USER_DATA)
    # Forbidden: the package path that fails closed on live AL2023 hosts.
    assert "dnf -y install docker-compose-plugin" not in ud
    assert "dnf install docker-compose-plugin" not in ud
    # Compose must not be a hard bootstrap gate (would prevent bootstrap.ok).
    assert "docker compose version >/dev/null\n" not in ud
    assert 'docker compose version >/dev/null 2>&1; then' in ud or "docker compose unavailable" in ud
    assert "deferred" in ud.lower()
    # Successful bootstrap artifacts must still be modeled.
    assert "touch /opt/dealbrain/bootstrap.ok" in ud
    assert "/opt/dealbrain/bin/dealbrain-staging-deploy.sh" in ud
    assert "chmod 0755 /opt/dealbrain/bin/dealbrain-staging-deploy.sh" in ud
    # Docker engine + fail-closed checks remain required.
    assert "dnf -y install \\\n  docker \\" in ud or "\n  docker \\\n" in ud
    assert "command -v docker >/dev/null" in ud
    assert "systemctl enable docker" in ud
    assert "systemctl start docker" in ud
    # Deploy orchestrator still fail-closes without Compose.
    orch = _read(HOST_SCRIPTS / "dealbrain-staging-deploy.sh")
    assert 'docker compose version >/dev/null || die "docker compose missing"' in orch


def test_architecture_lock_trailing_newline() -> None:
    lock = ROOT / "docs/architecture/ARCHITECTURE_LOCK.md"
    data = lock.read_bytes()
    assert data.endswith(b"\n")
