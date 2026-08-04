"""Sprint 25b.5r — SSM describe-document JMESPath / DocumentVersion hardening.

Root cause of the post-apply FAIL_PHASE=ssm_document_content_verification on
nonce 3aa762eff054e383694b2e0d1fde93b3 was a permanent bug: top-level JMESPath
projection against nested Document metadata produced DocumentVersion=null,
python printed None, and get-document failed ValidationException. Not a
transient read-after-create condition — so this sprint fixes the query and
fail-closes invalid versions rather than adding get-document retries.
"""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests.unit.test_sprint25b5n_staging_maintenance_gate import (
    ACCOUNT_ID,
    APPLY_SH,
    ASSERT_PY,
    GATE_LIB,
    _apply_gate_env,
    _approved_ssm_content,
    _prep_approved_apply,
    _run_apply,
    _run_assert,
    _write_json,
)

ROOT = Path(__file__).resolve().parents[2]


def _source_version_helper(meta_path: Path) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""\
        set -euo pipefail
        source {GATE_LIB.as_posix()!r}
        staging_maintenance_ssm_document_version_from_meta {meta_path.as_posix()!r}
        """
    )
    return subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_apply_script_uses_document_jmespath_projection() -> None:
    text = APPLY_SH.read_text(encoding="utf-8")
    assert (
        "--query 'Document.{Name:Name,Status:Status,DocumentType:DocumentType,"
        "DocumentVersion:DocumentVersion,DefaultVersion:DefaultVersion,Owner:Owner}'"
        in text
    )
    assert "--query '{Name:Name,Status:Status,DocumentType:DocumentType," not in text
    assert "staging_maintenance_ssm_document_version_from_meta" in text


def test_version_helper_accepts_active_numeric_version(tmp_path: Path) -> None:
    meta = _write_json(
        tmp_path / "meta.json",
        {
            "Name": "DealBrain-StagingRollback",
            "Status": "Active",
            "DocumentType": "Command",
            "DocumentVersion": "1",
            "DefaultVersion": "1",
            "Owner": ACCOUNT_ID,
        },
    )
    proc = _source_version_helper(meta)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "1"


@pytest.mark.parametrize(
    "version",
    [None, "", "None", "null", "01", "0", "v1", "latest", "  "],
)
def test_version_helper_rejects_invalid_versions(tmp_path: Path, version: object) -> None:
    payload = {
        "Name": "DealBrain-StagingRollback",
        "Status": "Active",
        "DocumentType": "Command",
        "DocumentVersion": version,
        "DefaultVersion": "1",
        "Owner": ACCOUNT_ID,
    }
    meta = _write_json(tmp_path / "meta.json", payload)
    proc = _source_version_helper(meta)
    assert proc.returncode != 0
    assert "DocumentVersion" in proc.stderr or "pattern" in proc.stderr.lower()


def test_null_describe_meta_fails_closed_before_get_document(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    _write_json(
        state / "ssm_meta.json",
        {
            "Name": None,
            "Status": None,
            "DocumentType": None,
            "DocumentVersion": None,
            "DefaultVersion": None,
            "Owner": None,
        },
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr
    assert "missing/invalid DocumentVersion" in proc.stderr
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "ssm describe-document" in log
    assert "ssm get-document" not in log
    assert log.count("APPLY_PATH ") == 1
    assert "SendCommand" not in log
    assert "ssm send-command" not in log.lower()
    assert "workflow_dispatch" not in log
    assert not re.search(r"terraform\s+.*-target", log)


def test_first_get_document_succeeds_with_document_jmespath(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "Document.{Name:Name" in log
    get_lines = [ln for ln in log.splitlines() if "ssm get-document" in ln]
    assert len(get_lines) == 1
    assert "--document-version 1" in get_lines[0]
    assert "SendCommand" not in log
    assert log.count("APPLY_PATH ") == 1
    assert "OK ssm document content" in proc.stdout


def test_access_denied_on_get_document_fails_immediately(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    (state / "ssm_get_fail.txt").write_text(
        "An error occurred (AccessDeniedException) when calling the "
        "GetDocument operation: Access Denied\n",
        encoding="utf-8",
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr
    assert "ssm get-document failed" in proc.stderr
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert log.count("ssm get-document") == 1
    assert log.count("APPLY_PATH ") == 1
    assert "SendCommand" not in log


def test_invalid_content_fails_immediately(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    _write_json(
        state / "ssm_content.json",
        {
            "Name": "DealBrain-StagingRollback",
            "Status": "Active",
            "DocumentType": "Command",
            "DocumentVersion": "1",
            "DefaultVersion": "1",
            "Owner": ACCOUNT_ID,
            "content": "{not-json",
        },
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert log.count("ssm get-document") == 1
    assert log.count("APPLY_PATH ") == 1


def test_content_mismatch_fails_immediately(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    bad = _approved_ssm_content()
    bad["mainSteps"][0]["inputs"]["runCommand"][-1] = "exec /tmp/evil.sh"
    _write_json(state / "approved_ssm_content.json", bad)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert log.count("APPLY_PATH ") == 1
    assert "SendCommand" not in log


def test_wrong_document_name_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    _write_json(
        state / "ssm_meta.json",
        {
            "Name": "DealBrain-StagingDeploy",
            "Status": "Active",
            "DocumentType": "Command",
            "DocumentVersion": "1",
            "DefaultVersion": "1",
            "Owner": ACCOUNT_ID,
        },
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr


def test_wrong_document_version_fails(tmp_path: Path) -> None:
    envelope = {
        "Name": "DealBrain-StagingRollback",
        "Status": "Active",
        "DocumentType": "Command",
        "DocumentVersion": "2",
        "DefaultVersion": "1",
        "Owner": ACCOUNT_ID,
        "content": json.dumps(_approved_ssm_content()),
    }
    path = _write_json(tmp_path / "ver.json", envelope)
    proc = _run_assert(["validate-ssm-content", str(path), "--version", "1"])
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr


def test_no_get_document_retry_budget_or_sleep_loop() -> None:
    """Hardening is fail-closed JMESPath/version guard — not get-document retry."""
    apply = APPLY_SH.read_text(encoding="utf-8")
    gate = GATE_LIB.read_text(encoding="utf-8")
    assert "ssm get-document" in apply
    assert "SSM_GET_DOCUMENT_RETRY" not in apply
    assert "SSM_GET_DOCUMENT_RETRY" not in gate
    get_segment = apply.split("aws ssm get-document", 1)[1].split(
        "staging_maintenance_verify_ssm_document", 1
    )[0]
    assert "sleep" not in get_segment
    assert "attempt" not in get_segment.lower()


def test_scripts_still_forbid_sendcommand_and_production_ops() -> None:
    for path in (APPLY_SH, GATE_LIB, ASSERT_PY):
        text = path.read_text(encoding="utf-8")
        assert "ssm send-command" not in text.lower()
        assert "gh workflow run" not in text
        assert "environments/production" not in text or path == ASSERT_PY
    apply = APPLY_SH.read_text(encoding="utf-8")
    assert "Rollback Staging remains unauthorized" in apply
    assert "EXECUTE_MAINTENANCE_APPLY" in apply
