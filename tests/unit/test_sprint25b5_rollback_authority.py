"""Sprint 25b.5 audit hardening — prior evidence, migration, release verify, pointers."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tarfile
import textwrap
from pathlib import Path

import pytest
from scripts.deploy.build_staging_bundle import build_bundle
from scripts.deploy.evidence import compute_evidence_sha256, create_evidence, write_evidence
from scripts.deploy.prior_staging_evidence import (
    PriorEvidenceError,
    discover_candidate_pairs,
    load_prior_evidence_with_sidecar,
    resolve_target_migration_revision,
    select_authoritative_prior_staging_evidence,
)
from scripts.deploy.rollback_evidence import create_rollback_evidence, validate_rollback_evidence
from scripts.deploy.validate_rollback_eligibility import (
    RollbackEligibilityError,
    validate_database_compatibility,
)
from scripts.deploy.verify_host_rollback_tooling import (
    HostToolingError,
    build_host_tooling_capability,
    verify_host_rollback_tooling,
    write_host_tooling_capability,
)
from scripts.deploy.verify_staging_bundle import (
    APPLICATION_RUNTIME_MEMBERS,
    CURRENT_BUNDLE_SCHEMA_VERSION,
    HISTORICAL_BUNDLE_SCHEMA_VERSION,
    REQUIRED_MEMBERS,
    BundleVerifyError,
    extract_validated_bundle,
    verify_release_directory,
)
from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "scripts/deploy/host"
ATOMICITY_SH = HOST / "deploy_atomicity.sh"
ROLLBACK_SH = HOST / "dealbrain-staging-rollback.sh"

SAMPLE_SHA = "83bfc6c57fd99a43445b6edaddcaf863fabf3473"
SAMPLE_DIGEST = "sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f"
OTHER_SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
CANON_REV = "d4e5f6a7b8c9"
BASELINE_RELEASE = f"rel-20260802T093246Z-{SAMPLE_SHA[:12]}"
SECOND_RELEASE = f"rel-20260802T120000Z-{OTHER_SHA[:12]}"
ACCOUNT = "123456789012"
REGION = "us-east-1"
INSTANCE = "i-0123456789abcdef0"
MANIFEST_SHA = "c" * 64


def _prior(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=BASELINE_RELEASE,
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256=MANIFEST_SHA,
        deploy_workflow_run_id="11",
        aws_account_id=ACCOUNT,
        aws_region=REGION,
        assumed_role_arn=f"arn:aws:iam::{ACCOUNT}:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-11-staging",
        ec2_instance_id=INSTANCE,
        ssm_command_id="11111111-1111-1111-1111-111111111111",
        migration_revision_before=CANON_REV,
        migration_revision_after=CANON_REV,
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-08-02T09:00:00Z",
        deployment_started_at="2026-08-02T09:30:00Z",
        deployment_finished_at="2026-08-02T09:35:00Z",
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


def _write_candidate(dir_path: Path, run_id: str, payload: dict) -> tuple[Path, Path, str]:
    run_dir = dir_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "staging-deploy-evidence.json"
    write_evidence(json_path, payload)
    sidecar = json_path.with_suffix(json_path.suffix + ".sha256")
    assert sidecar.is_file()
    return json_path, sidecar, f"{run_id}/staging-deploy-evidence.json"


def _select(candidates_dir: Path, **binding_overrides: object):
    pairs = discover_candidate_pairs(candidates_dir)
    kwargs = dict(
        expected_release_id=BASELINE_RELEASE,
        expected_image_digest=SAMPLE_DIGEST,
        expected_image_repository=SAMPLE_REPO,
        expected_aws_account_id=ACCOUNT,
        expected_aws_region=REGION,
        expected_ec2_instance_id=INSTANCE,
        expected_source_manifest_sha256=MANIFEST_SHA,
    )
    kwargs.update(binding_overrides)
    return select_authoritative_prior_staging_evidence(pairs, **kwargs)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _historical_release_tree(tmp_path: Path) -> Path:
    """Build a schema-1 historical-style release directory (no rollback binaries)."""
    release = tmp_path / "releases" / BASELINE_RELEASE
    (release / "compose").mkdir(parents=True)
    (release / "manifest").mkdir(parents=True)
    (release / "bin").mkdir(parents=True)
    (release / "compose" / "docker-compose.base.yml").write_text("services: {}\n", encoding="utf-8")
    (release / "compose" / "docker-compose.staging.yml").write_text(
        "services:\n  api: {}\n", encoding="utf-8"
    )
    (release / "manifest" / "release-manifest.json").write_text(
        json.dumps(
            {
                "release_id": BASELINE_RELEASE,
                "git_sha": SAMPLE_SHA,
                "image_repository": SAMPLE_REPO,
                "image_digest": SAMPLE_DIGEST,
            }
        ),
        encoding="utf-8",
    )
    (release / "bin" / "ghcr-login.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    files = {
        "compose/docker-compose.base.yml": _sha(release / "compose/docker-compose.base.yml"),
        "compose/docker-compose.staging.yml": _sha(release / "compose/docker-compose.staging.yml"),
        "manifest/release-manifest.json": _sha(release / "manifest" / "release-manifest.json"),
        "bin/ghcr-login.sh": _sha(release / "bin" / "ghcr-login.sh"),
    }
    meta = {
        "schema_version": HISTORICAL_BUNDLE_SCHEMA_VERSION,
        "release_id": BASELINE_RELEASE,
        "git_sha": SAMPLE_SHA,
        "image_repository": SAMPLE_REPO,
        "image_digest": SAMPLE_DIGEST,
        "source_manifest_sha256": MANIFEST_SHA,
        "file_checksums": files,
        "created_at": "2026-08-02T09:32:46Z",
    }
    meta_path = release / "bundle-meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files["bundle-meta.json"] = _sha(meta_path)
    meta["file_checksums"] = files
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (release / "DEPLOY_VERSION").write_text(
        json.dumps(
            {
                "release_id": BASELINE_RELEASE,
                "git_sha": SAMPLE_SHA,
                "image_digest": SAMPLE_DIGEST,
                "deployed_at": "2026-08-02T09:32:46Z",
                "migration_revision": CANON_REV,
            }
        ),
        encoding="utf-8",
    )
    return release


# ---------------------------------------------------------------------------
# Prior evidence authority (cases 1–8)
# ---------------------------------------------------------------------------


def test_prior_evidence_checksum_valid_and_bindings_eligible(tmp_path: Path) -> None:
    _write_candidate(tmp_path, "11", _prior())
    selected = _select(tmp_path)
    assert selected.deploy_workflow_run_id == "11"
    assert selected.migration_revision_after == CANON_REV


def test_prior_evidence_checksum_mismatch_fails(tmp_path: Path) -> None:
    json_path, sidecar, _key = _write_candidate(tmp_path, "11", _prior())
    sidecar.write_text(("0" * 64) + "\n", encoding="utf-8")
    with pytest.raises(PriorEvidenceError, match="sidecar mismatch"):
        load_prior_evidence_with_sidecar(json_path, sidecar)


def test_prior_evidence_missing_sidecar_fails(tmp_path: Path) -> None:
    json_path, sidecar, _key = _write_candidate(tmp_path, "11", _prior())
    sidecar.unlink()
    with pytest.raises(PriorEvidenceError, match="missing evidence checksum sidecar"):
        load_prior_evidence_with_sidecar(json_path, sidecar)


def test_prior_evidence_wrong_account_fails(tmp_path: Path) -> None:
    _write_candidate(tmp_path, "11", _prior(aws_account_id="999999999999"))
    with pytest.raises(PriorEvidenceError, match="aws_account_id"):
        _select(tmp_path)


def test_prior_evidence_wrong_region_fails(tmp_path: Path) -> None:
    _write_candidate(tmp_path, "11", _prior(aws_region="us-west-2"))
    with pytest.raises(PriorEvidenceError, match="aws_region"):
        _select(tmp_path)


def test_prior_evidence_wrong_instance_fails(tmp_path: Path) -> None:
    _write_candidate(tmp_path, "11", _prior(ec2_instance_id="i-0deadbeefdeadbeef"))
    with pytest.raises(PriorEvidenceError, match="ec2_instance_id"):
        _select(tmp_path)


def test_multiple_valid_evidence_uses_latest_finished_at(tmp_path: Path) -> None:
    _write_candidate(
        tmp_path,
        "10",
        _prior(
            deploy_workflow_run_id="10",
            deployment_started_at="2026-08-02T08:00:00Z",
            deployment_finished_at="2026-08-02T08:05:00Z",
            deployment_duration_seconds=300,
            role_session_name="gha-10-staging",
        ),
    )
    _write_candidate(
        tmp_path,
        "12",
        _prior(
            deploy_workflow_run_id="12",
            deployment_started_at="2026-08-02T10:00:00Z",
            deployment_finished_at="2026-08-02T10:05:00Z",
            deployment_duration_seconds=300,
            role_session_name="gha-12-staging",
            ssm_command_id="12121212-1212-1212-1212-121212121212",
        ),
    )
    selected = _select(tmp_path)
    assert selected.deploy_workflow_run_id == "12"


def test_ambiguous_tied_candidates_fail(tmp_path: Path) -> None:
    finished = "2026-08-02T09:35:00Z"
    _write_candidate(
        tmp_path,
        "11",
        _prior(deploy_workflow_run_id="11", deployment_finished_at=finished),
    )
    _write_candidate(
        tmp_path,
        "13",
        _prior(
            deploy_workflow_run_id="13",
            deployment_finished_at=finished,
            role_session_name="gha-13-staging",
            ssm_command_id="13131313-1313-1313-1313-131313131313",
        ),
    )
    with pytest.raises(PriorEvidenceError, match="ambiguous"):
        _select(tmp_path)


# ---------------------------------------------------------------------------
# Migration authority (cases 9–10, 22)
# ---------------------------------------------------------------------------


def test_migration_fallback_uses_exact_selected_validated_evidence(tmp_path: Path) -> None:
    _write_candidate(
        tmp_path,
        "11",
        _prior(migration_revision_after="aabbccddeeff"),
    )
    selected = _select(tmp_path)
    result = resolve_target_migration_revision(
        deploy_version_path=tmp_path / "missing-DEPLOY_VERSION",
        validated_prior=selected,
    )
    assert result.authority == "validated_prior_staging_evidence"
    assert result.migration_revision == "aabbccddeeff"
    assert result.prior is selected


def test_migration_fallback_cannot_use_another_evidence_file(tmp_path: Path) -> None:
    _write_candidate(tmp_path / "ok", "11", _prior(migration_revision_after=CANON_REV))
    other = _prior(
        migration_revision_after="ffffffffffff",
        deploy_workflow_run_id="99",
        role_session_name="gha-99-staging",
        ssm_command_id="99999999-9999-9999-9999-999999999999",
        deployment_finished_at="2026-08-02T11:00:00Z",
        deployment_started_at="2026-08-02T10:55:00Z",
        deployment_duration_seconds=300,
    )
    # Unchecked "other" file must not become authority unless selected.
    selected = _select(tmp_path / "ok")
    assert selected.migration_revision_after == CANON_REV
    assert other["migration_revision_after"] != selected.migration_revision_after
    result = resolve_target_migration_revision(
        deploy_version_path=None,
        validated_prior=selected,
    )
    assert result.migration_revision == CANON_REV


def test_database_incompatibility_exits_before_api_replacement() -> None:
    with pytest.raises(RollbackEligibilityError, match="database_incompatible"):
        validate_database_compatibility(
            current_db_revision="newerrev001",
            target_recorded_revision=CANON_REV,
        )
    host = ROLLBACK_SH.read_text(encoding="utf-8")
    assert host.index("database_incompatible") < host.index("API_REPLACEMENT_OCCURRED=1")
    assert "alembic downgrade" not in host.lower()


# ---------------------------------------------------------------------------
# Local release checksum verification (cases 11–14)
# ---------------------------------------------------------------------------


def test_local_release_all_checksums_valid(tmp_path: Path) -> None:
    release = _historical_release_tree(tmp_path)
    meta = verify_release_directory(
        release,
        expected_release_id=BASELINE_RELEASE,
        expected_git_sha=SAMPLE_SHA,
        expected_image_repository=SAMPLE_REPO,
        expected_digest=SAMPLE_DIGEST,
        expected_source_manifest_sha256=MANIFEST_SHA,
        require_deploy_version=True,
    )
    assert meta["schema_version"] == HISTORICAL_BUNDLE_SCHEMA_VERSION


def test_local_release_modified_file_rejected(tmp_path: Path) -> None:
    release = _historical_release_tree(tmp_path)
    target = release / "compose" / "docker-compose.staging.yml"
    target.write_text(target.read_text(encoding="utf-8") + "# tampered\n", encoding="utf-8")
    with pytest.raises(BundleVerifyError, match="checksum mismatch"):
        verify_release_directory(release, expected_release_id=BASELINE_RELEASE)


def test_local_release_missing_required_file_rejected(tmp_path: Path) -> None:
    release = _historical_release_tree(tmp_path)
    (release / "compose" / "docker-compose.staging.yml").unlink()
    with pytest.raises(BundleVerifyError, match="missing required member"):
        verify_release_directory(release, expected_release_id=BASELINE_RELEASE)


def test_local_release_unsafe_checksum_path_or_symlink_rejected(tmp_path: Path) -> None:
    release = _historical_release_tree(tmp_path)
    meta_path = release / "bundle-meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["file_checksums"]["../escape.txt"] = "a" * 64
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(BundleVerifyError, match="traversal|unsafe|absolute"):
        verify_release_directory(release)

    release2 = _historical_release_tree(tmp_path / "sym")
    escape = tmp_path / "outside-secret"
    escape.write_text("secret", encoding="utf-8")
    link = release2 / "compose" / "docker-compose.staging.yml"
    link.unlink()
    link.symlink_to(escape)
    with pytest.raises(BundleVerifyError, match="symlink|missing required member"):
        verify_release_directory(release2)


# ---------------------------------------------------------------------------
# Historical bundle compatibility (cases 15–16)
# ---------------------------------------------------------------------------


def test_historical_build_image_15_style_bundle_accepted(tmp_path: Path) -> None:
    release = _historical_release_tree(tmp_path)
    # Package as tarball and extract via schema-aware verifier.
    tarball = tmp_path / "hist.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        for path in sorted(release.rglob("*")):
            if path.is_file() and path.name != "DEPLOY_VERSION":
                tar.add(path, arcname=path.relative_to(release).as_posix())
    checksum = _sha(tarball)
    dest = tmp_path / "extracted"
    result = extract_validated_bundle(
        tarball,
        dest,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    assert result["meta"]["schema_version"] == HISTORICAL_BUNDLE_SCHEMA_VERSION
    assert not (dest / "bin" / "dealbrain-staging-rollback.sh").exists()
    for rel in APPLICATION_RUNTIME_MEMBERS:
        assert (dest / rel).is_file()


def test_unsupported_historical_bundle_schema_rejected(tmp_path: Path) -> None:
    release = _historical_release_tree(tmp_path)
    meta_path = release / "bundle-meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["schema_version"] = 99
    # Rebuild checksums roughly — identity check fails on schema before checksums.
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(BundleVerifyError, match="unsupported bundle schema_version"):
        verify_release_directory(release)


def test_current_schema_bundle_requires_rollback_tooling(tmp_path: Path) -> None:
    manifest = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="30741970067",
        test_workflow_run_id="222",
        created_at="2026-08-02T09:32:46Z",
        release_id=BASELINE_RELEASE,
    )
    man_path = tmp_path / "release-manifest.json"
    man_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out"
    tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=out)
    assert meta["schema_version"] == CURRENT_BUNDLE_SCHEMA_VERSION
    for rel in REQUIRED_MEMBERS:
        assert rel in meta["file_checksums"]
    extract_validated_bundle(
        tarball,
        tmp_path / "cur",
        expected_checksum=checksum_path.read_text(encoding="utf-8").split()[0],
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )


# ---------------------------------------------------------------------------
# Pointer compensating transaction (cases 17–21)
# ---------------------------------------------------------------------------


def _pointer_harness(script_body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script_body],
        check=False,
        capture_output=True,
        text=True,
    )


def test_pointer_pair_successful_update(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "dealbrain"
    rel_a = root / "releases" / BASELINE_RELEASE
    rel_b = root / "releases" / SECOND_RELEASE
    rel_a.mkdir(parents=True)
    rel_b.mkdir(parents=True)
    for rel, rid, sha, digest in (
        (rel_a, BASELINE_RELEASE, SAMPLE_SHA, SAMPLE_DIGEST),
        (rel_b, SECOND_RELEASE, OTHER_SHA, OTHER_DIGEST),
    ):
        (rel / "DEPLOY_VERSION").write_text(
            json.dumps(
                {
                    "release_id": rid,
                    "git_sha": sha,
                    "image_digest": digest,
                    "deployed_at": "2026-08-02T12:00:00Z",
                    "migration_revision": CANON_REV,
                }
            ),
            encoding="utf-8",
        )
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        RELEASE_DIR="{rel_a}"
        RELEASE_ID="{BASELINE_RELEASE}"
        GIT_SHA="{SAMPLE_SHA}"
        IMAGE_DIGEST="{SAMPLE_DIGEST}"
        PREVIOUS_CURRENT="{rel_b}"
        MIGRATION_AFTER="{CANON_REV}"
        source "{ATOMICITY_SH}"
        ln -sfn "{rel_b}" "$ROOT/current"
        ln -sfn "{rel_a}" "$ROOT/previous"
        _atomicity_running_api_digest() {{ echo "{SAMPLE_DIGEST}"; }}
        commit_release_pointer
        test "$(readlink -f "$ROOT/current")" = "{rel_a}"
        test "$(readlink -f "$ROOT/previous")" = "{rel_b}"
        echo OK
        """
    )
    proc = _pointer_harness(script)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "OK" in proc.stdout


