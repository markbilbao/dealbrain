"""Sprint 25b.5n — behavioral staging maintenance apply-gate tests.

Exercises dangerous execution paths with isolated mock binaries/fixtures.
Never invokes real Terraform apply or mutates AWS.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import textwrap
import unittest.mock as mock
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = ROOT / "docs/runbooks/STAGING_ROLLBACK.md"
SPRINT_DOC = ROOT / "docs/SPRINT_25B5N_STAGING_MAINTENANCE_APPLY_GATE.md"
GATE_LIB = ROOT / "scripts/deploy/staging_maintenance_gate_lib.sh"
CAPTURE_SH = ROOT / "scripts/deploy/staging_maintenance_pre_apply_capture.sh"
APPLY_SH = ROOT / "scripts/deploy/staging_maintenance_controlled_apply.sh"
ASSERT_PY = ROOT / "scripts/deploy/staging_maintenance_assert.py"
EC2_MAIN = ROOT / "infra/terraform/modules/ec2/main.tf"
STAGING_MAIN = ROOT / "infra/terraform/environments/staging/main.tf"
PROD_TF = ROOT / "infra/terraform/environments/production"
MAKEFILE = ROOT / "Makefile"
WORKFLOWS = ROOT / ".github/workflows"

INSTANCE_ID = "i-0edd57f32296aa323"
ACCOUNT_ID = "941035169846"
REGION = "us-east-1"
STATE_KEY = "staging/terraform.tfstate"
BACKEND_BUCKET = "dealbrain-terraform-state-941035169846"
WORKSPACE = "default"
ACK = (
    "I authorize temporary staging downtime caused by one EC2 stop/start for "
    "i-0edd57f32296aa323. I do not authorize replacement, destroy, production "
    "changes, or unrelated infrastructure changes."
)
RECOVERY_ACK = (
    "I confirm a backup operator and same-instance recovery procedure are "
    "available for staging instance i-0edd57f32296aa323."
)
BASELINE_RELEASE = "rel-20260802T093246Z-83bfc6c57fd9"
BASELINE_DIGEST = "sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f"
ALB_DNS = "dealbrain-staging-123456789.us-east-1.elb.amazonaws.com"
TG_ARN = f"arn:aws:elasticloadbalancing:{REGION}:{ACCOUNT_ID}:targetgroup/dealbrain-staging/abc123"
BOOT_A = "11111111-1111-1111-1111-111111111111"
BOOT_B = "22222222-2222-2222-2222-222222222222"
NONCE = "a" * 32
APPLY_NONCE = "b" * 32

UV = Path.home() / ".local" / "bin" / "uv"
PYTHON = "python3"


def _ensure_uv_on_path(env: dict[str, str]) -> dict[str, str]:
    """Ensure repository uv is visible to test subprocesses."""
    path_parts = [str(UV.parent), env.get("PATH", "")]
    if UV.is_file():
        env["PATH"] = os.pathsep.join(p for p in path_parts if p)
        env["UV"] = str(UV)
    return env


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _import_assert():
    import importlib.util

    spec = importlib.util.spec_from_file_location("staging_maintenance_assert", ASSERT_PY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ASSERT = _import_assert()


def _approved_allow_policy() -> dict[str, Any]:
    return ASSERT.expected_deploy_allow_policy()


def _approved_deny_policy() -> dict[str, Any]:
    return ASSERT.expected_deploy_deny_policy()


def _approved_ssm_content() -> dict[str, Any]:
    return ASSERT.expected_ssm_document_content()


def _ec2_before_after(*, secondary_change: str | None = None) -> tuple[dict, dict]:
    before: dict[str, Any] = {
        "id": INSTANCE_ID,
        "arn": f"arn:aws:ec2:{REGION}:{ACCOUNT_ID}:instance/{INSTANCE_ID}",
        "ami": "ami-0123456789abcdef0",
        "instance_type": "t3.large",
        "subnet_id": "subnet-aaa",
        "vpc_security_group_ids": ["sg-aaa"],
        "security_groups": [],
        "iam_instance_profile": "dealbrain-staging-api-host",
        "root_block_device": [{"volume_size": 30}],
        "ebs_block_device": [],
        "tags": {"Environment": "staging"},
        "tags_all": {"Environment": "staging"},
        "user_data_replace_on_change": False,
        "user_data_base64": "b2xk",
        "availability_zone": "us-east-1a",
        "private_ip": "10.0.0.10",
        "public_ip": "1.2.3.4",
        "public_dns": "ec2.example",
        "private_dns": "ip-10.internal",
        "password_data": None,
        "primary_network_interface_id": "eni-aaa",
    }
    after = dict(before)
    after["user_data_base64"] = "bmV3"
    if secondary_change:
        after[secondary_change] = "CHANGED"
    return before, after


def _valid_plan(
    *,
    extra_resource: dict | None = None,
    omit_data_read: bool = False,
    extra_data_read: bool = False,
    bad_outputs: bool = False,
    replace_paths: Any = None,
    secondary_change: str | None = None,
    after_unknown: dict | None = None,
    destroy: bool = False,
    replace: bool = False,
) -> dict[str, Any]:
    before, after = _ec2_before_after(secondary_change=secondary_change)
    ec2_actions = ["update"]
    if destroy:
        ec2_actions = ["delete"]
    if replace:
        ec2_actions = ["delete", "create"]
    resources = [
        {
            "address": "module.ssm_rollback_document.aws_ssm_document.staging_rollback",
            "mode": "managed",
            "change": {
                "actions": ["create"],
                "before": None,
                "after": {"name": "DealBrain-StagingRollback"},
            },
        },
        {
            "address": "module.github_deploy_role.aws_iam_role_policy.deploy_allow",
            "mode": "managed",
            "change": {
                "actions": ["update"],
                "before": {"name": "deploy_allow"},
                "after": {"name": "deploy_allow"},
            },
        },
        {
            "address": "module.ec2.aws_instance.api",
            "mode": "managed",
            "change": {
                "actions": ec2_actions,
                "before": before,
                "after": after if not destroy else None,
                "replace_paths": replace_paths,
                "after_unknown": after_unknown or {"public_ip": True},
            },
        },
    ]
    if not omit_data_read:
        resources.append(
            {
                "address": "module.github_deploy_role.data.aws_iam_policy_document.deploy_allow",
                "mode": "data",
                "change": {"actions": ["read"], "before": None, "after": {}},
            }
        )
    if extra_data_read:
        resources.append(
            {
                "address": "module.github_deploy_role.data.aws_iam_policy_document.extra",
                "mode": "data",
                "change": {"actions": ["read"], "before": None, "after": {}},
            }
        )
    if extra_resource:
        resources.append(extra_resource)
    outputs = {
        "ssm_rollback_document_name": {"actions": ["create"]},
        "ssm_rollback_document_arn": {"actions": ["create"]},
    }
    if bad_outputs:
        outputs["alb_dns_name"] = {"actions": ["update"]}
    return {
        "format_version": "1.2",
        "resource_changes": resources,
        "output_changes": outputs,
    }


def _host_evidence(
    phase: str, *, boot_id: str = BOOT_A, uptime: int = 1000, **overrides: Any
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "phase": phase,
        "instance_id": INSTANCE_ID,
        "account_id": ACCOUNT_ID,
        "region": REGION,
        "captured_at": _now(),
        "nonce": NONCE,
        "boot_id": boot_id,
        "uptime_seconds": uptime,
        "cloud_init_status": "done",
        "release_id": BASELINE_RELEASE,
        "image_digest": BASELINE_DIGEST,
        "current_pointer": BASELINE_RELEASE,
        "previous_pointer": "rel-prev-0001",
        "rollback_execution_marker_present": False,
    }
    data.update(overrides)
    return data


def _write_json(path: Path, data: Any, mode: int = 0o600) -> Path:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(mode)
    return path


def _run_assert(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(ASSERT_PY), *args],
        check=False,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Artefact / documentation consistency
# ---------------------------------------------------------------------------


def test_artefacts_exist() -> None:
    for path in (RUNBOOK, SPRINT_DOC, GATE_LIB, CAPTURE_SH, APPLY_SH, ASSERT_PY):
        assert path.is_file(), path


def test_canonical_acknowledgements_exact() -> None:
    lib = _read(GATE_LIB)
    runbook = _read(RUNBOOK)
    sprint = _read(SPRINT_DOC)
    assert f"STAGING_MAINTENANCE_ACK_CANONICAL='{ACK}'" in lib
    assert f"STAGING_MAINTENANCE_RECOVERY_ACK_CANONICAL='{RECOVERY_ACK}'" in lib
    assert "staging_maintenance_normalize_ack" not in lib
    assert "line breaks optional" not in runbook.lower()
    assert "whitespace normalization" in sprint.lower() or "byte-for-byte" in sprint
    assert ACK in runbook
    assert RECOVERY_ACK in runbook
    assert ACK in sprint
    assert RECOVERY_ACK in sprint


def test_no_skip_init_or_health_clear() -> None:
    for path in (APPLY_SH, CAPTURE_SH):
        text = _read(path)
        assert "STAGING_MAINTENANCE_SKIP_INIT" in text  # rejected explicitly
        assert "not permitted" in text
    apply = _read(APPLY_SH)
    assert "STAGING_MAINTENANCE_HEALTH_CLEAR" in apply
    assert "removed" in apply
    assert "mktemp -d" in _read(GATE_LIB)
    assert "set -Eeuo pipefail" in apply
    assert "set -Eeuo pipefail" in _read(CAPTURE_SH)


def test_no_terraform_target_and_no_ignore_changes_workaround() -> None:
    ec2 = _read(EC2_MAIN)
    staging = _read(STAGING_MAIN)
    assert "ignore_changes = [user_data_base64]" not in ec2
    assert 'ignore_changes = ["user_data_base64"]' not in ec2 + staging
    assert "terraform -target is forbidden" in _read(GATE_LIB)
    assert "-target" in _read(APPLY_SH)


def test_makefile_includes_25b5n_tests() -> None:
    makefile = _read(MAKEFILE)
    needle = "tests/unit/test_sprint25b5n_staging_maintenance_gate.py"
    for target in ("validate-staging-deploy:", "validate-pre-live:"):
        after = makefile.split(target, 1)[1].split("\n\n", 1)[0]
        assert needle in after


def test_bash_syntax_maintenance_scripts() -> None:
    for path in (GATE_LIB, CAPTURE_SH, APPLY_SH):
        proc = subprocess.run(
            ["bash", "-n", str(path)], check=False, capture_output=True, text=True
        )
        assert proc.returncode == 0, proc.stderr


def test_no_production_authorization() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").exists()
    prod_main = _read(PROD_TF / "main.tf")
    assert "ssm_rollback" not in prod_main


# ---------------------------------------------------------------------------
# Assert helper behavioral coverage (plan / evidence)
# ---------------------------------------------------------------------------


def test_plan_validator_accepts_expected(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    _write_json(plan, _valid_plan())
    proc = _run_assert(["validate-plan", str(plan)])
    assert proc.returncode == 0, proc.stderr


def test_plan_rejects_extra_resource_missing_read_bad_outputs(tmp_path: Path) -> None:
    cases = [
        _valid_plan(
            extra_resource={
                "address": "module.alb.aws_lb.main",
                "mode": "managed",
                "change": {"actions": ["update"], "before": {}, "after": {}},
            }
        ),
        _valid_plan(omit_data_read=True),
        _valid_plan(extra_data_read=True),
        _valid_plan(bad_outputs=True),
        _valid_plan(replace_paths=[["ami"]]),
        _valid_plan(secondary_change="ami"),
        _valid_plan(after_unknown={"instance_type": True}),
        _valid_plan(destroy=True),
        _valid_plan(replace=True),
    ]
    for idx, data in enumerate(cases):
        path = tmp_path / f"bad-{idx}.json"
        _write_json(path, data)
        proc = _run_assert(["validate-plan", str(path)])
        assert proc.returncode != 0, f"case {idx} unexpectedly passed"


def test_host_evidence_and_compare(tmp_path: Path) -> None:
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=5000))
    post = _write_json(
        tmp_path / "post.json",
        _host_evidence("post-apply", boot_id=BOOT_B, uptime=30),
    )
    assert (
        _run_assert(
            ["validate-host-evidence", str(pre), "--phase", "pre-apply", "--nonce", NONCE]
        ).returncode
        == 0
    )
    assert (
        _run_assert(
            ["validate-host-evidence", str(post), "--phase", "post-apply", "--nonce", NONCE]
        ).returncode
        == 0
    )
    assert _run_assert(["compare-host-evidence", str(pre), str(post)]).returncode == 0

    bad = _write_json(tmp_path / "bad.json", _host_evidence("pre-apply", release_id="nope"))
    assert _run_assert(["validate-host-evidence", str(bad), "--phase", "pre-apply"]).returncode != 0

    mismatch = _write_json(
        tmp_path / "mismatch.json",
        _host_evidence("post-apply", boot_id=BOOT_B, uptime=30, release_id="rel-other-0001"),
    )
    assert _run_assert(["compare-host-evidence", str(pre), str(mismatch)]).returncode != 0


def test_plan_checksum_and_symlink_rejection(tmp_path: Path) -> None:
    plan = tmp_path / "plan.bin"
    plan.write_bytes(b"tfplan-bytes")
    plan.chmod(0o600)
    digest = hashlib.sha256(plan.read_bytes()).hexdigest()
    assert _run_assert(["sha256", str(plan)]).stdout.strip() == digest
    assert _run_assert(["verify-plan-identity", str(plan), "--sha256", digest]).returncode == 0
    assert _run_assert(["verify-plan-identity", str(plan), "--sha256", "0" * 64]).returncode != 0

    link = tmp_path / "plan.link"
    link.symlink_to(plan)
    assert _run_assert(["sha256", str(link)]).returncode != 0

    plan.chmod(0o666)
    assert _run_assert(["verify-plan-identity", str(plan), "--sha256", digest]).returncode != 0


# ---------------------------------------------------------------------------
# Full-script behavioral harness with mocks
# ---------------------------------------------------------------------------


def _install_mocks(bin_dir: Path, state_dir: Path, *, plan_bytes: bytes, plan_json: dict) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "plan.bin").write_bytes(plan_bytes)
    _write_json(state_dir / "plan.json", plan_json)
    (state_dir / "invocations.log").write_text("", encoding="utf-8")
    (state_dir / "aws_mode").write_text("healthy", encoding="utf-8")
    (state_dir / "curl_mode").write_text("ok", encoding="utf-8")
    (state_dir / "account").write_text(ACCOUNT_ID, encoding="utf-8")
    (state_dir / "region").write_text(REGION, encoding="utf-8")
    (state_dir / "backend_bucket").write_text(BACKEND_BUCKET, encoding="utf-8")
    (state_dir / "backend_key").write_text(STATE_KEY, encoding="utf-8")
    (state_dir / "workspace").write_text(WORKSPACE, encoding="utf-8")
    (state_dir / "ec2_state").write_text("running", encoding="utf-8")
    (state_dir / "ec2_system").write_text("ok", encoding="utf-8")
    (state_dir / "ec2_instance").write_text("ok", encoding="utf-8")
    (state_dir / "alb_state").write_text("healthy", encoding="utf-8")
    (state_dir / "post_plan_code").write_text("0", encoding="utf-8")
    (state_dir / "apply_count").write_text("0", encoding="utf-8")
    _write_json(state_dir / "iam_allow.json", _approved_allow_policy())
    _write_json(state_dir / "iam_deny.json", _approved_deny_policy())
    _write_json(state_dir / "approved_ssm_content.json", _approved_ssm_content())

    aws_py = bin_dir / "aws"
    aws_py.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json, os, re, sys
            from pathlib import Path
            state = Path({str(state_dir)!r})
            (state / "invocations.log").open("a").write("aws " + " ".join(sys.argv[1:]) + "\\n")
            args = sys.argv[1:]
            account = (state / "account").read_text().strip()
            region = (state / "region").read_text().strip()
            if args[:2] == ["sts", "get-caller-identity"]:
                if "--query" in args and "Account" in args[args.index("--query")+1]:
                    print(account); raise SystemExit(0)
                print(json.dumps({{
                    "Account": account,
                    "Arn": "arn:aws:iam::" + account + ":user/x",
                }}))
                raise SystemExit(0)
            if args[:2] == ["configure", "get"] and args[2] == "region":
                print(region); raise SystemExit(0)
            if args[:2] == ["ec2", "describe-instances"]:
                state_name = (state / "ec2_state").read_text().strip()
                q = args[args.index("--query") + 1] if "--query" in args else ""
                out = args[args.index("--output") + 1] if "--output" in args else "json"
                if out == "text":
                    if "State.Name" in q:
                        print(state_name)
                    else:
                        print("{INSTANCE_ID}")
                    raise SystemExit(0)
                if "InstanceId" in q and "State" in q:
                    print(json.dumps({{"Id": "{INSTANCE_ID}", "State": state_name}}))
                else:
                    print(json.dumps({{
                        "InstanceId": "{INSTANCE_ID}", "State": state_name,
                        "Az": "us-east-1a", "PrivateIp": "10.0.0.10", "PublicIp": None,
                        "LaunchTime": "2026-01-01T00:00:00+00:00"
                    }}))
                raise SystemExit(0)
            if args[:2] == ["ec2", "describe-instance-status"]:
                q = args[args.index("--query")+1] if "--query" in args else ""
                out = args[args.index("--output")+1] if "--output" in args else "json"
                if "InstanceState" in q and out == "json":
                    print(json.dumps({{
                        "InstanceState": (state/"ec2_state").read_text().strip(),
                        "SystemStatus": (state/"ec2_system").read_text().strip(),
                        "InstanceStatus": (state/"ec2_instance").read_text().strip(),
                    }})); raise SystemExit(0)
                if "SystemStatus.Status" in q:
                    print((state/"ec2_system").read_text().strip()); raise SystemExit(0)
                if "InstanceStatus.Status" in q:
                    print((state/"ec2_instance").read_text().strip()); raise SystemExit(0)
                print("ok"); raise SystemExit(0)
            if args[:2] == ["elbv2", "describe-target-health"]:
                st = (state/"alb_state").read_text().strip()
                print(json.dumps({{"TargetHealthDescriptions":[{{"Target":{{"Id":"{INSTANCE_ID}"}},"TargetHealth":{{"State":st}}}}]}}))
                raise SystemExit(0)
            if args[:2] == ["elbv2", "describe-target-groups"]:
                print(json.dumps({{"TargetGroupArn":"{TG_ARN}","TargetGroupName":"dealbrain-staging","Port":80,"Protocol":"HTTP","VpcId":"vpc-1"}}))
                raise SystemExit(0)
            if args[:2] == ["ssm", "describe-document"]:
                # Simulate real AWS nesting under Document. Apply a minimal
                # JMESPath stand-in for the queries used by the apply gate.
                meta_path = state / "ssm_meta.json"
                if meta_path.is_file():
                    meta = json.loads(meta_path.read_text())
                else:
                    meta = {{
                        "Name":"DealBrain-StagingRollback",
                        "Status":"Active",
                        "DocumentType":"Command",
                        "DocumentVersion":"1",
                        "DefaultVersion":"1",
                        "Owner":"{ACCOUNT_ID}",
                    }}
                q = args[args.index("--query")+1] if "--query" in args else ""
                if q.startswith("Document."):
                    print(json.dumps(meta)); raise SystemExit(0)
                if "Name:Name" in q and "Document." not in q:
                    # Buggy top-level projection against nested Document payload.
                    print(json.dumps({{
                        "Name": None,
                        "Status": None,
                        "DocumentType": None,
                        "DocumentVersion": None,
                        "DefaultVersion": None,
                        "Owner": None,
                    }}))
                    raise SystemExit(0)
                print(json.dumps({{"Document": meta}})); raise SystemExit(0)
            if args[:2] == ["ssm", "get-document"]:
                fail_path = state / "ssm_get_fail.txt"
                if fail_path.is_file():
                    print(fail_path.read_text(), file=sys.stderr)
                    raise SystemExit(254)
                # Reject invalid --document-version the way AWS CLI does.
                if "--document-version" in args:
                    ver = args[args.index("--document-version")+1]
                    if not re.fullmatch(
                        r"([$]LATEST|[$]DEFAULT|[$]APPROVED|[$]PENDING_REVIEW|[1-9][0-9]*)",
                        ver or "",
                    ):
                        print(
                            "aws: [ERROR]: An error occurred (ValidationException) "
                            "when calling the GetDocument operation: Value at "
                            "'documentVersion' failed to satisfy constraint",
                            file=sys.stderr,
                        )
                        raise SystemExit(254)
                content_path = state / "ssm_content.json"
                if content_path.is_file():
                    print(content_path.read_text()); raise SystemExit(0)
                sidecar = state / "approved_ssm_content.json"
                body = (
                    json.loads(sidecar.read_text())
                    if sidecar.is_file()
                    else {{"schemaVersion": "2.2"}}
                )
                print(json.dumps({{
                    "Name":"DealBrain-StagingRollback",
                    "Status":"Active",
                    "DocumentType":"Command",
                    "DocumentVersion":"1",
                    "DefaultVersion":"1",
                    "Owner":"{ACCOUNT_ID}",
                    "content": json.dumps(body),
                }}))
                raise SystemExit(0)
            if args[:2] == ["iam", "get-role-policy"]:
                name = None
                if "--policy-name" in args:
                    name = args[args.index("--policy-name")+1]
                allow_path = state / "iam_allow.json"
                deny_path = state / "iam_deny.json"
                if name and name.endswith("-deny"):
                    print(deny_path.read_text() if deny_path.is_file() else "{{}}")
                else:
                    print(allow_path.read_text() if allow_path.is_file() else "{{}}")
                raise SystemExit(0)
            if args[:2] == ["rds", "describe-db-instances"]:
                print(json.dumps([{{"Id":"dealbrain-staging","Status":"available","Engine":"postgres","MultiAZ":False,"Class":"db.t3.micro"}}]))
                raise SystemExit(0)
            print("unexpected aws", args, file=sys.stderr); raise SystemExit(99)
            """
        ),
        encoding="utf-8",
    )
    aws_py.chmod(0o755)

    tf = bin_dir / "terraform"
    tf.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json, os, shutil, sys
            from pathlib import Path
            state = Path({str(state_dir)!r})
            (state / "invocations.log").open("a").write(
                "terraform " + " ".join(sys.argv[1:]) + "\\n"
            )
            args = sys.argv[1:]
            if args[:1] == ["init"]:
                Path(".terraform").mkdir(exist_ok=True)
                bucket = (state/"backend_bucket").read_text().strip()
                key = (state/"backend_key").read_text().strip()
                Path(".terraform/terraform.tfstate").write_text(json.dumps({{
                    "backend": {{"config": {{"bucket": bucket, "key": key, "region": "{REGION}"}}}}
                }}), encoding="utf-8")
                raise SystemExit(0)
            if args[:2] == ["workspace", "show"]:
                print((state/"workspace").read_text().strip()); raise SystemExit(0)
            if args[:1] == ["plan"]:
                out = None
                for i, a in enumerate(args):
                    if a == "-out" and i + 1 < len(args):
                        out = Path(args[i + 1])
                    elif a.startswith("-out="):
                        out = Path(a.split("=", 1)[1])
                detailed = "-detailed-exitcode" in args
                # post-apply residual?
                if detailed or (out is not None and out.name.startswith("post")):
                    code = int((state/"post_plan_code").read_text().strip() or "0")
                    if out is not None:
                        out.write_bytes(b"post-plan")
                    print("No changes" if code == 0 else "Plan: 1 to add")
                    raise SystemExit(code)
                if out is None:
                    print("plan text"); raise SystemExit(0)
                shutil.copyfile(state/"plan.bin", out)
                print("Plan: 1 to add, 2 to change")
                raise SystemExit(0)
            if args[:1] == ["show"]:
                target = Path(args[-1])
                if "-json" in args:
                    if target.name.startswith("post"):
                        print(json.dumps({{"resource_changes":[{{"address":"module.alb.aws_lb.x","mode":"managed","change":{{"actions":["update"]}}}}],"output_changes":{{}}}}))
                    else:
                        print((state/"plan.json").read_text())
                    raise SystemExit(0)
                print("Terraform will perform the following actions")
                raise SystemExit(0)
            if args[:1] == ["apply"]:
                stale = state / "stale_plan"
                if stale.is_file() and stale.read_text().strip() == "1":
                    print(
                        "Error: Saved plan is stale — please run plan again",
                        file=sys.stderr,
                    )
                    raise SystemExit(1)
                count = int((state/"apply_count").read_text().strip() or "0")
                count += 1
                (state/"apply_count").write_text(str(count), encoding="utf-8")
                (state/"invocations.log").open("a").write("APPLY_PATH " + args[-1] + "\\n")
                print("Apply complete")
                raise SystemExit(0)
            if args[:1] == ["output"]:
                raw = "-raw" in args
                name = args[-1]
                values = {{
                    "alb_target_group_arn": "{TG_ARN}",
                    "alb_dns_name": "{ALB_DNS}",
                    "ssm_rollback_document_name": "DealBrain-StagingRollback",
                    "ssm_rollback_document_arn": (
                        "arn:aws:ssm:{REGION}:{ACCOUNT_ID}:document/"
                        "DealBrain-StagingRollback"
                    ),
                }}
                print(values[name]); raise SystemExit(0)
            print("unexpected terraform", args, file=sys.stderr); raise SystemExit(99)
            """
        ),
        encoding="utf-8",
    )
    tf.chmod(0o755)

    curl = bin_dir / "curl"
    curl.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import sys
            from pathlib import Path
            state = Path({str(state_dir)!r})
            (state / "invocations.log").open("a").write("curl " + " ".join(sys.argv[1:]) + "\\n")
            mode = (state/"curl_mode").read_text().strip()
            url = sys.argv[-1]
            if "{ALB_DNS}" not in url:
                print("bad host", file=sys.stderr); raise SystemExit(2)
            if mode != "ok":
                if "-w" in sys.argv:
                    sys.stdout.write("503")
                raise SystemExit(0)
            if "-w" in sys.argv:
                sys.stdout.write("200")
            raise SystemExit(0)
            """
        ),
        encoding="utf-8",
    )
    curl.chmod(0o755)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts" / "deploy").mkdir(parents=True)
    (repo / "infra" / "terraform" / "environments" / "staging").mkdir(parents=True)
    for src in (GATE_LIB, CAPTURE_SH, APPLY_SH, ASSERT_PY):
        shutil.copy2(src, repo / "scripts" / "deploy" / src.name)
    # Deterministic nonce for harness: plan-only and apply use distinct nonces.
    assert_py = repo / "scripts" / "deploy" / "staging_maintenance_assert.py"
    text = assert_py.read_text(encoding="utf-8")
    text = text.replace(
        "def generate_nonce() -> str:\n"
        '    """Return a cryptographically strong 32-hex-char run nonce."""\n'
        "    nonce = secrets.token_hex(16)\n",
        "def generate_nonce() -> str:\n"
        '    """Return a cryptographically strong 32-hex-char run nonce."""\n'
        "    import os as _os\n"
        f"    nonce = {APPLY_NONCE!r} if _os.environ.get('EXECUTE_MAINTENANCE_APPLY') == '1' "
        f"else {NONCE!r}  # test harness fixed nonces\n"
        "    if False:\n"
        "        nonce = secrets.token_hex(16)\n",
    )
    assert_py.write_text(text, encoding="utf-8")
    (repo / "infra" / "terraform" / "environments" / "staging" / "main.tf").write_text(
        'terraform {\n  backend "s3" {}\n}\n',
        encoding="utf-8",
    )
    (repo / ".gitignore").write_text(".terraform/\n*.tfstate\n*.tfplan\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo, check=True, capture_output=True)
    # local remote synchronized with main
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
    subprocess.run(
        ["git", "push", "-u", "origin", "main"], cwd=repo, check=True, capture_output=True
    )
    return repo


def _run_apply(
    repo: Path,
    bin_dir: Path,
    env_extra: dict[str, str] | None = None,
    *,
    execute: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env = _ensure_uv_on_path(env)
    env["STAGING_MAINTENANCE_REPO_ROOT"] = str(repo)
    env["AWS_DEFAULT_REGION"] = REGION
    env["STAGING_MAINTENANCE_POLL_SECONDS"] = "0"
    env["STAGING_MAINTENANCE_EC2_ATTEMPTS"] = "2"
    env["STAGING_MAINTENANCE_ALB_ATTEMPTS"] = "2"
    env["STAGING_MAINTENANCE_EVIDENCE_WAIT_SECONDS"] = "0"
    # Caller-supplied nonce must be rejected; do not set STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE.
    env.pop("STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE", None)
    if execute:
        env["EXECUTE_MAINTENANCE_APPLY"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(repo / "scripts/deploy/staging_maintenance_controlled_apply.sh")],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _workdir_from_output(proc_stdout: str) -> Path:
    match = re.search(r"work_dir=(\S+)", proc_stdout)
    assert match, f"work_dir not found in output:\n{proc_stdout}"
    work = Path(match.group(1))
    assert work.is_dir(), work
    return work


def _prep_success(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path, str]:
    repo = _make_repo(tmp_path)
    state = tmp_path / "mockstate"
    bin_dir = tmp_path / "bin"
    plan_json = _valid_plan()
    plan_bytes = b"REVIEWED-PLAN-BYTES-v1"
    _install_mocks(bin_dir, state, plan_bytes=plan_bytes, plan_json=plan_json)
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    post = _write_json(
        tmp_path / "post.json",
        _host_evidence("post-apply", boot_id=BOOT_B, uptime=25),
    )
    digest = hashlib.sha256(plan_bytes).hexdigest()
    return repo, bin_dir, state, pre, post, digest


def _prep_approved_apply(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Path, Path, str]:
    """Plan-only then return apply-ready fixtures bound to the audited workdir."""
    repo, bin_dir, state, pre, _post, digest = _prep_success(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)},
        execute=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    approved = _workdir_from_output(proc.stdout)
    # Clear invocations so apply-path assertions measure the apply run only.
    (state / "invocations.log").write_text("", encoding="utf-8")
    (state / "apply_count").write_text("0", encoding="utf-8")
    pre_apply = _write_json(
        tmp_path / "pre-apply-run.json",
        _host_evidence("pre-apply", nonce=APPLY_NONCE, uptime=9000),
    )
    post_apply = _write_json(
        tmp_path / "post-apply-run.json",
        _host_evidence("post-apply", nonce=APPLY_NONCE, boot_id=BOOT_B, uptime=25),
    )
    return repo, bin_dir, state, approved, pre_apply, post_apply, digest


def _apply_gate_env(
    approved: Path,
    pre: Path,
    post: Path,
    digest: str,
    **extra: str,
) -> dict[str, str]:
    env = {
        "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR": str(approved),
        "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
        "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post),
        "STAGING_MAINTENANCE_ACK": ACK,
        "STAGING_MAINTENANCE_RECOVERY_ACK": RECOVERY_ACK,
        "STAGING_MAINTENANCE_DEMO_CLEAR": "1",
        "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM": digest,
    }
    env.update(extra)
    return env


def test_default_mode_never_calls_terraform_apply(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post),
        },
        execute=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "terraform apply" not in log
    assert "APPLY_PATH" not in log
    assert "Plan-only mode complete" in proc.stdout


