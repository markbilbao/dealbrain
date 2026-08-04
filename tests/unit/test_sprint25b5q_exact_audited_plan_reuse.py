"""Sprint 25b.5q — exact independently audited plan reuse (fail closed).

Behavioral coverage: apply mode consumes the exact audited plan-only binary and
identity artifacts. Never regenerates a replacement maintenance plan. Never
invokes real Terraform apply or mutates AWS.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.unit.test_sprint25b5n_staging_maintenance_gate import (
    ACK,
    APPLY_NONCE,
    APPLY_SH,
    ASSERT_PY,
    GATE_LIB,
    MAKEFILE,
    NONCE,
    RECOVERY_ACK,
    RUNBOOK,
    SPRINT_DOC,
    _apply_gate_env,
    _prep_approved_apply,
    _prep_success,
    _run_apply,
    _run_assert,
    _workdir_from_output,
)


def _plan_invocations(log: str) -> list[str]:
    return [
        line
        for line in log.splitlines()
        if line.startswith("terraform plan") and "-detailed-exitcode" not in line
    ]


def test_apply_uses_exact_audited_plan_path_and_skips_terraform_plan(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    plan_path = (approved / "staging-combined.tfplan").resolve()
    before = plan_path.stat()
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert f"APPLY_PATH {plan_path}" in log
    assert _plan_invocations(log) == []
    assert "Using exact independently audited plan" in proc.stdout
    assert "Apply does NOT regenerate" in proc.stdout
    after = plan_path.stat()
    assert (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns) == (
        before.st_ino,
        before.st_dev,
        before.st_size,
        before.st_mtime_ns,
    )
    assert plan_path.read_bytes() == b"REVIEWED-PLAN-BYTES-v1"


def test_audited_sha_confirmation_succeeds_for_same_binary(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    identity = json.loads((approved / "plan.identity.json").read_text(encoding="utf-8"))
    assert identity["sha256"] == digest
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert digest in proc.stdout or "Reviewed plan SHA-256" in proc.stdout


def test_equivalent_actions_different_binary_sha_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    other_bytes = b"EQUIVALENT-ACTIONS-BUT-DIFFERENT-BYTES"
    other_digest = hashlib.sha256(other_bytes).hexdigest()
    assert other_digest != digest
    # Keep structural JSON identical; only the saved binary bytes differ.
    (state / "plan.bin").write_bytes(other_bytes)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, other_digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "CHECKSUM" in proc.stderr or "checksum" in proc.stderr.lower()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_wrong_workdir_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    wrong = tmp_path / "not-the-approved-workdir"
    wrong.mkdir(mode=0o700)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(wrong, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=preflight" in proc.stderr
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_symlink_workdir_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    link = tmp_path / "approved-link"
    link.symlink_to(approved)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(link, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "symlink" in proc.stderr.lower()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_symlink_plan_file_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    plan = approved / "staging-combined.tfplan"
    real = approved / "staging-combined.tfplan.real"
    real.write_bytes(plan.read_bytes())
    real.chmod(0o600)
    plan.unlink()
    plan.symlink_to(real)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "symlink" in proc.stderr.lower()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "mutate,needle",
    [
        ("inode", "inode"),
        ("path", "path"),
        ("size", "size"),
        ("mode", "mode"),
        ("owner", "uid"),
        ("checksum", "checksum"),
    ],
)
def test_identity_field_mismatch_fails(tmp_path: Path, mutate: str, needle: str) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    identity_path = approved / "plan.identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    if mutate == "inode":
        identity["inode"] = int(identity["inode"]) + 999
    elif mutate == "path":
        identity["path"] = str(approved / "other.tfplan")
    elif mutate == "size":
        identity["size"] = int(identity["size"]) + 1
    elif mutate == "mode":
        identity["mode"] = 0o644
    elif mutate == "owner":
        identity["uid"] = int(identity["uid"]) + 1
    elif mutate == "checksum":
        identity["sha256"] = "f" * 64
    identity_path.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    identity_path.chmod(0o600)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert needle in proc.stderr.lower() or "plan_identity" in proc.stderr
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_missing_completed_plan_only_marker_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    (approved / "plan-only.complete").unlink()
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "plan-only" in proc.stderr.lower() or "complete" in proc.stderr.lower()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_failed_plan_only_workdir_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    authority = approved / "plan-only.authority.log"
    text = authority.read_text(encoding="utf-8")
    authority.write_text(text + "FAIL_PHASE=plan_validation\nFAIL: simulated\n", encoding="utf-8")
    authority.chmod(0o600)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE" in proc.stderr
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_stale_saved_plan_fails_closed_without_bypass(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    (state / "stale_plan").write_text("1", encoding="utf-8")
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=apply" in proc.stderr
    assert "stale" in proc.stderr.lower() or "apply failed" in proc.stderr.lower()
    # Native terraform apply was attempted against the exact path (no repo bypass).
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "terraform apply" in log
    assert str(approved / "staging-combined.tfplan") in log
    assert "Maintenance apply verification complete" not in proc.stdout


def test_fresh_apply_nonce_differs_and_evidence_required(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    plan_only_nonce = (approved / "host-evidence.nonce").read_text(encoding="utf-8").strip()
    assert plan_only_nonce == NONCE
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    apply_work = _workdir_from_output(proc.stdout)
    apply_nonce = (apply_work / "host-evidence.nonce").read_text(encoding="utf-8").strip()
    assert apply_nonce == APPLY_NONCE
    assert apply_nonce != plan_only_nonce
    assert (apply_work / "host-evidence-pre.json").is_file()
    assert (apply_work / "host-evidence-post.json").is_file()
    # Do not inject apply evidence into the approved plan workdir.
    assert not (approved / "host-evidence-post.json").exists()


def test_missing_approved_workdir_blocks_before_apply(tmp_path: Path) -> None:
    repo, bin_dir, state, _approved, pre, post, digest = _prep_approved_apply(tmp_path)
    env = _apply_gate_env(Path("/nonexistent-approved-workdir"), pre, post, digest)
    env["STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR"] = ""
    # Empty/missing explicit input
    proc = _run_apply(
        repo,
        bin_dir,
        {
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post),
            "STAGING_MAINTENANCE_ACK": ACK,
            "STAGING_MAINTENANCE_RECOVERY_ACK": RECOVERY_ACK,
            "STAGING_MAINTENANCE_DEMO_CLEAR": "1",
            "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM": digest,
        },
        execute=True,
    )
    assert proc.returncode != 0
    assert "APPROVED_PLAN_WORKDIR" in proc.stderr
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_ambiguous_glob_workdir_rejected(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(Path(str(approved) + "*"), pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "glob" in proc.stderr.lower() or "ambiguous" in proc.stderr.lower()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_no_apply_before_all_gates(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {
            "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR": str(approved),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post),
            "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM": digest,
            # missing ACK/demo/recovery
        },
        execute=True,
    )
    assert proc.returncode != 0
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_production_isolation_unchanged() -> None:
    for path in (APPLY_SH, GATE_LIB, ASSERT_PY):
        text = path.read_text(encoding="utf-8")
        assert "gh workflow run" not in text
        assert "environments/production" not in text or "FORBIDDEN" in text
        assert "dealbrain-production" not in text or "FORBIDDEN" in text
    apply = APPLY_SH.read_text(encoding="utf-8")
    assert "Do not touch production" in apply
    assert "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR" in apply


def test_plan_only_behavior_remains_valid(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, _post, digest = _prep_success(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)},
        execute=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Plan-only mode complete. Apply NOT executed." in proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "APPLY_PATH" not in log
    assert "terraform apply" not in log
    work = _workdir_from_output(proc.stdout)
    assert (work / "staging-combined.tfplan").is_file()
    assert (work / "plan-only.complete").is_file()
    assert (work / "repository.sha").is_file()
    assert hashlib.sha256((work / "staging-combined.tfplan").read_bytes()).hexdigest() == digest


def test_validate_approved_plan_workdir_api(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    repo_sha = (approved / "repository.sha").read_text(encoding="utf-8").strip()
    out = tmp_path / "meta.json"
    proc = _run_assert(
        [
            "validate-approved-plan-workdir",
            str(approved),
            "--repository-sha",
            repo_sha,
            "--plan-checksum",
            digest,
            "--out",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    meta = json.loads(out.read_text(encoding="utf-8"))
    assert meta["plan_sha256"] == digest
    assert meta["plan_path"] == str((approved / "staging-combined.tfplan").resolve())
    assert meta["plan_only_nonce"] == NONCE


def test_docs_and_makefile_describe_exact_plan_reuse() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    sprint = SPRINT_DOC.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    apply = APPLY_SH.read_text(encoding="utf-8")
    for doc in (runbook, sprint, apply):
        assert "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR" in doc
        lowered = doc.lower()
        assert (
            "does not regenerate" in lowered
            or "not regenerate" in lowered
            or "does not generate a replacement" in lowered
        )
    assert "test_sprint25b5q_exact_audited_plan_reuse.py" in makefile
    assert "immutable" in sprint.lower() or "exact" in sprint.lower()


def test_unsafe_workdir_mode_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    os.chmod(approved, 0o755)
    try:
        proc = _run_apply(
            repo,
            bin_dir,
            _apply_gate_env(approved, pre, post, digest),
            execute=True,
        )
    finally:
        os.chmod(approved, 0o700)
    assert proc.returncode != 0
    assert "0700" in proc.stderr or "mode" in proc.stderr.lower()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")