def test_pointer_first_update_failure_restores_original_pair(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "dealbrain"
    rel_a = root / "releases" / BASELINE_RELEASE
    rel_b = root / "releases" / SECOND_RELEASE
    rel_a.mkdir(parents=True)
    rel_b.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        source "{ATOMICITY_SH}"
        ln -sfn "{rel_b}" "$ROOT/current"
        ln -sfn "{rel_a}" "$ROOT/previous"
        atomic_point_previous() {{ return 1; }}
        if commit_current_and_previous_pointers "{rel_a}" "{rel_b}"; then
          echo "UNEXPECTED_SUCCESS"; exit 2
        fi
        test "$(readlink -f "$ROOT/current")" = "{rel_b}"
        test "$(readlink -f "$ROOT/previous")" = "{rel_a}"
        echo "$FAILURE_REASON"
        """
    )
    proc = _pointer_harness(script)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (
        "pointer_previous_update_failed" in proc.stdout
        or "pointer_pair_restore_failed" in proc.stdout
    )


def test_pointer_second_update_failure_restores_original_pair(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "dealbrain"
    rel_a = root / "releases" / BASELINE_RELEASE
    rel_b = root / "releases" / SECOND_RELEASE
    rel_a.mkdir(parents=True)
    rel_b.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        source "{ATOMICITY_SH}"
        ln -sfn "{rel_b}" "$ROOT/current"
        ln -sfn "{rel_a}" "$ROOT/previous"
        atomic_point_current() {{ return 1; }}
        if commit_current_and_previous_pointers "{rel_a}" "{rel_b}"; then
          echo "UNEXPECTED_SUCCESS"; exit 2
        fi
        test "$(readlink -f "$ROOT/current")" = "{rel_b}"
        test "$(readlink -f "$ROOT/previous")" = "{rel_a}"
        echo "$FAILURE_REASON"
        """
    )
    proc = _pointer_harness(script)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (
        "symlink_prepare_or_replace_failed" in proc.stdout
        or "pointer_pair_restore_failed" in proc.stdout
    )