def test_execute_alone_cannot_apply(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {
            "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR": str(approved),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post),
            # missing ACK/recovery/demo/checksum
        },
        execute=True,
    )
    assert proc.returncode != 0
    assert "terraform apply" not in (state / "invocations.log").read_text(encoding="utf-8")
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "ack",
    [
        ACK + " ",
        " " + ACK,
        ACK.replace(" ", "  ", 1),
        ACK + "\n",
        ACK.replace("authorize", "Authorize", 1),
        "prefix " + ACK,
        ACK + " suffix",
    ],
)
def test_ack_must_be_exact(tmp_path: Path, ack: str) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {
            **_apply_gate_env(approved, pre, post, digest),
            "STAGING_MAINTENANCE_ACK": ack,
        },
        execute=True,
    )
    assert proc.returncode != 0
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")


def test_missing_demo_and_recovery_fail(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "demo")
    base = {
        "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR": str(approved),
        "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
        "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post),
        "STAGING_MAINTENANCE_ACK": ACK,
        "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM": digest,
    }
    proc = _run_apply(
        repo, bin_dir, {**base, "STAGING_MAINTENANCE_RECOVERY_ACK": RECOVERY_ACK}, execute=True
    )
    assert proc.returncode != 0
    assert "DEMO_CLEAR" in proc.stderr

    repo2, bin_dir2, state2, approved2, pre2, post2, digest2 = _prep_approved_apply(
        tmp_path / "recovery"
    )
    proc = _run_apply(
        repo2,
        bin_dir2,
        {
            "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR": str(approved2),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre2),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post2),
            "STAGING_MAINTENANCE_ACK": ACK,
            "STAGING_MAINTENANCE_DEMO_CLEAR": "1",
            "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM": digest2,
        },
        execute=True,
    )
    assert proc.returncode != 0
    assert "RECOVERY_ACK" in proc.stderr


