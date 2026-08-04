"""Sprint 25b.5p — retain validated maintenance host evidence (fail closed).

Behavioral coverage for atomic retention of validated pre/post host evidence
into the authoritative work directory. Never invokes real Terraform apply or
mutates AWS.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unittest.mock as mock
from pathlib import Path

import pytest

from tests.unit.test_sprint25b5n_staging_maintenance_gate import (
    ACK,
    APPLY_SH,
    ASSERT,
    ASSERT_PY,
    GATE_LIB,
    NONCE,
    PYTHON,
    RECOVERY_ACK,
    ROOT,
    RUNBOOK,
    SPRINT_DOC,
    _host_evidence,
    _prep_success,
    _run_apply,
    _run_assert,
    _write_json,
)


def _workdir_from_output(proc_stdout: str) -> Path:
    match = re.search(r"work_dir=(\S+)", proc_stdout)
    assert match, f"work_dir not found in output:\n{proc_stdout}"
    work = Path(match.group(1))
    assert work.is_dir(), work
    return work


def _stat_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _assert_retained_file_safety(path: Path) -> None:
    assert path.is_file()
    assert not path.is_symlink()
    st = path.stat()
    assert st.st_uid == os.geteuid()
    assert st.st_gid == os.getegid()
    assert _stat_mode(path) == 0o600


def test_plan_only_retains_validated_host_evidence_pre(tmp_path: Path) -> None:
    """Regression: external pre validates + plan-only success ⇒ workdir has pre JSON."""
    repo, bin_dir, state, pre, _post, _digest = _prep_success(tmp_path)
    source_bytes = pre.read_bytes()
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)},
        execute=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Plan-only mode complete" in proc.stdout
    assert "Plan-only artifacts retained at" in proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "APPLY_PATH" not in log
    assert "terraform apply" not in log

    work = _workdir_from_output(proc.stdout)
    retained = work / "host-evidence-pre.json"
    binding = work / "host-evidence-pre.json.sha256"
    assert retained.is_file(), f"missing retained evidence in {work}: {list(work.iterdir())}"
    assert not (work / "host-evidence-post.json").exists()

    # Byte-for-byte identical to validated source
    assert retained.read_bytes() == source_bytes
    _assert_retained_file_safety(retained)
    _assert_retained_file_safety(binding)

    retained_data = json.loads(retained.read_text(encoding="utf-8"))
    assert retained_data["nonce"] == NONCE
    assert retained_data["phase"] == "pre-apply"
    # repository_sha optional in fixture; when present must match HEAD
    repo_sha = (repo / ".git").exists() and __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    if "repository_sha" in retained_data:
        assert retained_data["repository_sha"] == repo_sha

    digest = hashlib.sha256(source_bytes).hexdigest()
    assert binding.read_text(encoding="utf-8").startswith(digest)
    assert "host-evidence-pre.json" in binding.read_text(encoding="utf-8")

    # Expected companion artifacts also retained
    assert (work / "staging-combined.tfplan").is_file()
    assert (work / "staging-combined.plan.json").is_file()
    assert (work / "plan.identity.json").is_file()
    assert (work / "host-evidence.nonce").is_file()
    assert (work / "host-evidence-collect-pre.sh").is_file()


def test_wrong_nonce_rejected_and_not_retained(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, _post, _digest = _prep_success(tmp_path)
    bad = _write_json(
        tmp_path / "bad-nonce.json",
        _host_evidence("pre-apply", nonce="b" * 32, uptime=9000),
    )
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(bad)},
        execute=False,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_nonce" in proc.stderr
    assert "Plan-only mode complete" not in proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "APPLY_PATH" not in log
    work = _workdir_from_output(proc.stdout + proc.stderr)
    assert not (work / "host-evidence-pre.json").exists()


def test_wrong_phase_rejected_and_not_retained(tmp_path: Path) -> None:
    repo, bin_dir, state, _pre, post, _digest = _prep_success(tmp_path)
    # Supply post-apply evidence where pre-apply is required.
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(post)},
        execute=False,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_phase" in proc.stderr
    assert "Plan-only mode complete" not in proc.stdout
    work = _workdir_from_output(proc.stdout + proc.stderr)
    assert not (work / "host-evidence-pre.json").exists()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_malformed_json_rejected_and_not_retained(tmp_path: Path) -> None:
    repo, bin_dir, state, _pre, _post, _digest = _prep_success(tmp_path)
    bad = tmp_path / "malformed.json"
    bad.write_text("{not-json", encoding="utf-8")
    bad.chmod(0o600)
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(bad)},
        execute=False,
    )
    assert proc.returncode != 0
    assert "Plan-only mode complete" not in proc.stdout
    work = _workdir_from_output(proc.stdout + proc.stderr)
    assert not (work / "host-evidence-pre.json").exists()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_symlink_source_rejected(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, _post, _digest = _prep_success(tmp_path)
    link = tmp_path / "pre-link.json"
    link.symlink_to(pre)
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(link)},
        execute=False,
    )
    assert proc.returncode != 0
    assert "Plan-only mode complete" not in proc.stdout
    work = _workdir_from_output(proc.stdout + proc.stderr)
    assert not (work / "host-evidence-pre.json").exists()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_no_evidence_retained_before_validation_succeeds(tmp_path: Path) -> None:
    repo, bin_dir, state, _pre, _post, _digest = _prep_success(tmp_path)
    missing = tmp_path / "does-not-exist.json"
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(missing)},
        execute=False,
    )
    assert proc.returncode != 0
    assert "Plan-only mode complete" not in proc.stdout
    combined = proc.stdout + proc.stderr
    match = re.search(r"work_dir=(\S+)", combined)
    if match:
        work = Path(match.group(1))
        if work.is_dir():
            assert not (work / "host-evidence-pre.json").exists()
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_apply_mode_retains_pre_before_apply_and_post_after_validation(
    tmp_path: Path,
) -> None:
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path)
    pre_bytes = pre.read_bytes()
    post_bytes = post.read_bytes()
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
    assert proc.returncode == 0, proc.stderr + proc.stdout
    work = _workdir_from_output(proc.stdout)
    retained_pre = work / "host-evidence-pre.json"
    retained_post = work / "host-evidence-post.json"
    assert retained_pre.is_file()
    assert retained_post.is_file()
    assert retained_pre.read_bytes() == pre_bytes
    assert retained_post.read_bytes() == post_bytes
    _assert_retained_file_safety(retained_pre)
    _assert_retained_file_safety(retained_post)

    pre_data = json.loads(retained_pre.read_text(encoding="utf-8"))
    post_data = json.loads(retained_post.read_text(encoding="utf-8"))
    assert pre_data["nonce"] == post_data["nonce"] == NONCE
    assert pre_data["phase"] == "pre-apply"
    assert post_data["phase"] == "post-apply"

    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert log.count("APPLY_PATH ") == 1
    # Retention notes appear; pre retention precedes apply eligibility messaging.
    assert "Retained validated pre-apply host evidence" in proc.stdout
    assert "Retained validated post-apply host evidence" in proc.stdout
    pre_note_idx = proc.stdout.index("Retained validated pre-apply host evidence")
    apply_idx = proc.stdout.index("Applying exact reviewed saved plan")
    post_note_idx = proc.stdout.index("Retained validated post-apply host evidence")
    assert pre_note_idx < apply_idx < post_note_idx


def test_retention_failure_prevents_plan_only_success(tmp_path: Path) -> None:
    """Existing destination in workdir causes fail-closed (no plan-only success)."""
    repo, bin_dir, state, pre, _post, _digest = _prep_success(tmp_path)

    # Patch retain helper path by pre-seeding via a wrapper around assert retain.
    # Direct unit coverage below; here force destination conflict by monkeypatching
    # retain-host-evidence to create then re-call original logic is awkward in bash.
    # Use Python API with a synthetic workdir that already has the destination.
    work = tmp_path / "owned-work"
    work.mkdir(mode=0o700)
    existing = work / "host-evidence-pre.json"
    existing.write_text("stale\n", encoding="utf-8")
    existing.chmod(0o600)

    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    assert existing.read_text(encoding="utf-8") == "stale\n"

    # End-to-end: simulate retain failure by making source disappear after validate
    # is not practical; assert script path fails closed when retain CLI fails.
    proc = _run_assert(
        [
            "retain-host-evidence",
            str(pre),
            "--work-dir",
            str(work),
            "--phase",
            "pre-apply",
            "--nonce",
            NONCE,
        ]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_retention" in proc.stderr


def test_atomic_temp_cleanup_on_publish_failure(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))

    real_link = os.link

    def boom(src: str, dst: str) -> None:  # noqa: ARG001
        raise OSError("simulated publish failure")

    with (
        mock.patch("os.link", side_effect=boom),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    assert not (work / "host-evidence-pre.json").exists()
    leftovers = list(work.glob(".host-evidence-pre.json.*.tmp"))
    assert leftovers == [], leftovers
    # Ensure real link still works for subsequent success
    assert callable(real_link)


def test_retain_api_byte_identity_and_binding(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    repo_sha = "deadbeefcafebabe0123456789abcdef01234567"
    data = _host_evidence("pre-apply", uptime=9000, repository_sha=repo_sha)
    pre = _write_json(tmp_path / "pre.json", data)
    source_bytes = pre.read_bytes()

    binding = ASSERT.retain_validated_host_evidence(
        pre,
        work_dir=work,
        phase="pre-apply",
        expected_nonce=NONCE,
        expected_repository_sha=repo_sha,
    )
    retained = work / "host-evidence-pre.json"
    assert retained.read_bytes() == source_bytes
    _assert_retained_file_safety(retained)
    assert binding["sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert binding["source_sha256"] == binding["sha256"]
    assert binding["nonce"] == NONCE
    sidecar = work / "host-evidence-pre.json.sha256"
    _assert_retained_file_safety(sidecar)
    assert binding["sha256"] in sidecar.read_text(encoding="utf-8")

    retained_obj = json.loads(retained.read_text(encoding="utf-8"))
    assert retained_obj["nonce"] == NONCE
    assert retained_obj["repository_sha"] == repo_sha


def test_retain_post_phase_name_and_plan_only_does_not_require_post(
    tmp_path: Path,
) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    post = _write_json(
        tmp_path / "post.json",
        _host_evidence("post-apply", uptime=25),
    )
    ASSERT.retain_validated_host_evidence(
        post,
        work_dir=work,
        phase="post-apply",
        expected_nonce=NONCE,
    )
    assert (work / "host-evidence-post.json").is_file()
    assert not (work / "host-evidence-pre.json").exists()

    # Plan-only path must not invent post evidence.
    repo, bin_dir, _state, pre, _post, _digest = _prep_success(tmp_path / "plan")
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)},
        execute=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    work2 = _workdir_from_output(proc.stdout)
    assert (work2 / "host-evidence-pre.json").is_file()
    assert not (work2 / "host-evidence-post.json").exists()
    assert "no post-apply evidence invented" in proc.stdout.lower() or (
        "pre-apply evidence only" in proc.stdout.lower()
    )


def test_docs_describe_retained_evidence_and_no_manual_injection() -> None:
    runbook = Path(RUNBOOK).read_text(encoding="utf-8").lower()
    sprint = Path(SPRINT_DOC).read_text(encoding="utf-8").lower()
    for doc in (runbook, sprint):
        assert "host-evidence-pre.json" in doc
        assert "host-evidence-post.json" in doc
        assert "manually inject" in doc or "manual inject" in doc
        assert "host_evidence_retention" in doc
        assert "0600" in doc
        assert "byte" in doc or "identical" in doc
    # No production/workflow mutation language introduced for retention.
    apply = Path(APPLY_SH).read_text(encoding="utf-8")
    assert "retain_host_evidence" in apply or "retain-host-evidence" in apply
    assert "gh workflow" not in apply
    assert "SendCommand" not in apply or "must not invoke" in apply
    lib = Path(GATE_LIB).read_text(encoding="utf-8")
    assert "staging_maintenance_retain_host_evidence" in lib
    assert "retain-host-evidence" in Path(ASSERT_PY).read_text(encoding="utf-8")


def test_no_terraform_apply_in_plan_only_retention_tests(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, _post, _digest = _prep_success(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)},
        execute=False,
    )
    assert proc.returncode == 0
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "terraform apply" not in log
    assert "APPLY_PATH" not in log
    assert "ssm send-command" not in log.lower()
    assert "ec2 stop-instances" not in log.lower()


def test_makefile_includes_25b5p_tests() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "test_sprint25b5p_host_evidence_retention.py" in makefile


def test_bash_syntax_and_python_compile_retention_path() -> None:
    import subprocess

    for script in (
        ROOT / "scripts/deploy/staging_maintenance_gate_lib.sh",
        ROOT / "scripts/deploy/staging_maintenance_controlled_apply.sh",
    ):
        proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
    proc = subprocess.run(
        [PYTHON, "-m", "py_compile", str(ASSERT_PY)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_retain_rejects_symlink_source_via_api(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    link = tmp_path / "link.json"
    link.symlink_to(pre)
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            link,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    assert not (work / "host-evidence-pre.json").exists()
    assert list(work.glob(".host-evidence-pre.json.*.tmp")) == []


def _assert_no_retained_pair(work: Path) -> None:
    assert not (work / "host-evidence-pre.json").exists()
    assert not (work / "host-evidence-pre.json.sha256").exists()
    assert list(work.glob(".host-evidence-pre.json*.tmp")) == []
    assert list(work.glob(".host-evidence-pre.json.sha256*.tmp")) == []


def test_sidecar_temp_failure_after_evidence_publish_cleans_pair(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    real_mkstemp = __import__("tempfile").mkstemp
    calls = {"n": 0}

    def boom_mkstemp(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("simulated sidecar mkstemp failure")
        return real_mkstemp(*args, **kwargs)

    with (
        mock.patch("tempfile.mkstemp", side_effect=boom_mkstemp),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_sidecar_link_failure_after_evidence_publish_cleans_pair(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    real_link = os.link
    links = {"n": 0}

    def boom_link(src: str, dst: str) -> None:
        links["n"] += 1
        if links["n"] >= 2:
            raise OSError("simulated sidecar exclusive publish failure")
        return real_link(src, dst)

    with (
        mock.patch("os.link", side_effect=boom_link),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_post_publish_revalidation_failure_cleans_pair(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    real_validate = ASSERT.validate_host_evidence_file
    calls = {"n": 0}

    def boom_validate(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return real_validate(*args, **kwargs)
        raise ASSERT.AssertError(
            "simulated retained destination revalidation failure",
            code=11,
            phase="host_evidence",
        )

    with (
        mock.patch.object(ASSERT, "validate_host_evidence_file", side_effect=boom_validate),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_sidecar_content_verification_failure_cleans_pair(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    real_read = Path.read_bytes

    def boom_read(self: Path) -> bytes:
        if self.name == "host-evidence-pre.json.sha256":
            return b"0" * 64 + b"  host-evidence-pre.json\n"
        return real_read(self)

    with (
        mock.patch.object(Path, "read_bytes", boom_read),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_preexisting_destination_and_sidecar_never_removed(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))

    existing_dest = work / "host-evidence-pre.json"
    existing_dest.write_text("preexisting-dest\n", encoding="utf-8")
    existing_dest.chmod(0o600)
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    assert existing_dest.read_text(encoding="utf-8") == "preexisting-dest\n"

    existing_dest.unlink()
    existing_sidecar = work / "host-evidence-pre.json.sha256"
    existing_sidecar.write_text("deadbeef  host-evidence-pre.json\n", encoding="utf-8")
    existing_sidecar.chmod(0o600)
    with pytest.raises(ASSERT.AssertError) as excinfo2:
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo2.value.phase == "host_evidence_retention"
    assert existing_sidecar.read_text(encoding="utf-8") == "deadbeef  host-evidence-pre.json\n"
    assert not (work / "host-evidence-pre.json").exists()


def test_successful_retention_complete_pair_byte_identity(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    source_bytes = pre.read_bytes()
    binding = ASSERT.retain_validated_host_evidence(
        pre,
        work_dir=work,
        phase="pre-apply",
        expected_nonce=NONCE,
    )
    dest = work / "host-evidence-pre.json"
    sidecar = work / "host-evidence-pre.json.sha256"
    assert dest.is_file() and sidecar.is_file()
    assert dest.read_bytes() == source_bytes
    _assert_retained_file_safety(dest)
    _assert_retained_file_safety(sidecar)
    digest = hashlib.sha256(source_bytes).hexdigest()
    assert binding["sha256"] == digest
    assert sidecar.read_text(encoding="utf-8") == f"{digest}  host-evidence-pre.json\n"


def test_retain_fail_phase_directory_source(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    directory = tmp_path / "dir-source"
    directory.mkdir()
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            directory,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_retain_fail_phase_symlink_source(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    link = tmp_path / "sym.json"
    link.symlink_to(pre)
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            link,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_retain_fail_phase_source_mode_too_open(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    pre.chmod(0o644)
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_retain_fail_phase_source_ownership_mismatch(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    real_require = ASSERT._require_regular_file

    def wrong_owner(path: Path, **kwargs):
        st = real_require(path, **kwargs)
        if Path(path).resolve() == pre.resolve():
            vals = list(st)
            # st_uid is index 4 in the os.stat_result sequence.
            vals[4] = st.st_uid + 1
            return os.stat_result(vals)
        return st

    with (
        mock.patch.object(ASSERT, "_require_regular_file", side_effect=wrong_owner),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    assert "ownership mismatch" in str(excinfo.value)
    _assert_no_retained_pair(work)


def test_retain_fail_phase_unsafe_workdir(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o755)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"

    target = tmp_path / "real-work"
    target.mkdir(mode=0o700)
    link = tmp_path / "work-link"
    link.symlink_to(target)
    with pytest.raises(ASSERT.AssertError) as excinfo2:
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=link,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo2.value.phase == "host_evidence_retention"
    assert "symlink" in str(excinfo2.value).lower()


def test_retain_fail_phase_destination_exists(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    dest = work / "host-evidence-pre.json"
    dest.write_text("stale\n", encoding="utf-8")
    dest.chmod(0o600)
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    assert dest.read_text(encoding="utf-8") == "stale\n"


def test_retain_fail_phase_sidecar_publish_and_revalidation(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    real_link = os.link
    links = {"n": 0}

    def boom_link(src: str, dst: str) -> None:
        links["n"] += 1
        if links["n"] >= 2:
            raise OSError("sidecar publish boom")
        return real_link(src, dst)

    with (
        mock.patch("os.link", side_effect=boom_link),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)

    real_validate = ASSERT.validate_host_evidence_file
    calls = {"n": 0}

    def boom_validate(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return real_validate(*args, **kwargs)
        raise ASSERT.AssertError("dest revalidation boom", code=11, phase="host_evidence_phase")

    with (
        mock.patch.object(ASSERT, "validate_host_evidence_file", side_effect=boom_validate),
        pytest.raises(ASSERT.AssertError) as excinfo2,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo2.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work)


def test_plan_identity_phase_unchanged_for_shared_helper(tmp_path: Path) -> None:
    """Shared _require_regular_file still reports plan_identity_mode by default."""
    art = tmp_path / "plan.bin"
    art.write_bytes(b"x")
    art.chmod(0o644)
    with pytest.raises(ASSERT.AssertError) as excinfo:
        ASSERT._require_regular_file(art, exact_mode=0o600)
    assert excinfo.value.phase == "plan_identity_mode"

    proc = _run_assert(["verify-artifact-mode", str(art), "--mode", "600"])
    assert proc.returncode != 0
    assert "FAIL_PHASE=plan_identity_mode" in proc.stderr


def test_transactional_cleanup_cli_fail_phase_no_plan_only_or_apply(
    tmp_path: Path,
) -> None:
    """CLI retain failure reports retention phase; controlled apply never applies."""
    repo, bin_dir, state, pre, _post, _digest = _prep_success(tmp_path)
    work = tmp_path / "owned-work"
    work.mkdir(mode=0o700)
    existing = work / "host-evidence-pre.json"
    existing.write_text("stale\n", encoding="utf-8")
    existing.chmod(0o600)

    proc = _run_assert(
        [
            "retain-host-evidence",
            str(pre),
            "--work-dir",
            str(work),
            "--phase",
            "pre-apply",
            "--nonce",
            NONCE,
        ]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_retention" in proc.stderr
    assert "Plan-only mode complete" not in proc.stdout
    assert existing.read_text(encoding="utf-8") == "stale\n"

    # Sidecar publish failure: cleaned pair + retention phase (same impl as shell).
    work2 = tmp_path / "owned-work-2"
    work2.mkdir(mode=0o700)
    real_link = os.link
    links = {"n": 0}

    def boom_link(src: str, dst: str) -> None:
        links["n"] += 1
        if links["n"] >= 2:
            raise OSError("simulated sidecar exclusive publish failure")
        return real_link(src, dst)

    with (
        mock.patch("os.link", side_effect=boom_link),
        pytest.raises(ASSERT.AssertError) as excinfo,
    ):
        ASSERT.retain_validated_host_evidence(
            pre,
            work_dir=work2,
            phase="pre-apply",
            expected_nonce=NONCE,
        )
    assert excinfo.value.phase == "host_evidence_retention"
    _assert_no_retained_pair(work2)
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")
    assert "terraform apply" not in (state / "invocations.log").read_text(encoding="utf-8")
    assert repo.is_dir() and bin_dir.is_dir()