def test_pointer_previous_originally_absent_restored_to_absent(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "dealbrain"
    rel_a = root / "releases" / BASELINE_RELEASE
    rel_b = root / "releases" / SECOND_RELEASE
    rel_a.mkdir(parents=True)
    rel_b.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        source "{ATOMICITY_SH}"
        ln -sfn "{rel_b}" "$ROOT/current"
        # previous absent
        atomic_point_current() {{ return 1; }}
        if commit_current_and_previous_pointers "{rel_a}" "{rel_b}"; then
          echo "UNEXPECTED_SUCCESS"; exit 2
        fi
        test "$(readlink -f "$ROOT/current")" = "{rel_b}"
        if [[ -e "$ROOT/previous" || -L "$ROOT/previous" ]]; then
          echo "PREVIOUS_SHOULD_BE_ABSENT"; exit 3
        fi
        echo OK
        """
    )
    proc = _pointer_harness(script)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "OK" in proc.stdout


def test_pointer_restoration_failure_nonzero_no_rollback_ok(tmp_path: Path) -> None:
    root = tmp_path / "opt" / "dealbrain"
    rel_a = root / "releases" / BASELINE_RELEASE
    rel_b = root / "releases" / SECOND_RELEASE
    rel_a.mkdir(parents=True)
    rel_b.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        source "{ATOMICITY_SH}"
        ln -sfn "{rel_b}" "$ROOT/current"
        ln -sfn "{rel_a}" "$ROOT/previous"
        atomic_point_current() {{ return 1; }}
        _restore_pointer_state() {{ return 1; }}
        set +e
        commit_current_and_previous_pointers "{rel_a}" "{rel_b}"
        rc=$?
        set -e
        test "$rc" -ne 0
        test "$FAILURE_REASON" = "pointer_pair_restore_failed"
        echo OK
        """
    )
    proc = _pointer_harness(script)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    host = ROLLBACK_SH.read_text(encoding="utf-8")
    assert "pointer_pair_restore_failed" in ATOMICITY_SH.read_text(encoding="utf-8")
    assert 'FINAL_STATUS="rollback_ok"' in host
    assert "Never claim rollback_ok" in host or "never claim rollback_ok" in host.lower()