@pytest.mark.parametrize(
    "field,value,needle",
    [
        ("account", "000000000000", "account"),
        ("region", "us-west-2", "region"),
        ("backend_bucket", "wrong-bucket", "bucket"),
        ("backend_key", "production/terraform.tfstate", "state key"),
        ("workspace", "prod", "workspace"),
        ("ec2_state", "stopped", "running"),
        ("ec2_system", "impaired", "system"),
        ("ec2_instance", "impaired", "instance"),
        ("alb_state", "unhealthy", "healthy"),
        ("curl_mode", "fail", "live"),
    ],
)
def test_identity_and_health_failures(tmp_path: Path, field: str, value: str, needle: str) -> None:
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path)
    (state / field).write_text(value, encoding="utf-8")
    proc = _run_apply(
        repo,
        bin_dir,
        {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)},
        execute=False,
    )
    assert proc.returncode != 0
    assert needle.lower() in (proc.stderr + proc.stdout).lower()


def test_wrong_instance_in_evidence_fails(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path)
    bad = _write_json(
        tmp_path / "badpre.json", _host_evidence("pre-apply", instance_id="i-deadbeef")
    )
    proc = _run_apply(
        repo, bin_dir, {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(bad)}, execute=False
    )
    assert proc.returncode != 0
    assert (
        "host evidence" in (proc.stderr + proc.stdout).lower() or "instance" in proc.stderr.lower()
    )