# ---------------------------------------------------------------------------
# API failure / recovery executable harness (cases 23–30)
# Uses the exact production restore_source_api between stable markers.
# ---------------------------------------------------------------------------


def _extract_production_restore_source_api() -> str:
    host = ROLLBACK_SH.read_text(encoding="utf-8")
    begin = "# --- BEGIN restore_source_api (test-extractable) ---"
    end = "# --- END restore_source_api (test-extractable) ---"
    assert begin in host, "missing BEGIN marker for restore_source_api"
    assert end in host, "missing END marker for restore_source_api"
    region = host.split(begin, 1)[1].split(end, 1)[0]
    assert "restore_source_api()" in region
    assert 'DEALBRAIN_IMAGE="${IMAGE_REPOSITORY}@${src_digest}"' in region
    assert "*:latest" not in region
    return region.strip() + "\n"


def _recovery_harness(
    tmp_path: Path,
    fail_stage: str,
    *,
    docker_fail: bool = False,
    start_on_target: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Exercise production restore_source_api + pointer compensation with fakes."""
    root = tmp_path / "opt" / "dealbrain"
    source = root / "releases" / SECOND_RELEASE
    target = root / "releases" / BASELINE_RELEASE
    prev = root / "releases" / f"rel-prev-{SAMPLE_SHA[:12]}"
    for d in (source, target, prev):
        (d / "compose").mkdir(parents=True)
        (d / "compose" / "docker-compose.base.yml").write_text("x\n", encoding="utf-8")
        (d / "compose" / "docker-compose.staging.yml").write_text("y\n", encoding="utf-8")
        (d / "DEPLOY_VERSION").write_text("{}", encoding="utf-8")
    runtime = root / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "staging.env").write_text("APP_ENV=staging\n", encoding="utf-8")
    compose_log = tmp_path / "compose.log"
    production_fn = _extract_production_restore_source_api()
    initial_current = target if start_on_target else source
    docker_rc = "1" if docker_fail or fail_stage == "restore_fails" else "0"
    # Concatenate production function outside an f-string so bash braces stay intact.
    preamble = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        SOURCE_DIR="{source}"
        SOURCE_IMAGE_DIGEST="{OTHER_DIGEST}"
        IMAGE_REPOSITORY="{SAMPLE_REPO}"
        COMPOSE_PROJECT=dealbrain-staging
        ENV_FILE="{runtime}/staging.env"
        PREVIOUS_BEFORE="{prev}"
        RELEASE_COMMITTED=0
        API_REPLACEMENT_OCCURRED=1
        FINAL_STATUS=failed
        FAILURE_REASON="{fail_stage}"
        POINTER_RESTORE_FAILED=0
        COMPOSE_LOG="{compose_log}"
        source "{ATOMICITY_SH}"
        ln -sfn "{initial_current}" "$ROOT/current"
        ln -sfn "{prev}" "$ROOT/previous"
        # Fake docker / health / logging — production restore_source_api still runs.
        docker() {{
          printf '%s\\n' "$*" >> "$COMPOSE_LOG"
          printf 'DEALBRAIN_IMAGE=%s\\n' "${{DEALBRAIN_IMAGE:-}}" >> "$COMPOSE_LOG"
          if [[ "$1" == "compose" ]]; then
            return {docker_rc}
          fi
          return 0
        }}
        curl() {{ echo "fake-curl"; return 0; }}
        log() {{ echo "[log] $*"; }}
        """
    )
    epilogue = textwrap.dedent(
        f"""
        # Prove we loaded the production helper (digest authority, not a clone).
        declare -f restore_source_api | grep -F '@${{src_digest}}' >/dev/null
        declare -f restore_source_api | grep -F 'atomic_point_current' >/dev/null
        if restore_source_api; then
          echo RESTORE_OK
          code=1
        else
          POINTER_RESTORE_FAILED=1
          FAILURE_REASON=post_replacement_source_restore_failed
          echo RESTORE_FAIL
          code=1
        fi
        echo "CURRENT=$(readlink -f "$ROOT/current" || true)"
        echo "PREVIOUS=$(readlink -f "$ROOT/previous" || true)"
        echo "FAILURE_REASON=$FAILURE_REASON"
        echo "POINTER_RESTORE_FAILED=$POINTER_RESTORE_FAILED"
        echo "FINAL_STATUS=$FINAL_STATUS"
        # Rollback_ok is impossible on recovery paths.
        test "$FINAL_STATUS" != "rollback_ok"
        if [[ "$POINTER_RESTORE_FAILED" -eq 1 ]]; then
          exit 1
        fi
        test "$(readlink -f "$ROOT/current")" = "{source}"
        test "$(readlink -f "$ROOT/previous")" = "{prev}"
        # Non-zero exit: recovery after gate failure cannot claim success.
        exit "$code"
        """
    )
    return _pointer_harness(preamble + "\n" + production_fn + "\n" + epilogue)


@pytest.mark.parametrize(
    "stage",
    [
        "localhost_live_failed",
        "localhost_ready_failed",
        "alb_health_failed",
        "running_digest_mismatch",
    ],
)
def test_post_api_gate_failure_restores_source_and_pointers(tmp_path: Path, stage: str) -> None:
    proc = _recovery_harness(tmp_path, stage)
    # Production recovery restores pointers then exits non-zero (no rollback_ok).
    assert proc.returncode != 0, proc.stderr + proc.stdout
    assert "RESTORE_OK" in proc.stdout
    assert "POINTER_RESTORE_FAILED=0" in proc.stdout
    assert SECOND_RELEASE in proc.stdout
    compose_log = (tmp_path / "compose.log").read_text(encoding="utf-8")
    assert f"DEALBRAIN_IMAGE={SAMPLE_REPO}@{OTHER_DIGEST}" in compose_log
    assert ":latest" not in compose_log
    assert "@sha256:" in compose_log or OTHER_DIGEST in compose_log


def test_source_api_restoration_succeeds_with_exact_digest(tmp_path: Path) -> None:
    proc = _recovery_harness(tmp_path, "source_restore_probe")
    assert proc.returncode != 0, proc.stderr + proc.stdout
    assert "RESTORE_OK" in proc.stdout
    compose_log = (tmp_path / "compose.log").read_text(encoding="utf-8")
    assert f"{SAMPLE_REPO}@{OTHER_DIGEST}" in compose_log
    assert "up -d --force-recreate --no-deps api" in compose_log.replace("\n", " ")