def test_dirty_and_unsynced_repo_fail(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path)
    (repo / "dirt.txt").write_text("x", encoding="utf-8")
    proc = _run_apply(
        repo, bin_dir, {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)}, execute=False
    )
    assert proc.returncode != 0
    assert "clean" in proc.stderr.lower()
    (repo / "dirt.txt").unlink()
    # unsynced: commit ahead of origin
    (repo / "ahead.txt").write_text("y", encoding="utf-8")
    subprocess.run(["git", "add", "ahead.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "ahead"], cwd=repo, check=True, capture_output=True)
    proc = _run_apply(
        repo, bin_dir, {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre)}, execute=False
    )
    assert proc.returncode != 0
    assert "origin/main" in proc.stderr or "synchronized" in proc.stderr


def test_missing_host_fields_fail(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path)
    for key in ("cloud_init_status", "release_id", "image_digest"):
        data = _host_evidence("pre-apply")
        data.pop(key)
        path = _write_json(tmp_path / f"missing-{key}.json", data)
        proc = _run_apply(
            repo, bin_dir, {"STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(path)}, execute=False
        )
        assert proc.returncode != 0, key


def test_changed_checksum_symlink_unsafe_perms(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    # wrong checksum
    proc = _run_apply(
        repo,
        bin_dir,
        {
            **_apply_gate_env(approved, pre, post, digest),
            "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM": "f" * 64,
        },
        execute=True,
    )
    assert proc.returncode != 0
    assert "checksum" in proc.stderr.lower() or "CHECKSUM" in proc.stderr
    assert "APPLY_PATH" not in (state / "invocations.log").read_text(encoding="utf-8")

    # symlink plan file via assert helper already covered; unsafe perms on evidence
    pre.chmod(0o666)
    # world-writable is rejected only for group/other write in verify — 0666 has other write
    proc = _run_assert(
        ["validate-host-evidence", str(pre), "--phase", "pre-apply", "--nonce", NONCE]
    )
    assert proc.returncode != 0


def test_post_apply_timeouts_and_integrity_fail(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    base = {
        **_apply_gate_env(approved, pre, post, digest),
        "STAGING_MAINTENANCE_EC2_ATTEMPTS": "1",
        "STAGING_MAINTENANCE_ALB_ATTEMPTS": "1",
    }

    # Patch terraform apply mock to mark ec2 stopped for subsequent polls.
    tf = bin_dir / "terraform"
    tf_text = tf.read_text(encoding="utf-8")
    tf.write_text(
        tf_text.replace(
            'print("Apply complete")',
            f'Path({str(state)!r},"ec2_state").write_text("stopped"); print("Apply complete")',
        ),
        encoding="utf-8",
    )
    proc = _run_apply(repo, bin_dir, base, execute=True)
    assert proc.returncode != 0
    assert "FAIL_PHASE=ec2_recovery_timeout" in proc.stderr

    # reset mocks for ALB timeout
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "alb")
    tf = bin_dir / "terraform"
    tf.write_text(
        tf.read_text(encoding="utf-8").replace(
            'print("Apply complete")',
            f'Path({str(state)!r},"alb_state").write_text("unhealthy"); print("Apply complete")',
        ),
        encoding="utf-8",
    )
    base = {
        **_apply_gate_env(approved, pre, post, digest),
        "STAGING_MAINTENANCE_EC2_ATTEMPTS": "1",
        "STAGING_MAINTENANCE_ALB_ATTEMPTS": "1",
    }
    proc = _run_apply(repo, bin_dir, base, execute=True)
    assert proc.returncode != 0
    assert "FAIL_PHASE=alb_recovery_timeout" in proc.stderr


def test_post_live_ready_release_digest_pointer_cloudinit_drift(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    base = _apply_gate_env(approved, pre, post, digest)

    # /live failure after apply
    tf = bin_dir / "terraform"
    tf.write_text(
        tf.read_text(encoding="utf-8").replace(
            'print("Apply complete")',
            f'Path({str(state)!r},"curl_mode").write_text("fail"); print("Apply complete")',
        ),
        encoding="utf-8",
    )
    post_ok = _write_json(
        tmp_path / "post1.json",
        _host_evidence("post-apply", nonce=APPLY_NONCE, boot_id=BOOT_B, uptime=20),
    )
    proc = _run_apply(
        repo,
        bin_dir,
        {**base, "STAGING_MAINTENANCE_HOST_EVIDENCE_POST": str(post_ok)},
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=application_health" in proc.stderr

    # release mismatch
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "rel")
    bad_post = _write_json(
        tmp_path / "rel" / "badpost.json",
        _host_evidence(
            "post-apply",
            nonce=APPLY_NONCE,
            boot_id=BOOT_B,
            uptime=20,
            release_id="rel-other-9999",
        ),
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, bad_post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=release_integrity" in proc.stderr or "release" in proc.stderr.lower()

    # digest mismatch
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "dig")
    bad_post = _write_json(
        tmp_path / "dig" / "badpost.json",
        _host_evidence(
            "post-apply",
            nonce=APPLY_NONCE,
            boot_id=BOOT_B,
            uptime=20,
            image_digest="sha256:" + "ab" * 32,
        ),
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, bad_post, digest),
        execute=True,
    )
    assert proc.returncode != 0

    # pointer mismatch
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "ptr")
    bad_post = _write_json(
        tmp_path / "ptr" / "badpost.json",
        _host_evidence(
            "post-apply",
            nonce=APPLY_NONCE,
            boot_id=BOOT_B,
            uptime=20,
            current_pointer="rel-other-0002",
        ),
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, bad_post, digest),
        execute=True,
    )
    assert proc.returncode != 0

    # cloud-init error
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "ci")
    bad_post = _write_json(
        tmp_path / "ci" / "badpost.json",
        _host_evidence(
            "post-apply",
            nonce=APPLY_NONCE,
            boot_id=BOOT_B,
            uptime=20,
            cloud_init_status="error",
        ),
    )
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, bad_post, digest),
        execute=True,
    )
    assert proc.returncode != 0

    # missing post evidence
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "miss")
    proc = _run_apply(
        repo,
        bin_dir,
        {
            "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR": str(approved),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
            "STAGING_MAINTENANCE_ACK": ACK,
            "STAGING_MAINTENANCE_RECOVERY_ACK": RECOVERY_ACK,
            "STAGING_MAINTENANCE_DEMO_CLEAR": "1",
            "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM": digest,
        },
        execute=True,
    )
    assert proc.returncode != 0
    assert "HOST_EVIDENCE_POST" in proc.stderr or "host evidence" in proc.stderr.lower()

    # post-plan drift
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "drift")
    (state / "post_plan_code").write_text("2", encoding="utf-8")
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=post_plan_drift" in proc.stderr


def test_successful_mocked_path_applies_once_and_stops(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert log.count("APPLY_PATH ") == 1
    assert (state / "apply_count").read_text(encoding="utf-8").strip() == "1"
    assert "STOP before Deploy Staging" in proc.stdout
    assert "Deploy Staging" in proc.stdout
    assert "Rollback Staging remains unauthorized" in proc.stdout
    assert "HOST_EVIDENCE_RUN_NONCE=" + APPLY_NONCE in proc.stdout
    assert str(approved / "staging-combined.tfplan") in log
    assert "Using exact independently audited plan" in proc.stdout
    # Apply mode must not regenerate the maintenance plan (post residual plan is ok).
    maint_plans = [
        line
        for line in log.splitlines()
        if line.startswith("terraform plan") and "-detailed-exitcode" not in line
    ]
    assert maint_plans == []
    assert "workflow_dispatch" not in log
    assert "Rollback Staging" not in log
    assert "rollback.yml" not in log
    assert "terraform apply" in log or "APPLY_PATH" in log
    assert "iam get-role-policy" in log
    assert "ssm get-document" in log
    assert "ssm describe-document" in log
    assert "SendCommand" not in log
    assert not re.search(r"terraform\s+.*-target", log)
    assert "ignore_changes" not in log
    assert "OK IAM policy verification" in proc.stdout or "iam" in proc.stdout.lower()
    assert "OK ssm document content" in proc.stdout


def test_skip_init_rejected(tmp_path: Path) -> None:
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path)
    proc = _run_apply(
        repo,
        bin_dir,
        {
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
            "STAGING_MAINTENANCE_SKIP_INIT": "1",
        },
        execute=False,
    )
    assert proc.returncode != 0
    assert "SKIP_INIT" in proc.stderr


def test_no_rollback_or_target_in_scripts() -> None:
    for path in (APPLY_SH, CAPTURE_SH, GATE_LIB):
        text = _read(path)
        assert not re.search(r"^\s*terraform\s+apply\b.*-target", text, re.M)
        assert "ignore_changes = [user_data_base64]" not in text
    apply = _read(APPLY_SH)
    assert "Rollback Staging" in apply  # unauthorized messaging only
    assert "workflow_dispatch" not in apply
    assert "gh workflow" not in apply


# ---------------------------------------------------------------------------
# Sprint 25b.5n.2 — MEDIUM-gap behavioral coverage
# ---------------------------------------------------------------------------