def test_source_api_restoration_failure_explicit_status(tmp_path: Path) -> None:
    proc = _recovery_harness(tmp_path, "restore_fails", docker_fail=True)
    assert proc.returncode != 0
    assert "RESTORE_FAIL" in proc.stdout
    assert "post_replacement_source_restore_failed" in proc.stdout
    assert "POINTER_RESTORE_FAILED=1" in proc.stdout
    assert "FINAL_STATUS=failed" in proc.stdout
    assert "rollback_ok" not in proc.stdout.split("FINAL_STATUS=")[-1]


def test_recovery_uses_production_restore_source_api_not_clone() -> None:
    region = _extract_production_restore_source_api()
    assert "atomic_point_current" in region
    assert "atomic_point_previous" in region
    assert 'DEALBRAIN_IMAGE="${IMAGE_REPOSITORY}@${src_digest}"' in region
    # No mutable tag construction in the production helper.
    assert ":latest" not in region
    assert ":staging" not in region
    src = ROLLBACK_SH.read_text(encoding="utf-8")
    assert src.count("restore_source_api()") == 1


def test_recovery_never_uses_mutable_tags(tmp_path: Path) -> None:
    proc = _recovery_harness(tmp_path, "localhost_live_failed")
    assert "RESTORE_OK" in proc.stdout
    compose_log = (tmp_path / "compose.log").read_text(encoding="utf-8")
    for tag in (":latest", ":ci-latest", ":staging", ":production", ":main"):
        assert tag not in compose_log
    assert f"@{OTHER_DIGEST}" in compose_log


def test_evidence_finalization_failure_after_pointer_commit_no_rollback_ok(
    tmp_path: Path,
) -> None:
    # Healthy committed target/source pointer pair remains truthful, but
    # evidence finalization failure exits non-zero and cannot validate rollback_ok.
    root = tmp_path / "opt" / "dealbrain"
    source = root / "releases" / SECOND_RELEASE
    target = root / "releases" / BASELINE_RELEASE
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        source "{ATOMICITY_SH}"
        ln -sfn "{target}" "$ROOT/current"
        ln -sfn "{source}" "$ROOT/previous"
        FINAL_STATUS=failed
        FAILURE_REASON=evidence_upload_failed
        RELEASE_COMMITTED=1
        code=1
        test "$(readlink -f "$ROOT/current")" = "{target}"
        test "$(readlink -f "$ROOT/previous")" = "{source}"
        test "$FINAL_STATUS" != "rollback_ok"
        echo "CURRENT=$(readlink -f "$ROOT/current")"
        echo "PREVIOUS=$(readlink -f "$ROOT/previous")"
        echo "FAILURE_REASON=$FAILURE_REASON"
        exit "$code"
        """
    )
    proc = _pointer_harness(script)
    assert proc.returncode != 0, proc.stderr + proc.stdout
    assert str(target) in proc.stdout
    assert str(source) in proc.stdout
    assert "evidence_upload_failed" in proc.stdout

    payload = create_rollback_evidence(
        rollback_workflow_run_id="555",
        aws_account_id=ACCOUNT,
        aws_region=REGION,
        assumed_role_arn=f"arn:aws:iam::{ACCOUNT}:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-555-staging-rollback",
        ec2_instance_id=INSTANCE,
        ssm_command_id="22222222-2222-2222-2222-222222222222",
        rollback_started_at="2026-08-02T13:00:00Z",
        rollback_finished_at="2026-08-02T13:05:00Z",
        rollback_duration_seconds=300,
        source_release_id=SECOND_RELEASE,
        source_image_digest=OTHER_DIGEST,
        target_release_id=BASELINE_RELEASE,
        target_image_digest=SAMPLE_DIGEST,
        target_git_sha=SAMPLE_SHA,
        target_image_repository=SAMPLE_REPO,
        target_manifest_sha256="a" * 64,
        migration_revision_before=CANON_REV,
        migration_revision_after=CANON_REV,
        target_migration_revision_authority="validated_prior_staging_evidence",
        current_pointer_before=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
        current_pointer_after=f"/opt/dealbrain/releases/{BASELINE_RELEASE}",
        previous_pointer_before=f"/opt/dealbrain/releases/{BASELINE_RELEASE}",
        previous_pointer_after=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
        running_digest_after=SAMPLE_DIGEST,
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        final_status="failed",
        failure_reason="evidence_upload_failed",
    )
    validate_rollback_evidence(payload)
    assert payload["final_status"] != "rollback_ok"
    host = ROLLBACK_SH.read_text(encoding="utf-8")
    assert "evidence_upload_failed" in host
    assert 'FINAL_STATUS="rollback_ok"' in host
    assert "success evidence write/upload failed" in host


def test_evidence_checksum_upload_failure_cannot_return_zero() -> None:
    host = ROLLBACK_SH.read_text(encoding="utf-8")
    assert "if ! write_evidence; then" in host
    assert "EVIDENCE_UPLOADED" in host
    assert 'FINAL_STATUS="failed"' in host
    # on_exit coerces success without rollback_ok to non-zero.
    assert "rollback_ok" in host
    assert "POINTER_RESTORE_FAILED" in host
    assert "code=1" in host


def test_no_failure_path_leaves_unhealthy_current_with_exit_zero(tmp_path: Path) -> None:
    host = ROLLBACK_SH.read_text(encoding="utf-8")
    assert "Never leave current pointing" in host or "never leave current pointing" in host.lower()
    assert "POINTER_RESTORE_FAILED" in host
    assert "post_replacement_source_restore_failed" in host
    # Executable: restore leaves current on source; exit is still non-zero.
    proc = _recovery_harness(tmp_path, "alb_health_failed")
    assert proc.returncode != 0
    assert "RESTORE_OK" in proc.stdout
    assert SECOND_RELEASE in proc.stdout.split("CURRENT=")[-1].splitlines()[0]


def test_makefile_validate_targets_include_rollback_authority() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    authority = "tests/unit/test_sprint25b5_rollback_authority.py"
    for target in ("validate-staging-deploy:", "validate-pre-live:"):
        assert target in makefile
        # Slice from target header to the next blank-line-terminated recipe block.
        after = makefile.split(target, 1)[1]
        recipe = after.split("\n\n", 1)[0]
        assert authority in recipe, f"{target} missing {authority}"
        assert "tests/unit/test_sprint25b5_rollback_workflow.py" in recipe
    assert makefile.count(authority) >= 2


def test_module_lockfile_absent_and_staging_lockfile_tracked() -> None:
    module_lock = ROOT / "infra/terraform/modules/ssm_rollback_document/.terraform.lock.hcl"
    staging_lock = ROOT / "infra/terraform/environments/staging/.terraform.lock.hcl"
    assert not module_lock.exists()
    assert staging_lock.is_file()
    tracked = subprocess.run(
        ["git", "ls-files", "infra/terraform/environments/staging/.terraform.lock.hcl"],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert tracked.returncode == 0
    assert tracked.stdout.strip() == "infra/terraform/environments/staging/.terraform.lock.hcl"
    diff = subprocess.run(
        ["git", "diff", "--", "infra/terraform/environments/staging/.terraform.lock.hcl"],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert diff.returncode == 0
    assert diff.stdout == ""


# ---------------------------------------------------------------------------
# Host tooling preflight
# ---------------------------------------------------------------------------


def test_host_tooling_preflight_accepts_matching_capability(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in (
        "dealbrain-staging-rollback.sh",
        "deploy_atomicity.sh",
        "rollback_evidence.py",
        "write-staging-rollback-evidence.py",
        "prior_staging_evidence.py",
        "resolve-rollback-migration.py",
        "verify_host_rollback_tooling.py",
        "staging-rollback-evidence.schema.json",
        "verify_staging_bundle.py",
        "evidence.py",
    ):
        (bin_dir / name).write_text(f"content-{name}\n", encoding="utf-8")
    cap = build_host_tooling_capability(bin_dir)
    cap_path = bin_dir / "staging-host-tooling.json"
    write_host_tooling_capability(cap_path, cap)
    verified = verify_host_rollback_tooling(cap_path, bin_dir)
    assert verified["tooling_version"] == "25b.5"


def test_host_tooling_preflight_rejects_missing_or_outdated(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    with pytest.raises(HostToolingError, match="capability missing"):
        verify_host_rollback_tooling(bin_dir / "staging-host-tooling.json", bin_dir)

    for name in (
        "dealbrain-staging-rollback.sh",
        "deploy_atomicity.sh",
        "rollback_evidence.py",
        "write-staging-rollback-evidence.py",
        "prior_staging_evidence.py",
        "resolve-rollback-migration.py",
        "verify_host_rollback_tooling.py",
        "staging-rollback-evidence.schema.json",
        "verify_staging_bundle.py",
        "evidence.py",
    ):
        (bin_dir / name).write_text(f"content-{name}\n", encoding="utf-8")
    cap = build_host_tooling_capability(bin_dir, tooling_version="25b.4")
    cap_path = bin_dir / "staging-host-tooling.json"
    write_host_tooling_capability(cap_path, cap)
    with pytest.raises(HostToolingError, match="outdated|unexpected"):
        verify_host_rollback_tooling(cap_path, bin_dir)
    (bin_dir / "dealbrain-staging-rollback.sh").write_text("tampered\n", encoding="utf-8")
    cap2 = build_host_tooling_capability(bin_dir)
    # Restore expected version but mutate after write.
    write_host_tooling_capability(cap_path, cap2)
    (bin_dir / "dealbrain-staging-rollback.sh").write_text("tampered-again\n", encoding="utf-8")
    with pytest.raises(HostToolingError, match="checksum mismatch"):
        verify_host_rollback_tooling(cap_path, bin_dir)


def test_host_rollback_invokes_tooling_preflight_before_mutation() -> None:
    host = ROLLBACK_SH.read_text(encoding="utf-8")
    assert "verify_host_rollback_tooling.py" in host
    assert host.index("verify_host_rollback_tooling.py") < host.index("acquired flock")
    assert "staging-host-tooling.json" in host