def test_automatic_nonce_binding_and_mismatches(tmp_path: Path) -> None:
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path)
    # 1/2: generated apply nonce used and required for pre/post success path
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert f"HOST_EVIDENCE_RUN_NONCE={APPLY_NONCE}" in proc.stdout
    assert APPLY_NONCE != NONCE

    # 3: pre/post nonce mismatch
    bad_post = _write_json(
        tmp_path / "bad-nonce-post.json",
        _host_evidence("post-apply", boot_id=BOOT_B, uptime=20, nonce="c" * 32),
    )
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "mm")
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, bad_post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_nonce" in proc.stderr

    # 4: caller-supplied alternate nonce rejected
    repo, bin_dir, state, pre, post, digest = _prep_success(tmp_path / "caller")
    proc = _run_apply(
        repo,
        bin_dir,
        {
            "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE": str(pre),
            "STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE": "c" * 32,
        },
        execute=False,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_nonce" in proc.stderr


def test_host_evidence_phase_stale_swap_and_pointers(tmp_path: Path) -> None:
    # 5: wrong phase
    wrong = _write_json(tmp_path / "phase.json", _host_evidence("post-apply"))
    proc = _run_assert(
        ["validate-host-evidence", str(wrong), "--phase", "pre-apply", "--nonce", NONCE]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_phase" in proc.stderr

    # 6: stale evidence
    stale = _host_evidence("pre-apply")
    stale["captured_at"] = "2020-01-01T00:00:00Z"
    path = _write_json(tmp_path / "stale.json", stale)
    proc = _run_assert(
        [
            "validate-host-evidence",
            str(path),
            "--phase",
            "pre-apply",
            "--nonce",
            NONCE,
            "--max-age-seconds",
            "60",
        ]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_stale" in proc.stderr

    # 7: pre reused as post
    pre = _write_json(tmp_path / "pre.json", _host_evidence("pre-apply", uptime=9000))
    proc = _run_assert(
        ["validate-host-evidence", str(pre), "--phase", "post-apply", "--nonce", NONCE]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_phase" in proc.stderr

    # 8: post reused as pre
    post = _write_json(
        tmp_path / "post.json", _host_evidence("post-apply", boot_id=BOOT_B, uptime=20)
    )
    proc = _run_assert(
        ["validate-host-evidence", str(post), "--phase", "pre-apply", "--nonce", NONCE]
    )
    assert proc.returncode != 0

    # 9: another run nonce
    other = _write_json(tmp_path / "other.json", _host_evidence("pre-apply", nonce="d" * 32))
    proc = _run_assert(
        ["validate-host-evidence", str(other), "--phase", "pre-apply", "--nonce", NONCE]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=host_evidence_nonce" in proc.stderr

    # 10: missing previous pointer
    missing = _host_evidence("pre-apply")
    del missing["previous_pointer"]
    path = _write_json(tmp_path / "noprev.json", missing)
    proc = _run_assert(
        ["validate-host-evidence", str(path), "--phase", "pre-apply", "--nonce", NONCE]
    )
    assert proc.returncode != 0

    # 11: previous-pointer mismatch across compare
    pre = _write_json(tmp_path / "pre2.json", _host_evidence("pre-apply", uptime=9000))
    bad = _write_json(
        tmp_path / "post2.json",
        _host_evidence(
            "post-apply",
            boot_id=BOOT_B,
            uptime=20,
            previous_pointer="rel-other-prev-9",
        ),
    )
    proc = _run_assert(["compare-host-evidence", str(pre), str(bad), "--nonce", NONCE])
    assert proc.returncode != 0


def test_iam_policy_structural_rejections(tmp_path: Path) -> None:
    base = _approved_allow_policy()

    def _mutate(mutator) -> Path:
        policy = json.loads(json.dumps(base))
        mutator(policy)
        return _write_json(tmp_path / f"iam-{mutator.__name__}.json", policy)

    def passrole(p):
        p["Statement"].append(
            {
                "Sid": "EvilPass",
                "Effect": "Allow",
                "Action": ["iam:PassRole"],
                "Resource": ["*"],
            }
        )

    def iam_star(p):
        p["Statement"].append(
            {"Sid": "EvilIam", "Effect": "Allow", "Action": ["iam:*"], "Resource": ["*"]}
        )

    def action_star(p):
        p["Statement"].append(
            {"Sid": "EvilStar", "Effect": "Allow", "Action": ["*"], "Resource": ["*"]}
        )

    def prod_arn(p):
        for s in p["Statement"]:
            if s["Sid"] == "SendCommandApprovedDocument":
                s["Resource"] = [
                    f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:document/DealBrain-ProductionDeploy"
                ]

    def wrong_account(p):
        for s in p["Statement"]:
            if s["Sid"] == "SendCommandApprovedDocument":
                s["Resource"] = [
                    f"arn:aws:ssm:{REGION}:000000000000:document/DealBrain-StagingDeploy",
                    f"arn:aws:ssm:{REGION}:000000000000:document/DealBrain-StagingRollback",
                ]

    def unexpected_ssm(p):
        for s in p["Statement"]:
            if s["Sid"] == "SendCommandApprovedDocument":
                s["Resource"].append(
                    f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:document/AWS-RunShellScript"
                )

    def unexpected_ec2(p):
        for s in p["Statement"]:
            if s["Sid"] == "SendCommandEnvironmentTaggedInstances":
                s["Resource"] = [f"arn:aws:ec2:{REGION}:{ACCOUNT_ID}:instance/i-deadbeef"]

    def unexpected_s3(p):
        for s in p["Statement"]:
            if s["Sid"] == "ReleaseArtifactsObjectAccess":
                s["Resource"] = ["arn:aws:s3:::other-bucket/releases/*"]

    def missing_deploy(p):
        for s in p["Statement"]:
            if s["Sid"] == "SendCommandApprovedDocument":
                s["Resource"] = [
                    f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:document/DealBrain-StagingRollback"
                ]

    def missing_rollback(p):
        for s in p["Statement"]:
            if s["Sid"] == "SendCommandApprovedDocument":
                s["Resource"] = [
                    f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:document/DealBrain-StagingDeploy"
                ]

    def unexpected_stmt(p):
        p["Statement"].append(
            {
                "Sid": "Extra",
                "Effect": "Allow",
                "Action": ["ec2:DescribeInstances"],
                "Resource": ["*"],
            }
        )

    cases = [
        passrole,
        iam_star,
        action_star,
        prod_arn,
        wrong_account,
        unexpected_ssm,
        unexpected_ec2,
        unexpected_s3,
        missing_deploy,
        missing_rollback,
        unexpected_stmt,
    ]
    for mutator in cases:
        path = _mutate(mutator)
        deny = _write_json(tmp_path / f"deny-{mutator.__name__}.json", _approved_deny_policy())
        proc = _run_assert(["validate-iam-allowlist", str(path), "--deny-path", str(deny)])
        assert proc.returncode != 0, mutator.__name__
        assert "FAIL_PHASE=iam_policy_verification" in proc.stderr

    # 23: approved canonical passes despite statement ordering
    shuffled = _approved_allow_policy()
    shuffled["Statement"] = list(reversed(shuffled["Statement"]))
    path = _write_json(tmp_path / "shuf.json", shuffled)
    deny = _write_json(tmp_path / "deny-ok.json", _approved_deny_policy())
    proc = _run_assert(["validate-iam-allowlist", str(path), "--deny-path", str(deny)])
    assert proc.returncode == 0, proc.stderr


def test_ssm_content_structural_rejections(tmp_path: Path) -> None:
    base = _approved_ssm_content()

    def _wrap(content: dict) -> Path:
        return _write_json(
            tmp_path / "ssm.json",
            {
                "Name": "DealBrain-StagingRollback",
                "Status": "Active",
                "DocumentType": "Command",
                "DocumentVersion": "1",
                "DefaultVersion": "1",
                "Owner": ACCOUNT_ID,
                "content": json.dumps(content),
            },
        )

    # 24 wrong entrypoint
    c = json.loads(json.dumps(base))
    c["mainSteps"][0]["inputs"]["runCommand"][-1] = "exec /tmp/evil.sh"
    assert _run_assert(["validate-ssm-content", str(_wrap(c))]).returncode != 0

    # 25 free-form command parameter
    c = json.loads(json.dumps(base))
    c["parameters"]["commands"] = {"type": "String", "allowedPattern": ".*"}
    assert _run_assert(["validate-ssm-content", str(_wrap(c))]).returncode != 0

    # 26 altered allowedPattern
    c = json.loads(json.dumps(base))
    c["parameters"]["ReleaseId"]["allowedPattern"] = ".*"
    assert _run_assert(["validate-ssm-content", str(_wrap(c))]).returncode != 0

    # 27 missing timeout
    c = json.loads(json.dumps(base))
    del c["mainSteps"][0]["inputs"]["timeoutSeconds"]
    assert _run_assert(["validate-ssm-content", str(_wrap(c))]).returncode != 0

    # 28 excessive timeout
    c = json.loads(json.dumps(base))
    c["mainSteps"][0]["inputs"]["timeoutSeconds"] = "99999"
    assert _run_assert(["validate-ssm-content", str(_wrap(c))]).returncode != 0

    # 29 extra execution step
    c = json.loads(json.dumps(base))
    c["mainSteps"].append({"action": "aws:runShellScript", "name": "Extra", "inputs": {}})
    assert _run_assert(["validate-ssm-content", str(_wrap(c))]).returncode != 0

    # 30 production identifier
    c = json.loads(json.dumps(base))
    c["description"] = "production rollback"
    proc = _run_assert(["validate-ssm-content", str(_wrap(c))])
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr

    # 31 wrong active/default version
    envelope = {
        "Name": "DealBrain-StagingRollback",
        "Status": "Active",
        "DocumentType": "Command",
        "DocumentVersion": "2",
        "DefaultVersion": "1",
        "Owner": ACCOUNT_ID,
        "content": json.dumps(base),
    }
    path = _write_json(tmp_path / "ver.json", envelope)
    assert _run_assert(["validate-ssm-content", str(path), "--version", "1"]).returncode != 0

    # 32 malformed content JSON
    path = _write_json(
        tmp_path / "mal.json",
        {
            "Name": "DealBrain-StagingRollback",
            "Status": "Active",
            "content": "{not-json",
        },
    )
    assert _run_assert(["validate-ssm-content", str(path)]).returncode != 0

    # 33 approved canonical passes despite key ordering
    # json.dumps with different key order still parses to same structure
    raw = json.loads(json.dumps(base, sort_keys=False))
    # reverse parameter key insertion via rebuild
    params = raw["parameters"]
    raw["parameters"] = {k: params[k] for k in reversed(list(params))}
    assert _run_assert(["validate-ssm-content", str(_wrap(raw))]).returncode == 0


def test_plan_identity_owner_mode_and_toctou(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    work.chmod(0o700)
    plan = work / "plan.bin"
    plan.write_bytes(b"PLAN-BYTES")
    plan.chmod(0o600)

    # record identity
    proc = _run_assert(
        ["record-plan-identity", str(plan), "--work-dir", str(work), "--out", str(work / "id.json")]
    )
    assert proc.returncode == 0, proc.stderr
    identity = json.loads((work / "id.json").read_text(encoding="utf-8"))

    # 34/35 wrong uid/gid via identity mismatch
    bad = dict(identity)
    bad["uid"] = identity["uid"] + 1
    _write_json(work / "bad-uid.json", bad)
    proc = _run_assert(
        [
            "verify-plan-identity",
            str(plan),
            "--identity-file",
            str(work / "bad-uid.json"),
            "--work-dir",
            str(work),
        ]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=plan_identity_owner" in proc.stderr

    bad = dict(identity)
    bad["gid"] = identity["gid"] + 1
    _write_json(work / "bad-gid.json", bad)
    proc = _run_assert(
        [
            "verify-plan-identity",
            str(plan),
            "--identity-file",
            str(work / "bad-gid.json"),
            "--work-dir",
            str(work),
        ]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=plan_identity_owner" in proc.stderr

    # 36-40 mode failures
    for mode in (0o604, 0o640, 0o644, 0o660, 0o666):
        plan.chmod(mode)
        proc = _run_assert(
            [
                "verify-plan-identity",
                str(plan),
                "--identity-file",
                str(work / "id.json"),
                "--work-dir",
                str(work),
            ]
        )
        assert proc.returncode != 0, oct(mode)
        assert "FAIL_PHASE=plan_identity_mode" in proc.stderr
    plan.chmod(0o600)

    # 41 inode substitution
    bad = dict(identity)
    bad["inode"] = identity["inode"] + 999
    _write_json(work / "bad-ino.json", bad)
    proc = _run_assert(
        [
            "verify-plan-identity",
            str(plan),
            "--identity-file",
            str(work / "bad-ino.json"),
            "--work-dir",
            str(work),
        ]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=plan_identity_checksum" in proc.stderr

    # 42 device substitution
    bad = dict(identity)
    bad["dev"] = identity["dev"] + 1
    _write_json(work / "bad-dev.json", bad)
    proc = _run_assert(
        [
            "verify-plan-identity",
            str(plan),
            "--identity-file",
            str(work / "bad-dev.json"),
            "--work-dir",
            str(work),
        ]
    )
    assert proc.returncode != 0

    # 43 plan moved outside owned temp directory
    outside = tmp_path / "outside.bin"
    shutil.copy2(plan, outside)
    outside.chmod(0o600)
    bad = dict(identity)
    bad["path"] = str(outside.resolve())
    _write_json(work / "bad-path.json", bad)
    proc = _run_assert(
        [
            "verify-plan-identity",
            str(outside),
            "--identity-file",
            str(work / "bad-path.json"),
            "--work-dir",
            str(work),
        ]
    )
    assert proc.returncode != 0

    # 44/45 parent temp directory ownership/mode
    work.chmod(0o755)
    proc = _run_assert(
        [
            "verify-plan-identity",
            str(plan),
            "--identity-file",
            str(work / "id.json"),
            "--work-dir",
            str(work),
        ]
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=plan_identity_mode" in proc.stderr
    work.chmod(0o700)

    # 46/47 JSON and human artifacts broader than 0600
    art = work / "plan.json"
    art.write_text("{}", encoding="utf-8")
    art.chmod(0o644)
    proc = _run_assert(["verify-artifact-mode", str(art), "--mode", "600"])
    assert proc.returncode != 0
    art.chmod(0o600)
    human = work / "plan.txt"
    human.write_text("plan", encoding="utf-8")
    human.chmod(0o644)
    assert _run_assert(["verify-artifact-mode", str(human), "--mode", "600"]).returncode != 0


def test_iam_and_ssm_failures_block_success_and_deploy(tmp_path: Path) -> None:
    # 48/50 IAM verification failure
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "iam")
    evil = _approved_allow_policy()
    evil["Statement"].append(
        {
            "Sid": "EvilPass",
            "Effect": "Allow",
            "Action": ["iam:PassRole"],
            "Resource": ["*"],
        }
    )
    _write_json(state / "iam_allow.json", evil)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=iam_policy_verification" in proc.stderr
    assert "Maintenance apply verification complete" not in proc.stdout
    log = (state / "invocations.log").read_text(encoding="utf-8")
    assert "workflow_dispatch" not in log
    assert "Deploy Staging" not in log or "STOP before Deploy Staging" not in proc.stdout

    # 49/51 SSM content verification failure
    repo, bin_dir, state, approved, pre, post, digest = _prep_approved_apply(tmp_path / "ssm")
    bad_content = _approved_ssm_content()
    bad_content["mainSteps"][0]["inputs"]["runCommand"][-1] = "exec /tmp/evil.sh"
    _write_json(state / "approved_ssm_content.json", bad_content)
    proc = _run_apply(
        repo,
        bin_dir,
        _apply_gate_env(approved, pre, post, digest),
        execute=True,
    )
    assert proc.returncode != 0
    assert "FAIL_PHASE=ssm_document_content_verification" in proc.stderr
    assert "Maintenance apply verification complete" not in proc.stdout


def test_no_test_path_invokes_rollback_or_real_aws_mutation() -> None:
    # Inspect executable scripts + harness helpers, not this file's assertion strings.
    for path in (APPLY_SH, CAPTURE_SH, GATE_LIB, ASSERT_PY):
        text = _read(path)
        assert "gh workflow run" not in text
        assert "workflow_dispatch" not in text
        assert "terraform apply -auto-approve" not in text
        assert "ssm send-command" not in text.lower()
        assert "ec2 stop-instances" not in text.lower()
    apply = _read(APPLY_SH)
    assert "Rollback Staging remains unauthorized" in apply
    assert "gh workflow" not in apply


def test_docs_align_with_executable_nonce_and_verification() -> None:
    runbook = _read(RUNBOOK).lower()
    sprint = _read(SPRINT_DOC).lower()
    for doc in (runbook, sprint):
        assert "internally generated" in doc or "generates" in doc and "nonce" in doc
        assert "passrole" in doc or "pass role" in doc or "iam:passrole" in doc
        assert "0600" in doc
        assert "0700" in doc
        assert "structurally" in doc or "structural" in doc
    # Stronger-than-code claims should not remain
    assert "impossible for cloud-init to rerun" not in runbook
    assert "line breaks optional" not in runbook


# ---------------------------------------------------------------------------
# Sprint 25b.5o — host-evidence rollback-marker permission (sudo read-only)
# ---------------------------------------------------------------------------

ROLLBACK_MARKER_PATH = "/opt/dealbrain/runtime/rollback-execution.marker"


def _generate_collect_snippets(tmp_path: Path) -> tuple[Path, Path]:
    """Write pre/post collect snippets via the real gate-lib helper."""
    work = tmp_path / "snippet-work"
    work.mkdir()
    pre = work / "host-evidence-collect-pre.sh"
    post = work / "host-evidence-collect-post.sh"
    script = textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        set -Eeuo pipefail
        source {GATE_LIB!s}
        STAGING_MAINTENANCE_RUN_NONCE={NONCE!r}
        staging_maintenance_write_host_evidence_collect_snippet \\
          {pre!s} pre-apply {NONCE!r} deadbeefcafebabe0123456789abcdef01234567
        staging_maintenance_write_host_evidence_collect_snippet \\
          {post!s} post-apply {NONCE!r} deadbeefcafebabe0123456789abcdef01234567
        """
    )
    proc = subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert pre.is_file() and post.is_file()
    return pre, post


def _load_rollback_marker_present(snippet: Path):
    """Extract and exec rollback_marker_present() from a generated snippet."""
    text = snippet.read_text(encoding="utf-8")
    # Snippet wraps Python in a quoted heredoc; extract the helper body.
    start = text.index("def rollback_marker_present() -> bool:")
    end = text.index("\nboot_id = read_text(")
    helper_src = text[start:end]
    assert "ROLLBACK_MARKER_PATH" in text
    ns: dict[str, Any] = {"subprocess": __import__("subprocess")}
    # Bind the module-level constant used by the helper.
    const_line = [line for line in text.splitlines() if line.startswith("ROLLBACK_MARKER_PATH = ")][
        0
    ]
    exec(const_line, ns)  # noqa: S102 — test loads generated helper source
    exec(helper_src, ns)  # noqa: S102
    return ns["rollback_marker_present"]


class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _sudo_marker_run_fake(
    *,
    probe_rc: int = 0,
    probe_err: str = "",
    check_rc: int = 0,
    check_err: str = "",
    allow_check: bool = True,
    calls: list[list[str]] | None = None,
):
    """Build a subprocess.run side_effect for rollback_marker_present()."""

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        if calls is not None:
            calls.append(list(cmd))
        if cmd[:3] == ["sudo", "-n", "true"]:
            return _FakeCompleted(probe_rc, stderr=probe_err)
        if cmd[:4] == ["sudo", "-n", "test", "-e"]:
            if not allow_check:
                raise AssertionError("test -e must not run when sudo probe fails")
            assert cmd[4] == ROLLBACK_MARKER_PATH
            return _FakeCompleted(check_rc, stderr=check_err)
        raise AssertionError(f"unexpected cmd: {cmd}")

    return fake_run


def test_marker_present_via_successful_sudo_check(tmp_path: Path) -> None:
    pre, post = _generate_collect_snippets(tmp_path)
    for snippet in (pre, post):
        helper = _load_rollback_marker_present(snippet)
        calls: list[list[str]] = []
        fake_run = _sudo_marker_run_fake(check_rc=0, calls=calls)
        with mock.patch("subprocess.run", side_effect=fake_run):
            assert helper() is True
        assert ["sudo", "-n", "true"] in calls
        assert ["sudo", "-n", "test", "-e", ROLLBACK_MARKER_PATH] in calls


def test_marker_absent_via_successful_sudo_check(tmp_path: Path) -> None:
    pre, post = _generate_collect_snippets(tmp_path)
    for snippet in (pre, post):
        helper = _load_rollback_marker_present(snippet)
        fake_run = _sudo_marker_run_fake(check_rc=1, check_err="")
        with mock.patch("subprocess.run", side_effect=fake_run):
            assert helper() is False


@pytest.mark.parametrize(
    "probe_rc,probe_err",
    [
        (1, "sudo: a password is required"),
        (1, ""),
        (127, "sudo: command not found"),
    ],
)
def test_sudo_unavailable_or_denied_fails_closed_no_json(
    tmp_path: Path, probe_rc: int, probe_err: str
) -> None:
    pre, _post = _generate_collect_snippets(tmp_path)
    helper = _load_rollback_marker_present(pre)
    fake_run = _sudo_marker_run_fake(probe_rc=probe_rc, probe_err=probe_err, allow_check=False)
    with (
        mock.patch("subprocess.run", side_effect=fake_run),
        pytest.raises(SystemExit) as excinfo,
    ):
        helper()
    msg = str(excinfo.value)
    assert "sudo" in msg.lower()
    # Must not look like valid evidence JSON
    assert not msg.strip().startswith("{")
    assert "rollback_execution_marker_present" not in msg


@pytest.mark.parametrize(
    "check_rc,check_err",
    [
        (1, "sudo: a password is required"),  # denial on test (stderr)
        (2, "test: binary operator expected"),
        (126, "permission denied"),
        (255, ""),
    ],
)
def test_sudo_command_error_or_ambiguous_fails_closed_no_json(
    tmp_path: Path, check_rc: int, check_err: str
) -> None:
    pre, _post = _generate_collect_snippets(tmp_path)
    helper = _load_rollback_marker_present(pre)
    fake_run = _sudo_marker_run_fake(check_rc=check_rc, check_err=check_err)
    with (
        mock.patch("subprocess.run", side_effect=fake_run),
        pytest.raises(SystemExit) as excinfo,
    ):
        helper()
    msg = str(excinfo.value)
    assert "rollback-marker" in msg.lower() or "ambiguous" in msg.lower()
    assert not msg.strip().startswith("{")
    assert "rollback_execution_marker_present" not in msg


def test_unprivileged_path_exists_not_authoritative_for_marker(tmp_path: Path) -> None:
    pre, post = _generate_collect_snippets(tmp_path)
    for snippet in (pre, post):
        text = snippet.read_text(encoding="utf-8")
        assert "def rollback_marker_present()" in text
        assert '["sudo", "-n", "test", "-e", ROLLBACK_MARKER_PATH]' in text
        assert '["sudo", "-n", "true"]' in text
        # Direct unprivileged exists() on the marker path must not be authoritative.
        assert 'Path("/opt/dealbrain/runtime/rollback-execution.marker").exists()' not in text
        assert "Path(ROLLBACK_MARKER_PATH).exists()" not in text
        assert "marker = rollback_marker_present()" in text


def test_marker_helper_remains_read_only_and_no_mutation_commands(tmp_path: Path) -> None:
    pre, post = _generate_collect_snippets(tmp_path)
    for snippet in (pre, post):
        text = snippet.read_text(encoding="utf-8")
        py_start = text.index("python3 - <<'PY'")
        py_body = text[py_start:]
        # Read-only Session Manager model preserved.
        assert "Read-only Session Manager collection" in text
        assert "Do not use SSM SendCommand" in text
        assert "never create/remove/chmod/chown/alter the marker" in text.lower() or (
            "never create" in text.lower() and "alter the marker" in text.lower()
        )
        # No marker mutation primitives in the collect helper Python body.
        for bad in (
            "touch ",
            "unlink(",
            "os.remove",
            "os.unlink",
            "os.rename",
            "shutil.move",
            "shutil.rmtree",
            "chmod(",
            "chown(",
            ".write_text(",
            ".write_bytes(",
            ".unlink(",
            ".mkdir(",
            ".touch(",
            ".rename(",
            "truncate(",
            f"tee {ROLLBACK_MARKER_PATH}",
            f"> {ROLLBACK_MARKER_PATH}",
            f">> {ROLLBACK_MARKER_PATH}",
            f"rm {ROLLBACK_MARKER_PATH}",
            f"mv {ROLLBACK_MARKER_PATH}",
        ):
            assert bad not in py_body, bad
        # sudo usage is existence-only (probe + test -e).
        assert '"sudo", "-n", "true"' in py_body
        assert '"sudo", "-n", "test", "-e"' in py_body
        assert "sudoedit" not in py_body.lower()
        assert "visudo" not in py_body.lower()
        # Must not open the marker for write.
        assert "open(" not in py_body or "DEPLOY_VERSION" in py_body


def test_collect_snippet_preserves_nonce_and_evidence_bindings(tmp_path: Path) -> None:
    pre, post = _generate_collect_snippets(tmp_path)
    repo_sha = "deadbeefcafebabe0123456789abcdef01234567"
    for phase, snippet in (("pre-apply", pre), ("post-apply", post)):
        text = snippet.read_text(encoding="utf-8")
        assert f"Run nonce (embed exactly; do not invent another): {NONCE}" in text
        assert f'"phase": "{phase}"' in text
        assert f'"nonce": "{NONCE}"' in text
        assert f'"instance_id": "{INSTANCE_ID}"' in text
        assert f'"account_id": "{ACCOUNT_ID}"' in text
        assert f'"region": "{REGION}"' in text
        assert "boot_id" in text
        assert "uptime_seconds" in text
        assert "cloud_init_status" in text
        assert "release_id" in text
        assert "image_digest" in text
        assert "current_pointer" in text
        assert "previous_pointer" in text
        assert "rollback_execution_marker_present" in text
        assert "captured_at" in text
        assert repo_sha in text
        assert "repository_sha" in text
        assert "Do not dump env" in text
        assert "Do not use SSM SendCommand" in text


def test_pre_and_post_evidence_helpers_share_corrected_marker_behavior(
    tmp_path: Path,
) -> None:
    pre, post = _generate_collect_snippets(tmp_path)
    pre_text = pre.read_text(encoding="utf-8")
    post_text = post.read_text(encoding="utf-8")
    # Same helper definition and call site in both phases.
    for text in (pre_text, post_text):
        assert "def rollback_marker_present() -> bool:" in text
        assert "marker = rollback_marker_present()" in text
        assert 'Path("/opt/dealbrain/runtime/rollback-execution.marker").exists()' not in text

    # Helper bodies are identical aside from phase string binding.
    def _helper_body(text: str) -> str:
        start = text.index("def rollback_marker_present() -> bool:")
        end = text.index("\nboot_id = read_text(")
        return text[start:end]

    assert _helper_body(pre_text) == _helper_body(post_text)


def test_docs_state_sudo_readonly_marker_check_and_fail_closed() -> None:
    runbook = re.sub(r"\s+", " ", _read(RUNBOOK).lower())
    sprint = re.sub(r"\s+", " ", _read(SPRINT_DOC).lower())
    for doc in (runbook, sprint):
        assert "passwordless sudo" in doc
        assert "read-only" in doc
        assert "rollback-marker" in doc or "rollback marker" in doc
        assert "fail" in doc and "closed" in doc
        assert "never creates" in doc or "never create" in doc
        assert "removes" in doc or "remove" in doc
        assert "alters the marker" in doc or "alter the marker" in doc
    # Must not broaden maintenance authorization beyond the existing ACK.
    assert ACK in _read(SPRINT_DOC)
    assert ACK in _read(RUNBOOK)
