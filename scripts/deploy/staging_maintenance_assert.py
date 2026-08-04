#!/usr/bin/env python3
"""Sprint 25b.5n — fail-closed plan / host-evidence / IAM / SSM assertions.

Used by staging maintenance operator scripts. No AWS or Terraform mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

INSTANCE_ID = "i-0edd57f32296aa323"
ACCOUNT_ID = "941035169846"
REGION = "us-east-1"
RELEASE_BUCKET = f"dealbrain-staging-release-artifacts-{ACCOUNT_ID}"
RELEASE_BUCKET_ARN = f"arn:aws:s3:::{RELEASE_BUCKET}"

EXPECTED_CREATE = 1
EXPECTED_UPDATE = 2
EXPECTED_REPLACE = 0
EXPECTED_DESTROY = 0
EXPECTED_READ = 1

SSM_ADDRESS = "module.ssm_rollback_document.aws_ssm_document.staging_rollback"
IAM_ADDRESS = "module.github_deploy_role.aws_iam_role_policy.deploy_allow"
EC2_ADDRESS = "module.ec2.aws_instance.api"
DATA_ADDRESS = "module.github_deploy_role.data.aws_iam_policy_document.deploy_allow"

EXPECTED_MANAGED = {
    SSM_ADDRESS: ["create"],
    IAM_ADDRESS: ["update"],
    EC2_ADDRESS: ["update"],
}
EXPECTED_READS = {DATA_ADDRESS: ["read"]}
EXPECTED_OUTPUT_CHANGES = {
    "ssm_rollback_document_name": ["create"],
    "ssm_rollback_document_arn": ["create"],
}

FORBIDDEN_PREFIXES = (
    "module.rds",
    "module.alb",
    "module.networking",
    "module.security_groups",
    "module.secrets",
    "module.release_artifacts",
)
FORBIDDEN_SUBSTRINGS = (
    "aws_s3_bucket",
    "aws_route53",
    "environments/production",
    "dealbrain-production",
    "module.production",
)

EC2_CRITICAL_ATTRS = frozenset(
    {
        "id",
        "arn",
        "ami",
        "instance_type",
        "subnet_id",
        "vpc_security_group_ids",
        "security_groups",
        "iam_instance_profile",
        "root_block_device",
        "ebs_block_device",
        "tags",
        "tags_all",
        "user_data_replace_on_change",
        "availability_zone",
        "key_name",
        "monitoring",
        "associate_public_ip_address",
        "source_dest_check",
        "private_ip",
        "tenancy",
        "ebs_optimized",
        "hibernation",
        "disable_api_termination",
        "disable_api_stop",
        "credit_specification",
        "metadata_options",
        "cpu_options",
        "capacity_reservation_specification",
        "enclave_options",
        "maintenance_options",
        "private_dns_name_options",
        "network_interface",
        "secondary_private_ips",
        "ipv6_addresses",
        "ipv6_address_count",
        "host_id",
        "placement_group",
        "placement_partition_number",
        "user_data",
    }
)

BOOT_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
RELEASE_ID_RE = re.compile(r"^rel-[A-Za-z0-9][A-Za-z0-9._-]{3,127}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
NONCE_RE = re.compile(r"^[0-9a-f]{32}$")
SHA1_OR_SHA256_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
CLOUD_INIT_ALLOWLIST = frozenset(
    {
        "done",
        "disabled",
        "done (disabled on next boot)",
    }
)
ALB_DNS_RE = re.compile(r"^(dualstack\.)?[a-z0-9][a-z0-9-]*\.[a-z0-9-]+\.elb\.amazonaws\.com$")
TG_ARN_RE = re.compile(
    rf"^arn:aws:elasticloadbalancing:{re.escape(REGION)}:{re.escape(ACCOUNT_ID)}:targetgroup/.+$"
)

PRODUCTION_MARKERS = (
    "production",
    "dealbrain-production",
    "/production/",
    ":production",
    "environment/production",
    "environments/production",
)

SSM_DOC_NAME = "DealBrain-StagingRollback"
SSM_DEPLOY_DOC_NAME = "DealBrain-StagingDeploy"
SSM_ENTRYPOINT = "/opt/dealbrain/bin/dealbrain-staging-rollback.sh"
SSM_TIMEOUT_SECONDS = "2400"
SSM_MAX_TIMEOUT_SECONDS = 2400

FORBIDDEN_IAM_ACTIONS = frozenset(
    {
        "iam:PassRole",
        "iam:*",
        "*",
        "sts:AssumeRole",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:UpdateAssumeRolePolicy",
        "iam:CreateAccessKey",
        "iam:CreatePolicyVersion",
        "iam:SetDefaultPolicyVersion",
    }
)


class AssertError(Exception):
    def __init__(self, message: str, code: int = 2, phase: str = "assert") -> None:
        super().__init__(message)
        self.code = code
        self.phase = phase


def _die(message: str, code: int = 2, phase: str = "assert") -> None:
    raise AssertError(message, code=code, phase=phase)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _die(f"missing JSON file: {path}", code=2)
    except json.JSONDecodeError as exc:
        _die(f"malformed JSON in {path}: {exc}", code=2)
    except OSError as exc:
        _die(f"cannot read {path}: {exc}", code=2)


def _is_truthy_unknown(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, dict):
        return any(_is_truthy_unknown(v) for v in value.values())
    if isinstance(value, list):
        return any(_is_truthy_unknown(v) for v in value)
    return False


def _actions_bucket(acts: list[str]) -> str | None:
    if acts == ["no-op"]:
        return None
    if acts == ["create"]:
        return "create"
    if acts == ["update"]:
        return "update"
    if acts == ["delete"]:
        return "destroy"
    if acts == ["read"]:
        return "read"
    if acts in (["delete", "create"], ["create", "delete"]):
        return "replace"
    return "unknown"


def generate_nonce() -> str:
    """Return a cryptographically strong 32-hex-char run nonce."""
    nonce = secrets.token_hex(16)
    if not NONCE_RE.fullmatch(nonce):
        _die("generated nonce failed format check", phase="host_evidence_nonce")
    return nonce


def validate_nonce_format(nonce: str, *, phase: str = "host_evidence_nonce") -> str:
    if not isinstance(nonce, str) or not NONCE_RE.fullmatch(nonce):
        _die("host evidence nonce missing or malformed (want 32 lowercase hex)", phase=phase)
    return nonce


def canonical_json(value: Any) -> str:
    """Stable JSON for semantic comparison (sorted keys, compact separators)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value]


def _normalize_condition(cond: Any) -> dict[str, dict[str, list[str]]]:
    if cond is None:
        return {}
    if not isinstance(cond, dict):
        _die("IAM Condition must be an object", phase="iam_policy_verification")
    out: dict[str, dict[str, list[str]]] = {}
    for op, keys in cond.items():
        if not isinstance(keys, dict):
            _die(
                f"IAM Condition operator {op!r} must map to an object",
                phase="iam_policy_verification",
            )
        norm_keys: dict[str, list[str]] = {}
        for key, vals in keys.items():
            items = [str(v) for v in _as_list(vals)]
            norm_keys[str(key)] = sorted(items)
        out[str(op)] = dict(sorted(norm_keys.items()))
    return dict(sorted(out.items()))


def _normalize_statement(stmt: Any) -> dict[str, Any]:
    if not isinstance(stmt, dict):
        _die("IAM Statement must be an object", phase="iam_policy_verification")
    actions = sorted(str(a) for a in _as_list(stmt.get("Action", [])))
    resources = sorted(str(r) for r in _as_list(stmt.get("Resource", [])))
    effect = stmt.get("Effect")
    if effect not in ("Allow", "Deny"):
        _die(f"IAM Effect invalid: {effect!r}", phase="iam_policy_verification")
    sid = stmt.get("Sid")
    if not isinstance(sid, str) or not sid:
        _die("IAM Statement Sid is required", phase="iam_policy_verification")
    normalized: dict[str, Any] = {
        "Sid": sid,
        "Effect": effect,
        "Action": actions,
        "Resource": resources,
    }
    if "Condition" in stmt and stmt.get("Condition") not in (None, {}):
        normalized["Condition"] = _normalize_condition(stmt.get("Condition"))
    # Reject unexpected keys that change authorization semantics.
    allowed_keys = {
        "Sid",
        "Effect",
        "Action",
        "Resource",
        "Condition",
        "Principal",
        "NotAction",
        "NotResource",
    }
    extra = set(stmt) - allowed_keys
    if extra:
        _die(
            f"IAM Statement {sid} has unexpected keys: {sorted(extra)}",
            phase="iam_policy_verification",
        )
    if "NotAction" in stmt or "NotResource" in stmt or "Principal" in stmt:
        _die(
            f"IAM Statement {sid} uses unsupported fields",
            phase="iam_policy_verification",
        )
    return normalized


def normalize_iam_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        _die("IAM policy document must be an object", phase="iam_policy_verification")
    version = policy.get("Version")
    if version != "2012-10-17":
        _die(f"IAM Version {version!r} != '2012-10-17'", phase="iam_policy_verification")
    statements = policy.get("Statement")
    if not isinstance(statements, list) or not statements:
        _die("IAM Statement must be a non-empty list", phase="iam_policy_verification")
    normalized_stmts = [_normalize_statement(s) for s in statements]
    # Order-independent by Sid for comparison; duplicate Sids rejected.
    by_sid: dict[str, dict[str, Any]] = {}
    for stmt in normalized_stmts:
        sid = stmt["Sid"]
        if sid in by_sid:
            _die(f"duplicate IAM Sid: {sid}", phase="iam_policy_verification")
        by_sid[sid] = stmt
    return {
        "Version": "2012-10-17",
        "Statement": [by_sid[k] for k in sorted(by_sid)],
    }


def expected_deploy_allow_policy() -> dict[str, Any]:
    deploy_arn = f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:document/{SSM_DEPLOY_DOC_NAME}"
    rollback_arn = f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:document/{SSM_DOC_NAME}"
    return normalize_iam_policy(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "SendCommandApprovedDocument",
                    "Effect": "Allow",
                    "Action": "ssm:SendCommand",
                    "Resource": [deploy_arn, rollback_arn],
                },
                {
                    "Sid": "SendCommandEnvironmentTaggedInstances",
                    "Effect": "Allow",
                    "Action": "ssm:SendCommand",
                    "Resource": f"arn:aws:ec2:{REGION}:{ACCOUNT_ID}:instance/*",
                    "Condition": {
                        "StringEquals": {
                            "ssm:resourceTag/Environment": "staging",
                            "ssm:resourceTag/Project": "dealbrain",
                        }
                    },
                },
                {
                    "Sid": "ObserveSsmCommands",
                    "Effect": "Allow",
                    "Action": "ssm:GetCommandInvocation",
                    "Resource": "*",
                },
                {
                    "Sid": "DescribeForTargeting",
                    "Effect": "Allow",
                    "Action": [
                        "ec2:DescribeInstances",
                        "ec2:DescribeInstanceStatus",
                        "rds:DescribeDBInstances",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "ReleaseArtifactsObjectAccess",
                    "Effect": "Allow",
                    "Action": ["s3:PutObject", "s3:GetObject"],
                    "Resource": [
                        f"{RELEASE_BUCKET_ARN}/releases/*",
                        f"{RELEASE_BUCKET_ARN}/evidence/*",
                    ],
                },
                {
                    "Sid": "ReleaseArtifactsListBucket",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": RELEASE_BUCKET_ARN,
                    "Condition": {
                        "StringLike": {
                            "s3:prefix": [
                                "releases/",
                                "releases/*",
                                "evidence/",
                                "evidence/*",
                            ]
                        }
                    },
                },
            ],
        }
    )


def expected_deploy_deny_policy() -> dict[str, Any]:
    return normalize_iam_policy(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyIamMutationAndPassRole",
                    "Effect": "Deny",
                    "Action": "iam:*",
                    "Resource": "*",
                },
                {
                    "Sid": "DenyOrganizationsMutation",
                    "Effect": "Deny",
                    "Action": "organizations:*",
                    "Resource": "*",
                },
                {
                    "Sid": "DenySecretsManagerValueAccess",
                    "Effect": "Deny",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:PutSecretValue",
                        "secretsmanager:DeleteSecret",
                        "secretsmanager:UpdateSecret",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "DenyRdsMutationAndSnapshot",
                    "Effect": "Deny",
                    "Action": [
                        "rds:CreateDBSnapshot",
                        "rds:DeleteDBInstance",
                        "rds:ModifyDBInstance",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "DenyDangerousEc2Mutation",
                    "Effect": "Deny",
                    "Action": [
                        "ec2:TerminateInstances",
                        "ec2:StopInstances",
                        "ec2:ModifyInstanceAttribute",
                        "ec2:RunInstances",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "DenySendCommandOppositeEnvironment",
                    "Effect": "Deny",
                    "Action": "ssm:SendCommand",
                    "Resource": f"arn:aws:ec2:{REGION}:{ACCOUNT_ID}:instance/*",
                    "Condition": {
                        "StringEquals": {
                            "ssm:resourceTag/Environment": "production",
                        }
                    },
                },
                {
                    "Sid": "DenyOppositeEnvironmentSecretArns",
                    "Effect": "Deny",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                        "secretsmanager:PutSecretValue",
                        "secretsmanager:UpdateSecret",
                        "secretsmanager:DeleteSecret",
                    ],
                    "Resource": "arn:aws:secretsmanager:*:*:secret:dealbrain/production/*",
                },
                {
                    "Sid": "DenyTerraformStateWrites",
                    "Effect": "Deny",
                    "Action": [
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:PutObjectAcl",
                    ],
                    "Resource": [
                        "arn:aws:s3:::dealbrain-terraform-state-*/*",
                        "arn:aws:s3:::dealbrain-terraform-state-*",
                    ],
                },
            ],
        }
    )


def _reject_dangerous_allow_actions(policy: dict[str, Any]) -> None:
    for stmt in policy["Statement"]:
        if stmt["Effect"] != "Allow":
            continue
        for action in stmt["Action"]:
            if action in FORBIDDEN_IAM_ACTIONS or action.lower() == "iam:passrole":
                _die(
                    f"IAM allow policy forbids action {action!r} (Sid={stmt['Sid']})",
                    phase="iam_policy_verification",
                )
            if action == "iam:*" or action.endswith(":PassRole"):
                _die(
                    f"IAM allow policy forbids action {action!r} (Sid={stmt['Sid']})",
                    phase="iam_policy_verification",
                )


def _reject_production_and_foreign_arns(
    policy: dict[str, Any], *, allow_opposite_deny: bool
) -> None:
    blob = canonical_json(policy).lower()
    # Deny policy intentionally mentions production as the opposite-environment deny target.
    if not allow_opposite_deny:
        for marker in PRODUCTION_MARKERS:
            if marker in blob:
                _die(
                    f"IAM policy contains production identifier {marker!r}",
                    phase="iam_policy_verification",
                )
    for stmt in policy["Statement"]:
        for resource in stmt["Resource"]:
            if resource == "*":
                continue
            if "arn:aws:" not in resource and not resource.startswith("arn:aws:"):
                continue
            # Account binding for concrete account-scoped ARNs.
            m = re.search(r"arn:aws:[a-z0-9-]+:([a-z0-9-]*):(\d{12}|\*):", resource)
            if m:
                region, account = m.group(1), m.group(2)
                if account not in ("*", ACCOUNT_ID) and account.isdigit():
                    _die(
                        f"IAM resource in unexpected account: {resource}",
                        phase="iam_policy_verification",
                    )
                if (
                    region
                    and region not in ("*", REGION, "")
                    and "secretsmanager" not in resource
                    and not (allow_opposite_deny and "secretsmanager" in resource)
                ):
                    _die(
                        f"IAM resource in unexpected region: {resource}",
                        phase="iam_policy_verification",
                    )


def validate_iam_deploy_allow_policy(policy: dict[str, Any]) -> None:
    normalized = normalize_iam_policy(policy)
    _reject_dangerous_allow_actions(normalized)
    _reject_production_and_foreign_arns(normalized, allow_opposite_deny=False)
    expected = expected_deploy_allow_policy()
    if canonical_json(normalized) != canonical_json(expected):
        _die(
            "IAM deploy_allow policy does not match the approved staging contract "
            "(structural mismatch after normalization)",
            phase="iam_policy_verification",
        )


def validate_iam_deploy_deny_policy(policy: dict[str, Any]) -> None:
    normalized = normalize_iam_policy(policy)
    expected = expected_deploy_deny_policy()
    if canonical_json(normalized) != canonical_json(expected):
        _die(
            "IAM deploy_deny policy does not match the approved staging contract",
            phase="iam_policy_verification",
        )
    # Explicit PassRole / iam mutation deny must remain present.
    deny_iam = next(
        (s for s in normalized["Statement"] if s["Sid"] == "DenyIamMutationAndPassRole"),
        None,
    )
    if deny_iam is None or "iam:*" not in deny_iam["Action"]:
        _die(
            "IAM deny policy missing iam:* PassRole/mutation deny",
            phase="iam_policy_verification",
        )


def expected_ssm_document_content() -> dict[str, Any]:
    """Canonical content matching infra/terraform/modules/ssm_rollback_document."""
    return {
        "schemaVersion": "2.2",
        "description": "DealBrain staging digest rollback. Bounded parameters; host-side secrets only.",  # noqa: E501
        "parameters": {
            "ReleaseId": {
                "type": "String",
                "description": "Target release ID from the validated build manifest.",
                "allowedPattern": "^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$",
            },
            "GitSha": {
                "type": "String",
                "description": "Full 40-character git SHA of the target image source.",
                "allowedPattern": "^[0-9a-f]{40}$",
            },
            "ImageRepository": {
                "type": "String",
                "description": "Canonical GHCR repository without tag or digest.",
                "allowedPattern": "^ghcr\\.io/[a-z0-9._/-]+$",
            },
            "ImageDigest": {
                "type": "String",
                "description": "Immutable target image digest.",
                "allowedPattern": "^sha256:[0-9a-f]{64}$",
            },
            "BundleChecksum": {
                "type": "String",
                "description": "SHA-256 hex digest of the target release bundle.tar.gz.",
                "allowedPattern": "^[0-9a-f]{64}$",
            },
            "DeployRunId": {
                "type": "String",
                "description": "GitHub Actions rollback workflow run ID.",
                "allowedPattern": "^[0-9]+$",
            },
            "BundleBucket": {
                "type": "String",
                "description": "Staging release-artifacts S3 bucket name.",
                "allowedPattern": "^dealbrain-staging-release-artifacts-[0-9]{12}$",
            },
            "BundleKey": {
                "type": "String",
                "description": "S3 object key for the target release bundle tarball.",
                "allowedPattern": "^releases/rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}/bundle\\.tar\\.gz$",  # noqa: E501
            },
            "SourceManifestSha256": {
                "type": "String",
                "description": "Checksum of the authoritative target release-manifest.",
                "allowedPattern": "^[0-9a-f]{64}$",
            },
        },
        "mainSteps": [
            {
                "action": "aws:runShellScript",
                "name": "DealBrainStagingRollback",
                "inputs": {
                    "workingDirectory": "/opt/dealbrain",
                    "timeoutSeconds": SSM_TIMEOUT_SECONDS,
                    "runCommand": [
                        "#!/bin/bash",
                        "set -euo pipefail",
                        "# Fixed rollback entrypoint only — parameters exported as env, never eval'd.",  # noqa: E501
                        "export DEALBRAIN_RELEASE_ID='{{ReleaseId}}'",
                        "export DEALBRAIN_GIT_SHA='{{GitSha}}'",
                        "export DEALBRAIN_IMAGE_REPOSITORY='{{ImageRepository}}'",
                        "export DEALBRAIN_IMAGE_DIGEST='{{ImageDigest}}'",
                        "export DEALBRAIN_BUNDLE_CHECKSUM='{{BundleChecksum}}'",
                        "export DEALBRAIN_DEPLOY_RUN_ID='{{DeployRunId}}'",
                        "export DEALBRAIN_BUNDLE_BUCKET='{{BundleBucket}}'",
                        "export DEALBRAIN_BUNDLE_KEY='{{BundleKey}}'",
                        "export DEALBRAIN_SOURCE_MANIFEST_SHA256='{{SourceManifestSha256}}'",
                        "export DEALBRAIN_ENVIRONMENT='staging'",
                        "export DEALBRAIN_OPERATION='rollback'",
                        f"exec {SSM_ENTRYPOINT}",
                    ],
                },
            }
        ],
    }


def _parse_ssm_content(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed: Any
    meta: dict[str, Any]
    content_field = None
    if isinstance(raw, dict):
        if "content" in raw:
            content_field = raw["content"]
        elif "Content" in raw:
            content_field = raw["Content"]
    if (
        isinstance(raw, dict)
        and content_field is not None
        and isinstance(content_field, (str, dict))
    ):
        # get-document envelope
        content = content_field
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                _die(
                    f"SSM document content JSON malformed: {exc}",
                    phase="ssm_document_content_verification",
                )
        elif isinstance(content, dict):
            parsed = content
        else:
            _die(
                "SSM document content has unexpected type",
                phase="ssm_document_content_verification",
            )
        meta = raw
    elif isinstance(raw, dict) and "schemaVersion" in raw:
        parsed = raw
        meta = {}
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            _die(
                f"SSM document content JSON malformed: {exc}",
                phase="ssm_document_content_verification",
            )
        meta = {}
    else:
        _die("SSM document payload must be an object", phase="ssm_document_content_verification")
    if not isinstance(parsed, dict):
        _die(
            "SSM document content must be a JSON object",
            phase="ssm_document_content_verification",
        )
    return parsed, meta


def validate_ssm_document_content(
    payload: dict[str, Any],
    *,
    expected_name: str = SSM_DOC_NAME,
    expected_version: str | None = None,
) -> None:
    content, meta = _parse_ssm_content(payload)

    if meta:
        name = meta.get("Name") or meta.get("name")
        if name is not None and name != expected_name:
            _die(
                f"SSM document name {name!r} != {expected_name!r}",
                phase="ssm_document_content_verification",
            )
        doc_type = meta.get("DocumentType") or meta.get("documentType")
        if doc_type is not None and doc_type != "Command":
            _die(
                f"SSM document type {doc_type!r} != 'Command'",
                phase="ssm_document_content_verification",
            )
        status = meta.get("Status") or meta.get("status")
        if status is not None and status != "Active":
            _die(
                f"SSM document status {status!r} != 'Active'",
                phase="ssm_document_content_verification",
            )
        owner = meta.get("Owner") or meta.get("owner")
        if owner is not None and str(owner) not in (ACCOUNT_ID, "self"):
            _die(
                f"SSM document owner {owner!r} != {ACCOUNT_ID!r}",
                phase="ssm_document_content_verification",
            )
        default_version = meta.get("DefaultVersion") or meta.get("defaultVersion")
        doc_version = meta.get("DocumentVersion") or meta.get("documentVersion")
        if expected_version is not None and str(doc_version) != str(expected_version) and str(
            default_version
        ) != str(expected_version):
            _die(
                f"SSM active/default version mismatch (got document={doc_version!r} "
                f"default={default_version!r} expected={expected_version!r})",
                phase="ssm_document_content_verification",
            )
        if (
            default_version is not None
            and doc_version is not None
            and str(default_version) != str(doc_version)
        ):
            _die(
                "SSM DocumentVersion is not the default active version",
                phase="ssm_document_content_verification",
            )

    # Structural content checks before canonical equality.
    blob = canonical_json(content)
    if re.search(r"production", blob, flags=re.IGNORECASE):
        _die(
            "SSM content contains production identifier",
            phase="ssm_document_content_verification",
        )
    for marker in ("DATABASE_URL", "AWS_SECRET", "printenv", "env |"):
        if marker.lower() in blob.lower():
            _die(
                f"SSM content contains forbidden sequence {marker!r}",
                phase="ssm_document_content_verification",
            )

    params = content.get("parameters")
    if not isinstance(params, dict):
        _die("SSM content missing parameters object", phase="ssm_document_content_verification")
    for name, spec in params.items():
        if not isinstance(spec, dict):
            _die(f"SSM parameter {name} invalid", phase="ssm_document_content_verification")
        if "allowedPattern" not in spec:
            _die(
                f"SSM parameter {name} missing allowedPattern",
                phase="ssm_document_content_verification",
            )
        ptype = spec.get("type")
        if ptype not in ("String", "StringList"):
            _die(
                f"SSM parameter {name} has free-form/unsupported type {ptype!r}",
                phase="ssm_document_content_verification",
            )
        # Reject free-form command parameters.
        if name.lower() in {"commands", "command", "script", "shell"}:
            _die(
                f"SSM free-form command parameter forbidden: {name}",
                phase="ssm_document_content_verification",
            )

    steps = content.get("mainSteps")
    if not isinstance(steps, list) or len(steps) != 1:
        _die(
            "SSM content must have exactly one mainSteps entry",
            phase="ssm_document_content_verification",
        )
    step = steps[0]
    if not isinstance(step, dict):
        _die("SSM mainSteps entry must be an object", phase="ssm_document_content_verification")
    if step.get("action") != "aws:runShellScript":
        _die(
            f"SSM unexpected plugin/action: {step.get('action')!r}",
            phase="ssm_document_content_verification",
        )
    inputs = step.get("inputs") or {}
    if not isinstance(inputs, dict):
        _die("SSM step inputs must be an object", phase="ssm_document_content_verification")
    timeout = inputs.get("timeoutSeconds")
    if timeout is None:
        _die("SSM timeoutSeconds missing", phase="ssm_document_content_verification")
    try:
        timeout_int = int(str(timeout))
    except ValueError:
        _die(
            f"SSM timeoutSeconds invalid: {timeout!r}",
            phase="ssm_document_content_verification",
        )
    if timeout_int <= 0:
        _die("SSM timeoutSeconds must be positive", phase="ssm_document_content_verification")
    if timeout_int > SSM_MAX_TIMEOUT_SECONDS:
        _die(
            f"SSM timeoutSeconds {timeout_int} exceeds bound {SSM_MAX_TIMEOUT_SECONDS}",
            phase="ssm_document_content_verification",
        )
    if str(timeout) != SSM_TIMEOUT_SECONDS:
        _die(
            f"SSM timeoutSeconds {timeout!r} != approved {SSM_TIMEOUT_SECONDS!r}",
            phase="ssm_document_content_verification",
        )

    run_command = inputs.get("runCommand")
    if not isinstance(run_command, list) or not run_command:
        _die("SSM runCommand missing", phase="ssm_document_content_verification")
    joined = "\n".join(str(x) for x in run_command)
    if SSM_ENTRYPOINT not in joined:
        _die("SSM entrypoint path mismatch", phase="ssm_document_content_verification")
    if "exec /opt/dealbrain/bin/dealbrain-staging-rollback.sh" not in joined:
        _die("SSM fixed entrypoint exec line missing", phase="ssm_document_content_verification")
    if "DEALBRAIN_ENVIRONMENT='staging'" not in joined:
        _die("SSM environment must be fixed to staging", phase="ssm_document_content_verification")
    # No alternate executable path / env dump / secrets.
    for bad in ("printenv", "env -0", "cat /etc/environment", "DATABASE_URL", "eval ", "`"):
        if bad in joined:
            _die(
                f"SSM content contains forbidden sequence {bad!r}",
                phase="ssm_document_content_verification",
            )

    expected = expected_ssm_document_content()
    if canonical_json(content) != canonical_json(expected):
        _die(
            "SSM document content does not match approved canonical contract",
            phase="ssm_document_content_verification",
        )


def validate_ssm_document_meta(
    data: dict[str, Any],
    *,
    expected_name: str = SSM_DOC_NAME,
) -> None:
    if not isinstance(data, dict):
        _die("SSM document metadata must be an object", phase="ssm_document_content_verification")
    if data.get("Name") != expected_name:
        _die(
            f"SSM document name {data.get('Name')!r} != {expected_name!r}",
            phase="ssm_document_content_verification",
        )
    if data.get("Status") != "Active":
        _die(
            f"SSM document status {data.get('Status')!r} != Active",
            phase="ssm_document_content_verification",
        )
    doc_type = data.get("DocumentType")
    if doc_type is not None and doc_type != "Command":
        _die(
            f"SSM document type {doc_type!r} != Command",
            phase="ssm_document_content_verification",
        )
    if not data.get("DocumentVersion"):
        _die("SSM document DocumentVersion missing", phase="ssm_document_content_verification")
    default_version = data.get("DefaultVersion")
    if default_version is not None and str(default_version) != str(data.get("DocumentVersion")):
        _die(
            "SSM DocumentVersion is not the default active version",
            phase="ssm_document_content_verification",
        )
    owner = data.get("Owner")
    if owner is not None and str(owner) != ACCOUNT_ID:
        _die(
            f"SSM document owner {owner!r} != {ACCOUNT_ID!r}",
            phase="ssm_document_content_verification",
        )


def validate_plan(plan: dict[str, Any]) -> None:
    if not isinstance(plan, dict):
        _die("plan JSON must be an object", phase="plan_validation")
    if "resource_changes" not in plan:
        _die("plan JSON missing resource_changes", phase="plan_validation")
    resource_changes = plan.get("resource_changes")
    if not isinstance(resource_changes, list):
        _die("resource_changes must be a list", phase="plan_validation")

    counts = {
        "create": 0,
        "update": 0,
        "replace": 0,
        "destroy": 0,
        "read": 0,
    }
    managed: dict[str, list[str]] = {}
    reads: dict[str, list[str]] = {}

    for rc in resource_changes:
        if not isinstance(rc, dict):
            _die("resource_changes entry must be an object", phase="plan_validation")
        addr = rc.get("address")
        if not isinstance(addr, str) or not addr:
            _die("resource change missing address", phase="plan_validation")
        change = rc.get("change") or {}
        if not isinstance(change, dict):
            _die(f"{addr}: change must be an object", phase="plan_validation")
        acts = change.get("actions")
        if not isinstance(acts, list) or not all(isinstance(a, str) for a in acts):
            _die(f"{addr}: actions must be a list of strings", phase="plan_validation")
        bucket = _actions_bucket(acts)
        if bucket is None:
            continue
        if bucket == "unknown":
            _die(f"{addr}: unknown/unsupported action form {acts}", phase="plan_validation")
        lower = addr.lower()
        if any(addr.startswith(p) for p in FORBIDDEN_PREFIXES) or any(
            s in lower for s in FORBIDDEN_SUBSTRINGS
        ):
            _die(f"forbidden resource change: {addr} actions={acts}", phase="plan_validation")
        counts[bucket] += 1
        mode = rc.get("mode")
        provider_is_data = mode == "data" or ".data." in addr or addr.startswith("data.")
        if bucket == "read" or provider_is_data:
            if bucket != "read":
                _die(
                    f"{addr}: data/read resource must use actions=['read'] (got {acts})",
                    phase="plan_validation",
                )
            reads[addr] = acts
        else:
            managed[addr] = acts

    expected_counts = {
        "create": EXPECTED_CREATE,
        "update": EXPECTED_UPDATE,
        "replace": EXPECTED_REPLACE,
        "destroy": EXPECTED_DESTROY,
        "read": EXPECTED_READ,
    }
    if counts != expected_counts:
        _die(f"plan counts {counts} != {expected_counts}", code=3, phase="plan_validation")

    if managed != EXPECTED_MANAGED:
        _die(
            f"managed addresses/actions {managed} != {EXPECTED_MANAGED}",
            code=4,
            phase="plan_validation",
        )
    if reads != EXPECTED_READS:
        _die(
            f"read addresses/actions {reads} != {EXPECTED_READS}",
            code=4,
            phase="plan_validation",
        )

    output_changes = plan.get("output_changes")
    if not isinstance(output_changes, dict):
        _die("plan JSON missing output_changes object", phase="plan_validation")
    normalized_outputs: dict[str, list[str]] = {}
    for name, oc in output_changes.items():
        if not isinstance(oc, dict):
            _die(f"output_changes.{name} must be an object", phase="plan_validation")
        acts = oc.get("actions")
        if not isinstance(acts, list):
            _die(f"output_changes.{name}.actions must be a list", phase="plan_validation")
        if acts == ["no-op"]:
            continue
        normalized_outputs[name] = acts
    if normalized_outputs != EXPECTED_OUTPUT_CHANGES:
        _die(
            f"output_changes {normalized_outputs} != {EXPECTED_OUTPUT_CHANGES}",
            code=4,
            phase="plan_validation",
        )

    ec2 = next((rc for rc in resource_changes if rc.get("address") == EC2_ADDRESS), None)
    if ec2 is None:
        _die(f"missing {EC2_ADDRESS}", phase="plan_validation")
    change = ec2.get("change") or {}
    acts = change.get("actions")
    if acts != ["update"]:
        _die(
            f"EC2 actions {acts} (replacement/destroy forbidden)",
            code=5,
            phase="plan_validation",
        )
    replace_paths = change.get("replace_paths")
    if replace_paths not in (None, [], ()):
        _die(
            f"EC2 replace_paths must be null/empty (got {replace_paths!r})",
            code=5,
            phase="plan_validation",
        )

    before = change.get("before")
    after = change.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        _die("EC2 before/after must be objects", code=6, phase="plan_validation")

    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed != ["user_data_base64"]:
        _die(
            f"EC2 changed attributes {changed} (only user_data_base64 allowed)",
            code=7,
            phase="plan_validation",
        )

    if before.get("id") != INSTANCE_ID or after.get("id") != INSTANCE_ID:
        _die(
            f"EC2 id must remain {INSTANCE_ID} "
            f"(before={before.get('id')!r} after={after.get('id')!r})",
            code=8,
            phase="plan_validation",
        )
    if before.get("user_data_replace_on_change", False) not in (False, None):
        _die(
            "EC2 before.user_data_replace_on_change must be false", code=8, phase="plan_validation"
        )
    if after.get("user_data_replace_on_change", False) not in (False, None):
        _die("EC2 after.user_data_replace_on_change must be false", code=8, phase="plan_validation")

    for key in EC2_CRITICAL_ATTRS:
        if key == "user_data_base64":
            continue
        if (key in before or key in after) and before.get(key) != after.get(key):
            _die(f"EC2 critical attribute changed: {key}", code=7, phase="plan_validation")

    after_unknown = change.get("after_unknown")
    if after_unknown is None:
        after_unknown = {}
    if not isinstance(after_unknown, dict):
        _die("EC2 after_unknown must be an object or null", code=9, phase="plan_validation")

    for key, value in after_unknown.items():
        if not _is_truthy_unknown(value):
            continue
        if key in EC2_CRITICAL_ATTRS or key in {
            "ami",
            "instance_type",
            "subnet_id",
            "vpc_security_group_ids",
            "iam_instance_profile",
            "root_block_device",
            "ebs_block_device",
            "tags",
            "tags_all",
            "id",
            "user_data_replace_on_change",
            "user_data_base64",
            "user_data",
        }:
            _die(
                f"EC2 after_unknown ambiguity for critical/config field: {key}",
                code=9,
                phase="plan_validation",
            )
        if key not in {
            "public_ip",
            "public_dns",
            "private_dns",
            "password_data",
            "primary_network_interface_id",
        }:
            _die(f"EC2 unexpected after_unknown field: {key}", code=9, phase="plan_validation")


def validate_plan_file(path: Path) -> None:
    plan = _load_json(path)
    if not isinstance(plan, dict):
        _die("plan JSON must be an object", phase="plan_validation")
    validate_plan(plan)
    print("OK plan assertions: structural counts/actions/outputs/EC2 user_data_base64-only")


def _require_regular_file(
    path: Path,
    *,
    exact_mode: int | None = None,
    max_mode: int | None = 0o600,
    phase: str = "plan_identity_mode",
) -> os.stat_result:
    if path.is_symlink():
        _die(f"refusing symlink: {path}", code=10, phase=phase)
    if not path.is_file():
        _die(f"not a regular file: {path}", code=10, phase=phase)
    st = path.stat()
    mode = stat.S_IMODE(st.st_mode)
    if mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX):
        _die(
            f"setuid/setgid/sticky bits forbidden on {path}: {oct(mode)}",
            phase=phase,
        )
    if exact_mode is not None:
        if mode != exact_mode:
            _die(
                f"file mode {oct(mode)} != required {oct(exact_mode)} on {path}",
                code=10,
                phase=phase,
            )
    elif max_mode is not None:
        if mode & ~max_mode:
            _die(
                f"file mode {oct(mode)} broader than allowed {oct(max_mode)} on {path}",
                code=10,
                phase=phase,
            )
        if mode & 0o022:
            _die(
                f"group/other writable permissions {oct(mode)} on {path}",
                code=10,
                phase=phase,
            )
        if mode & 0o044 and mode != 0o600 and mode & 0o077:
            _die(
                f"group/world-readable permissions {oct(mode)} on {path}",
                code=10,
                phase=phase,
            )
    return st


def sha256_file(path: Path) -> str:
    _require_regular_file(path, exact_mode=None, max_mode=0o600)
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def record_plan_identity(path: Path, *, work_dir: Path | None = None) -> dict[str, Any]:
    """Record immutable plan identity after chmod 0600. Uses current euid/egid only."""
    path = path.resolve()
    if path.is_symlink():
        _die(f"plan path must not be a symlink: {path}", phase="plan_identity_mode")
    try:
        os.chmod(path, 0o600)
    except OSError as exc:
        _die(f"cannot chmod plan to 0600: {exc}", phase="plan_identity_mode")

    st = _require_regular_file(path, exact_mode=0o600)
    euid = os.geteuid()
    egid = os.getegid()
    if st.st_uid != euid:
        _die(
            f"plan uid {st.st_uid} != current euid {euid}",
            phase="plan_identity_owner",
        )
    if st.st_gid != egid:
        _die(
            f"plan gid {st.st_gid} != current egid {egid}",
            phase="plan_identity_owner",
        )

    parent = path.parent.resolve()
    if work_dir is not None:
        work_resolved = work_dir.resolve()
        if parent != work_resolved and work_resolved not in path.parents:
            _die(
                f"plan path {path} is outside owned work directory {work_resolved}",
                phase="plan_identity_owner",
            )
        pst = work_resolved.stat()
        if pst.st_uid != euid:
            _die(
                f"work directory uid {pst.st_uid} != euid {euid}",
                phase="plan_identity_owner",
            )
        pmode = stat.S_IMODE(pst.st_mode)
        if pmode != 0o700:
            _die(
                f"work directory mode {oct(pmode)} != 0700",
                phase="plan_identity_mode",
            )
        if work_resolved.is_symlink():
            _die("work directory must not be a symlink", phase="plan_identity_mode")

    digest = sha256_file(path)
    identity = {
        "path": str(path),
        "dev": st.st_dev,
        "inode": st.st_ino,
        "size": st.st_size,
        "sha256": digest,
        "uid": st.st_uid,
        "gid": st.st_gid,
        "mode": stat.S_IMODE(st.st_mode),
        "euid": euid,
        "egid": egid,
    }
    print(canonical_json(identity))
    return identity


def verify_plan_identity(
    path: Path,
    *,
    expected_sha256: str,
    expected_inode: int | None = None,
    expected_size: int | None = None,
    expected_dev: int | None = None,
    expected_uid: int | None = None,
    expected_gid: int | None = None,
    expected_mode: int | None = 0o600,
    work_dir: Path | None = None,
    identity_file: Path | None = None,
) -> None:
    # Never accept caller-supplied expected uid/gid/mode as authority for recording;
    # verification compares against previously recorded identity and/or current euid/egid.
    path = path.resolve()
    if identity_file is not None:
        recorded = _load_json(identity_file)
        if not isinstance(recorded, dict):
            _die("plan identity file must be an object", phase="plan_identity_checksum")
        expected_sha256 = str(recorded["sha256"])
        expected_inode = int(recorded["inode"])
        expected_size = int(recorded["size"])
        expected_dev = int(recorded["dev"])
        expected_uid = int(recorded["uid"])
        expected_gid = int(recorded["gid"])
        expected_mode = int(recorded["mode"])
        recorded_path = str(recorded["path"])
        if str(path) != recorded_path:
            _die(
                f"plan path changed: {path} != {recorded_path}",
                phase="plan_identity_checksum",
            )
        if work_dir is None and recorded.get("path"):
            pass

    if path.is_symlink():
        _die(f"plan path must not be a symlink: {path}", phase="plan_identity_mode")
    st = _require_regular_file(
        path, exact_mode=expected_mode if expected_mode is not None else 0o600
    )

    euid = os.geteuid()
    egid = os.getegid()
    if st.st_uid != euid:
        _die(f"plan uid {st.st_uid} != current euid {euid}", phase="plan_identity_owner")
    if st.st_gid != egid:
        _die(f"plan gid {st.st_gid} != current egid {egid}", phase="plan_identity_owner")
    if expected_uid is not None and st.st_uid != expected_uid:
        _die(f"plan uid changed: {st.st_uid} != {expected_uid}", phase="plan_identity_owner")
    if expected_gid is not None and st.st_gid != expected_gid:
        _die(f"plan gid changed: {st.st_gid} != {expected_gid}", phase="plan_identity_owner")
    if expected_mode is not None and stat.S_IMODE(st.st_mode) != expected_mode:
        _die(
            f"plan mode {oct(stat.S_IMODE(st.st_mode))} != {oct(expected_mode)}",
            phase="plan_identity_mode",
        )
    if expected_inode is not None and st.st_ino != expected_inode:
        _die("plan inode changed before apply", phase="plan_identity_checksum")
    if expected_dev is not None and st.st_dev != expected_dev:
        _die("plan device id changed before apply", phase="plan_identity_checksum")
    if expected_size is not None and st.st_size != expected_size:
        _die("plan size changed before apply", phase="plan_identity_checksum")

    if work_dir is not None:
        work_resolved = work_dir.resolve()
        if work_resolved not in path.parents and path.parent.resolve() != work_resolved:
            _die(
                f"plan path {path} escaped owned work directory {work_resolved}",
                phase="plan_identity_owner",
            )
        pst = work_resolved.stat()
        if pst.st_uid != euid:
            _die(
                f"work directory uid {pst.st_uid} != euid {euid}",
                phase="plan_identity_owner",
            )
        if stat.S_IMODE(pst.st_mode) != 0o700:
            _die(
                f"work directory mode {oct(stat.S_IMODE(pst.st_mode))} != 0700",
                phase="plan_identity_mode",
            )

    digest = sha256_file(path)
    if digest != expected_sha256:
        _die(
            f"plan checksum mismatch: got {digest} expected {expected_sha256}",
            phase="plan_identity_checksum",
        )


def verify_artifact_mode(path: Path, *, exact_mode: int = 0o600) -> None:
    _require_regular_file(path, exact_mode=exact_mode)


def validate_host_evidence(
    data: dict[str, Any],
    *,
    phase: str,
    expected_nonce: str | None = None,
    max_age_seconds: int = 3600,
    expected_repository_sha: str | None = None,
) -> None:
    fail_phase = "host_evidence"
    if not isinstance(data, dict):
        _die("host evidence must be a JSON object", code=11, phase=fail_phase)
    if data.get("schema_version") != 1:
        _die("host evidence schema_version must be 1", code=11, phase=fail_phase)
    got_phase = data.get("phase")
    if got_phase != phase:
        _die(
            f"host evidence phase {got_phase!r} != required {phase!r}",
            code=11,
            phase="host_evidence_phase",
        )
    if data.get("instance_id") != INSTANCE_ID:
        _die("host evidence instance_id mismatch", code=11, phase=fail_phase)
    if data.get("account_id") != ACCOUNT_ID:
        _die("host evidence account_id mismatch", code=11, phase=fail_phase)
    if data.get("region") != REGION:
        _die("host evidence region mismatch", code=11, phase=fail_phase)

    nonce = data.get("nonce")
    if not isinstance(nonce, str) or not NONCE_RE.fullmatch(nonce):
        _die(
            "host evidence nonce missing or malformed (want 32 lowercase hex)",
            code=11,
            phase="host_evidence_nonce",
        )
    if expected_nonce is not None:
        validate_nonce_format(expected_nonce)
        if nonce != expected_nonce:
            _die(
                "host evidence nonce mismatch with run nonce",
                code=11,
                phase="host_evidence_nonce",
            )

    captured_at = data.get("captured_at")
    if not isinstance(captured_at, str) or not captured_at:
        _die("host evidence captured_at missing", code=11, phase=fail_phase)
    try:
        ts = captured_at.replace("Z", "+00:00")
        captured = datetime.fromisoformat(ts)
        if captured.tzinfo is None:
            _die("host evidence captured_at must be timezone-aware", code=11, phase=fail_phase)
        age = (datetime.now(UTC) - captured.astimezone(UTC)).total_seconds()
        if age < -60:
            _die("host evidence timestamp is in the future", code=11, phase="host_evidence_stale")
        if age > max_age_seconds:
            _die(
                f"host evidence is stale ({int(age)}s old)",
                code=11,
                phase="host_evidence_stale",
            )
    except AssertError:
        raise
    except Exception as exc:  # noqa: BLE001 — fail closed on bad timestamps
        _die(f"host evidence captured_at invalid: {exc}", code=11, phase=fail_phase)

    boot_id = data.get("boot_id")
    if not isinstance(boot_id, str) or not BOOT_ID_RE.fullmatch(boot_id):
        _die("host evidence boot_id invalid", code=11, phase=fail_phase)
    uptime = data.get("uptime_seconds")
    if not isinstance(uptime, int) or isinstance(uptime, bool) or uptime < 0:
        _die(
            "host evidence uptime_seconds must be a non-negative integer", code=11, phase=fail_phase
        )

    cloud = data.get("cloud_init_status")
    if cloud not in CLOUD_INIT_ALLOWLIST:
        _die(f"host evidence cloud_init_status not allowed: {cloud!r}", code=11, phase=fail_phase)

    release_id = data.get("release_id")
    if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
        _die("host evidence release_id invalid", code=11, phase=fail_phase)
    digest = data.get("image_digest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        _die("host evidence image_digest invalid", code=11, phase=fail_phase)

    current_pointer = data.get("current_pointer")
    if not isinstance(current_pointer, str) or not RELEASE_ID_RE.fullmatch(current_pointer):
        _die("host evidence current_pointer invalid", code=11, phase=fail_phase)
    if "previous_pointer" not in data:
        _die("host evidence previous_pointer missing", code=11, phase=fail_phase)
    previous_pointer = data.get("previous_pointer")
    if previous_pointer is not None and (
        not isinstance(previous_pointer, str) or not RELEASE_ID_RE.fullmatch(previous_pointer)
    ):
        _die("host evidence previous_pointer invalid", code=11, phase=fail_phase)

    marker = data.get("rollback_execution_marker_present")
    if marker is not False:
        _die(
            "host evidence rollback_execution_marker_present must be false",
            code=11,
            phase=fail_phase,
        )

    if "repository_sha" in data:
        repo_sha = data.get("repository_sha")
        if not isinstance(repo_sha, str) or not SHA1_OR_SHA256_RE.fullmatch(repo_sha):
            _die("host evidence repository_sha invalid", code=11, phase=fail_phase)
        if expected_repository_sha is not None and repo_sha != expected_repository_sha:
            _die(
                "host evidence repository_sha mismatch with approved repository SHA",
                code=11,
                phase=fail_phase,
            )


def validate_host_evidence_file(
    path: Path,
    *,
    phase: str,
    expected_nonce: str | None = None,
    expected_repository_sha: str | None = None,
    max_age_seconds: int = 3600,
    file_safety_phase: str = "plan_identity_mode",
) -> dict[str, Any]:
    _require_regular_file(
        path, exact_mode=None, max_mode=0o600, phase=file_safety_phase
    )
    data = _load_json(path)
    if not isinstance(data, dict):
        _die("host evidence must be a JSON object", code=11, phase="host_evidence")
    validate_host_evidence(
        data,
        phase=phase,
        expected_nonce=expected_nonce,
        expected_repository_sha=expected_repository_sha,
        max_age_seconds=max_age_seconds,
    )
    print(f"OK host evidence ({phase})")
    return data


HOST_EVIDENCE_RETAINED_NAMES = {
    "pre-apply": "host-evidence-pre.json",
    "post-apply": "host-evidence-post.json",
}

HOST_EVIDENCE_RETENTION_PHASE = "host_evidence_retention"


class _PublishedRetentionArtifact(NamedTuple):
    """Identity of a final path published by the current retain invocation."""

    path: Path
    expected_name: str
    work_dir: Path
    st_dev: int
    st_ino: int
    st_uid: int
    st_gid: int


def _read_regular_file_bytes_nofollow(
    path: Path, *, phase: str = HOST_EVIDENCE_RETENTION_PHASE
) -> bytes:
    """Read exact file bytes without following symlinks and without shell interpolation."""
    if path.is_symlink():
        _die(f"refusing symlink: {path}", code=11, phase=phase)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        _die(f"cannot open evidence file {path}: {exc}", code=11, phase=phase)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            _die(
                f"evidence path is not a regular file: {path}",
                code=11,
                phase=phase,
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _safe_unlink_published_retention_artifact(
    artifact: _PublishedRetentionArtifact, *, phase: str = HOST_EVIDENCE_RETENTION_PHASE
) -> None:
    """Unlink a final path only when it still matches this invocation's publication.

    Uses lstat (no symlink follow). Refuses ambiguous cleanup rather than deleting.
    Never removes a pre-existing destination this invocation did not publish.
    """
    path = artifact.path
    if path.name != artifact.expected_name:
        _die(
            f"refusing cleanup: basename mismatch for {path}",
            code=11,
            phase=phase,
        )
    try:
        parent = path.parent.resolve()
    except OSError as exc:
        _die(f"refusing cleanup: cannot resolve parent of {path}: {exc}", code=11, phase=phase)
    if parent != artifact.work_dir:
        _die(
            f"refusing cleanup: {path} is outside authoritative workdir {artifact.work_dir}",
            code=11,
            phase=phase,
        )
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        _die(f"refusing cleanup: cannot lstat {path}: {exc}", code=11, phase=phase)
    if stat.S_ISLNK(st.st_mode):
        _die(f"refusing cleanup: {path} is a symlink", code=11, phase=phase)
    if not stat.S_ISREG(st.st_mode):
        _die(f"refusing cleanup: {path} is not a regular file", code=11, phase=phase)
    if st.st_dev != artifact.st_dev or st.st_ino != artifact.st_ino:
        _die(
            f"refusing cleanup: {path} device/inode changed since publication",
            code=11,
            phase=phase,
        )
    if st.st_uid != artifact.st_uid or st.st_gid != artifact.st_gid:
        _die(
            f"refusing cleanup: {path} ownership changed since publication",
            code=11,
            phase=phase,
        )
    try:
        os.unlink(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        _die(f"failed to cleanup published retention artifact {path}: {exc}", code=11, phase=phase)


def _atomic_publish_exclusive(
    raw: bytes, *, work_dir: Path, dest: Path
) -> _PublishedRetentionArtifact:
    """Write bytes via a private temp file in work_dir, then publish without replace.

    Destination must not already exist. Temp files are cleaned up on any failure.
    The published file is never partially visible under the final name.
    Returns publication identity for invocation-scoped transactional cleanup.
    """
    fail_phase = HOST_EVIDENCE_RETENTION_PHASE
    euid = os.geteuid()
    egid = os.getegid()
    if dest.name == "" or dest.parent.resolve() != work_dir:
        _die(
            f"retention destination must be a direct child of workdir: {dest}",
            code=11,
            phase=fail_phase,
        )
    if dest.exists() or dest.is_symlink():
        _die(f"refusing to overwrite existing path: {dest}", code=11, phase=fail_phase)

    tmp_path: Path | None = None
    linked = False
    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{dest.name}.",
            suffix=".tmp",
            dir=str(work_dir),
        )
        tmp_path = Path(tmp_name)
        try:
            os.write(fd, raw)
            os.fsync(fd)
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)

        if tmp_path.is_symlink():
            _die("temporary evidence file must not be a symlink", code=11, phase=fail_phase)
        tst = tmp_path.stat()
        if tst.st_uid != euid or tst.st_gid != egid:
            _die(
                "temporary evidence file ownership mismatch with current euid/egid",
                code=11,
                phase=fail_phase,
            )
        if stat.S_IMODE(tst.st_mode) != 0o600:
            _die(
                f"temporary evidence file mode {oct(stat.S_IMODE(tst.st_mode))} != 0600",
                code=11,
                phase=fail_phase,
            )

        # Hard-link publish is atomic and fails closed if dest already exists.
        try:
            os.link(tmp_path, dest)
            linked = True
        except FileExistsError:
            _die(f"refusing to overwrite existing path: {dest}", code=11, phase=fail_phase)
        except OSError as exc:
            _die(f"failed to publish retained file {dest}: {exc}", code=11, phase=fail_phase)

        try:
            published = os.lstat(dest)
        except OSError as exc:
            _die(f"failed to lstat published file {dest}: {exc}", code=11, phase=fail_phase)
        if stat.S_ISLNK(published.st_mode) or not stat.S_ISREG(published.st_mode):
            _die(f"published path is not a regular file: {dest}", code=11, phase=fail_phase)
        if published.st_uid != euid or published.st_gid != egid:
            _die(
                "published file ownership mismatch with current euid/egid",
                code=11,
                phase=fail_phase,
            )
        if stat.S_IMODE(published.st_mode) != 0o600:
            _die(
                f"published file mode {oct(stat.S_IMODE(published.st_mode))} != 0600",
                code=11,
                phase=fail_phase,
            )
        return _PublishedRetentionArtifact(
            path=dest,
            expected_name=dest.name,
            work_dir=work_dir,
            st_dev=published.st_dev,
            st_ino=published.st_ino,
            st_uid=published.st_uid,
            st_gid=published.st_gid,
        )
    except BaseException as exc:
        if linked:
            with suppress(OSError):
                os.unlink(dest)
        if isinstance(exc, AssertError):
            raise
        if isinstance(exc, Exception):
            _die(f"atomic evidence publish failed: {exc}", code=11, phase=fail_phase)
        raise
    finally:
        if tmp_path is not None:
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)


def _resolve_retention_work_dir(work_dir: Path, *, phase: str) -> Path:
    """Validate workdir via lstat (no follow), then resolve and bind identity."""
    try:
        lst = os.lstat(work_dir)
    except OSError as exc:
        _die(f"work directory missing: {work_dir}: {exc}", code=11, phase=phase)
    if stat.S_ISLNK(lst.st_mode):
        _die("work directory must not be a symlink", code=11, phase=phase)
    if not stat.S_ISDIR(lst.st_mode):
        _die(f"work directory is not a directory: {work_dir}", code=11, phase=phase)

    try:
        work_resolved = work_dir.resolve()
    except OSError as exc:
        _die(f"cannot resolve work directory {work_dir}: {exc}", code=11, phase=phase)
    if not work_resolved.is_dir():
        _die(f"work directory missing: {work_resolved}", code=11, phase=phase)
    try:
        rst = os.lstat(work_resolved)
    except OSError as exc:
        _die(f"cannot lstat resolved work directory: {exc}", code=11, phase=phase)
    if stat.S_ISLNK(rst.st_mode):
        _die("resolved work directory must not be a symlink", code=11, phase=phase)
    if (rst.st_dev, rst.st_ino) != (lst.st_dev, lst.st_ino):
        _die(
            "work directory resolve escaped authoritative directory identity",
            code=11,
            phase=phase,
        )

    euid = os.geteuid()
    if rst.st_uid != euid:
        _die(
            f"work directory uid {rst.st_uid} != current euid {euid}",
            code=11,
            phase=phase,
        )
    if stat.S_IMODE(rst.st_mode) != 0o700:
        _die(
            f"work directory mode {oct(stat.S_IMODE(rst.st_mode))} != 0700",
            code=11,
            phase=phase,
        )
    return work_resolved


def _retention_reraise(exc: BaseException, *, phase: str) -> None:
    """Normalize retain-path failures to FAIL_PHASE=host_evidence_retention."""
    if isinstance(exc, AssertError):
        if exc.phase == phase:
            raise exc
        _die(str(exc), code=exc.code, phase=phase)
    _die(f"host evidence retention failed: {exc}", code=11, phase=phase)


def retain_validated_host_evidence(
    source: Path,
    *,
    work_dir: Path,
    phase: str,
    expected_nonce: str,
    expected_repository_sha: str | None = None,
    max_age_seconds: int = 3600,
) -> dict[str, Any]:
    """Retain validated host evidence into the authoritative work directory.

    Order of authority:
      1) validate external/operator-supplied source with existing evidence rules
      2) atomically publish an exact byte copy into work_dir
      3) re-parse and revalidate the retained destination
      4) bind SHA-256 so audits can prove retained == validated source

    Evidence JSON and its `.sha256` sidecar are one logical publication unit.
    On any failure after this invocation publishes a final path, those
    invocation-owned finals are removed (never pre-existing paths). Retention
    failure raises AssertError with FAIL_PHASE=host_evidence_retention.
    """
    fail_phase = HOST_EVIDENCE_RETENTION_PHASE
    if phase not in HOST_EVIDENCE_RETAINED_NAMES:
        _die(f"unsupported evidence phase for retention: {phase!r}", code=11, phase=fail_phase)
    validate_nonce_format(expected_nonce)

    work_resolved = _resolve_retention_work_dir(work_dir, phase=fail_phase)
    euid = os.geteuid()
    egid = os.getegid()

    dest_name = HOST_EVIDENCE_RETAINED_NAMES[phase]
    binding_name = f"{dest_name}.sha256"
    dest = work_resolved / dest_name
    binding_path = work_resolved / binding_name

    if dest.exists() or dest.is_symlink():
        _die(
            f"refusing to overwrite existing retained evidence: {dest} "
            "(do not manually inject evidence into a completed workdir)",
            code=11,
            phase=fail_phase,
        )
    if binding_path.exists() or binding_path.is_symlink():
        _die(
            f"refusing to overwrite existing evidence binding: {binding_path}",
            code=11,
            phase=fail_phase,
        )

    # Source must pass the existing validator before any retained copy is created.
    if source.is_symlink():
        _die(f"refusing symlink source evidence: {source}", code=11, phase=fail_phase)
    source_st = _require_regular_file(
        source, exact_mode=None, max_mode=0o600, phase=fail_phase
    )
    if source_st.st_uid != euid or source_st.st_gid != egid:
        _die(
            "source evidence ownership mismatch with current euid/egid",
            code=11,
            phase=fail_phase,
        )
    # Source semantic authority keeps host_evidence_* phases; file-safety uses
    # host_evidence_retention via file_safety_phase.
    validate_host_evidence_file(
        source,
        phase=phase,
        expected_nonce=expected_nonce,
        expected_repository_sha=expected_repository_sha,
        max_age_seconds=max_age_seconds,
        file_safety_phase=fail_phase,
    )

    raw = _read_regular_file_bytes_nofollow(source, phase=fail_phase)
    source_digest = hashlib.sha256(raw).hexdigest()

    published_dest: _PublishedRetentionArtifact | None = None
    published_binding: _PublishedRetentionArtifact | None = None
    try:
        published_dest = _atomic_publish_exclusive(raw, work_dir=work_resolved, dest=dest)

        # Destination file-safety: regular, non-symlink, euid/egid, mode 0600.
        if dest.is_symlink():
            _die(f"retained evidence must not be a symlink: {dest}", code=11, phase=fail_phase)
        st = _require_regular_file(dest, exact_mode=0o600, phase=fail_phase)
        if st.st_uid != euid:
            _die(
                f"retained evidence uid {st.st_uid} != current euid {euid}",
                code=11,
                phase=fail_phase,
            )
        if st.st_gid != egid:
            _die(
                f"retained evidence gid {st.st_gid} != current egid {egid}",
                code=11,
                phase=fail_phase,
            )

        # Re-parse and revalidate retained destination with the same evidence authority.
        try:
            validate_host_evidence_file(
                dest,
                phase=phase,
                expected_nonce=expected_nonce,
                expected_repository_sha=expected_repository_sha,
                max_age_seconds=max_age_seconds,
                file_safety_phase=fail_phase,
            )
        except AssertError as exc:
            _retention_reraise(exc, phase=fail_phase)

        retained_raw = _read_regular_file_bytes_nofollow(dest, phase=fail_phase)
        retained_digest = hashlib.sha256(retained_raw).hexdigest()
        if retained_raw != raw or retained_digest != source_digest:
            _die(
                "retained evidence is not byte-for-byte identical to the validated source",
                code=11,
                phase=fail_phase,
            )

        binding_body = (f"{retained_digest}  {dest_name}\n").encode("ascii")
        published_binding = _atomic_publish_exclusive(
            binding_body, work_dir=work_resolved, dest=binding_path
        )
        if binding_path.is_symlink():
            _die(
                f"evidence binding must not be a symlink: {binding_path}",
                code=11,
                phase=fail_phase,
            )
        bst = _require_regular_file(binding_path, exact_mode=0o600, phase=fail_phase)
        if bst.st_uid != euid or bst.st_gid != egid:
            _die("evidence binding ownership mismatch", code=11, phase=fail_phase)
        if binding_path.read_bytes() != binding_body:
            _die("evidence binding contents corrupted", code=11, phase=fail_phase)

        # Complete-pair authority: both finals must still be the published artifacts.
        for artifact in (published_dest, published_binding):
            cur = os.lstat(artifact.path)
            if stat.S_ISLNK(cur.st_mode) or not stat.S_ISREG(cur.st_mode):
                _die(
                    f"retained pair member is not a regular file: {artifact.path}",
                    code=11,
                    phase=fail_phase,
                )
            if cur.st_dev != artifact.st_dev or cur.st_ino != artifact.st_ino:
                _die(
                    f"retained pair member identity changed: {artifact.path}",
                    code=11,
                    phase=fail_phase,
                )
            if cur.st_uid != euid or cur.st_gid != egid:
                _die(
                    f"retained pair ownership mismatch: {artifact.path}",
                    code=11,
                    phase=fail_phase,
                )
            if stat.S_IMODE(cur.st_mode) != 0o600:
                _die(
                    f"retained pair mode != 0600: {artifact.path}",
                    code=11,
                    phase=fail_phase,
                )

        binding = {
            "phase": phase,
            "path": str(dest),
            "sha256": retained_digest,
            "source_sha256": source_digest,
            "size": len(raw),
            "mode": 0o600,
            "uid": euid,
            "gid": egid,
            "nonce": expected_nonce,
            "binding_path": str(binding_path),
        }
        print(f"OK retained host evidence ({phase}) sha256={retained_digest}")
        print(canonical_json(binding))
        return binding
    except BaseException as exc:
        # Roll back only finals published by this invocation (sidecar first).
        cleanup_error: AssertError | None = None
        for artifact in (published_binding, published_dest):
            if artifact is None:
                continue
            try:
                _safe_unlink_published_retention_artifact(artifact, phase=fail_phase)
            except AssertError as cleanup_exc:
                cleanup_error = cleanup_exc
        # Scrub any private temps left in the workdir for these basenames.
        for pattern in (f".{dest_name}.*.tmp", f".{binding_name}.*.tmp"):
            for tmp in work_resolved.glob(pattern):
                with suppress(OSError):
                    try:
                        if not stat.S_ISLNK(os.lstat(tmp).st_mode):
                            tmp.unlink(missing_ok=True)
                    except OSError:
                        pass
        if cleanup_error is not None:
            _retention_reraise(cleanup_error, phase=fail_phase)
        _retention_reraise(exc, phase=fail_phase)
        raise  # pragma: no cover — _retention_reraise always raises


def compare_host_evidence(
    pre: dict[str, Any],
    post: dict[str, Any],
    *,
    expected_nonce: str | None = None,
    expected_repository_sha: str | None = None,
) -> dict[str, Any]:
    validate_host_evidence(
        pre,
        phase="pre-apply",
        expected_nonce=expected_nonce,
        expected_repository_sha=expected_repository_sha,
        max_age_seconds=24 * 3600,
    )
    validate_host_evidence(
        post,
        phase="post-apply",
        expected_nonce=expected_nonce,
        expected_repository_sha=expected_repository_sha,
        max_age_seconds=24 * 3600,
    )

    if pre["nonce"] != post["nonce"]:
        _die(
            "pre/post host evidence nonce mismatch",
            code=12,
            phase="host_evidence_nonce",
        )
    if expected_nonce is not None and pre["nonce"] != expected_nonce:
        _die(
            "host evidence nonce does not match run nonce",
            code=12,
            phase="host_evidence_nonce",
        )
    # Reject swapped evidence submissions (already phase-checked; keep explicit).
    if pre.get("phase") != "pre-apply" or post.get("phase") != "post-apply":
        _die("host evidence phases are not pre-apply/post-apply", phase="host_evidence_phase")

    if pre["release_id"] != post["release_id"]:
        _die(
            f"release_id mismatch pre={pre['release_id']} post={post['release_id']}",
            code=12,
            phase="release_integrity",
        )
    if pre["image_digest"] != post["image_digest"]:
        _die(
            f"image_digest mismatch pre={pre['image_digest']} post={post['image_digest']}",
            code=12,
            phase="release_integrity",
        )
    if pre["current_pointer"] != post["current_pointer"]:
        _die("current_pointer changed across maintenance", code=12, phase="release_integrity")
    if pre.get("previous_pointer") != post.get("previous_pointer"):
        _die("previous_pointer changed across maintenance", code=12, phase="release_integrity")
    if post.get("rollback_execution_marker_present") is not False:
        _die(
            "rollback execution marker present after maintenance",
            code=12,
            phase="release_integrity",
        )
    if post["cloud_init_status"] not in CLOUD_INIT_ALLOWLIST:
        _die("post cloud-init status not accepted", code=12, phase="release_integrity")
    if post["cloud_init_status"] == "error":
        _die("post cloud-init status is error", code=12, phase="release_integrity")

    boot_changed = pre["boot_id"] != post["boot_id"]
    uptime_reset = post["uptime_seconds"] < pre["uptime_seconds"]
    stop_start_consistent = boot_changed and uptime_reset
    result = {
        "boot_id_pre": pre["boot_id"],
        "boot_id_post": post["boot_id"],
        "boot_id_changed": boot_changed,
        "uptime_pre": pre["uptime_seconds"],
        "uptime_post": post["uptime_seconds"],
        "uptime_reset": uptime_reset,
        "stop_start_evidence_consistent": stop_start_consistent,
        "release_id": pre["release_id"],
        "image_digest": pre["image_digest"],
        "cloud_init_pre": pre["cloud_init_status"],
        "cloud_init_post": post["cloud_init_status"],
        "nonce": pre["nonce"],
    }
    print(json.dumps(result, sort_keys=True))
    return result


def validate_alb_dns(dns: str) -> None:
    if not isinstance(dns, str) or not ALB_DNS_RE.fullmatch(dns):
        _die(f"ALB DNS rejected (expected ELB hostname): {dns!r}", code=13, phase="preflight")


def validate_tg_arn(arn: str) -> None:
    if not isinstance(arn, str) or not TG_ARN_RE.fullmatch(arn):
        _die(f"target group ARN rejected: {arn!r}", code=13, phase="preflight")


def _cmd_validate_plan(args: argparse.Namespace) -> int:
    validate_plan_file(Path(args.path))
    return 0


def _cmd_sha256(args: argparse.Namespace) -> int:
    digest = sha256_file(Path(args.path))
    print(digest)
    return 0


def _cmd_generate_nonce(_args: argparse.Namespace) -> int:
    print(generate_nonce())
    return 0


def _cmd_record_plan_identity(args: argparse.Namespace) -> int:
    work_dir = Path(args.work_dir) if args.work_dir else None
    identity = record_plan_identity(Path(args.path), work_dir=work_dir)
    if args.out:
        out = Path(args.out)
        out.write_text(canonical_json(identity) + "\n", encoding="utf-8")
        os.chmod(out, 0o600)
    return 0


def _cmd_verify_plan_identity(args: argparse.Namespace) -> int:
    # Caller-supplied uid/gid/mode are never accepted as authority; identity file
    # recorded by this helper (from current euid/egid) or checksum+inode fields.
    identity_file = Path(args.identity_file) if args.identity_file else None
    sha = args.sha256 or ""
    if identity_file is None and not sha:
        _die(
            "verify-plan-identity requires --sha256 or --identity-file",
            phase="plan_identity_checksum",
        )
    verify_plan_identity(
        Path(args.path),
        expected_sha256=sha,
        expected_inode=args.inode,
        expected_size=args.size,
        expected_dev=args.dev,
        expected_uid=None,
        expected_gid=None,
        expected_mode=0o600,
        work_dir=Path(args.work_dir) if args.work_dir else None,
        identity_file=identity_file,
    )
    print("OK plan identity")
    return 0


def _cmd_verify_artifact_mode(args: argparse.Namespace) -> int:
    verify_artifact_mode(Path(args.path), exact_mode=int(args.mode, 8))
    print("OK artifact mode")
    return 0


def _cmd_validate_host_evidence(args: argparse.Namespace) -> int:
    validate_host_evidence_file(
        Path(args.path),
        phase=args.phase,
        expected_nonce=args.nonce,
        expected_repository_sha=args.repository_sha,
        max_age_seconds=args.max_age_seconds,
    )
    return 0


def _cmd_retain_host_evidence(args: argparse.Namespace) -> int:
    if not args.nonce:
        _die(
            "retain-host-evidence requires --nonce (run-generated nonce)",
            phase="host_evidence_nonce",
        )
    retain_validated_host_evidence(
        Path(args.path),
        work_dir=Path(args.work_dir),
        phase=args.phase,
        expected_nonce=args.nonce,
        expected_repository_sha=args.repository_sha or None,
        max_age_seconds=args.max_age_seconds,
    )
    return 0


def _cmd_compare_host_evidence(args: argparse.Namespace) -> int:
    pre = _load_json(Path(args.pre))
    post = _load_json(Path(args.post))
    if not isinstance(pre, dict) or not isinstance(post, dict):
        _die("pre/post evidence must be objects", phase="host_evidence")
    compare_host_evidence(
        pre,
        post,
        expected_nonce=args.nonce,
        expected_repository_sha=args.repository_sha,
    )
    return 0


def _cmd_validate_alb_dns(args: argparse.Namespace) -> int:
    validate_alb_dns(args.dns)
    print("OK alb dns")
    return 0


def _cmd_validate_tg_arn(args: argparse.Namespace) -> int:
    validate_tg_arn(args.arn)
    print("OK tg arn")
    return 0


def _cmd_validate_iam_allowlist(args: argparse.Namespace) -> int:
    policy = _load_json(Path(args.path))
    if not isinstance(policy, dict):
        _die("IAM policy document must be an object", phase="iam_policy_verification")
    validate_iam_deploy_allow_policy(policy)
    if args.deny_path:
        deny = _load_json(Path(args.deny_path))
        if not isinstance(deny, dict):
            _die("IAM deny policy must be an object", phase="iam_policy_verification")
        validate_iam_deploy_deny_policy(deny)
    print("OK IAM policy verification")
    return 0


def _cmd_validate_ssm_document(args: argparse.Namespace) -> int:
    data = _load_json(Path(args.path))
    if not isinstance(data, dict):
        _die("SSM document metadata must be an object", phase="ssm_document_content_verification")
    validate_ssm_document_meta(data, expected_name=args.name)
    print("OK ssm document meta")
    return 0


def _cmd_validate_ssm_content(args: argparse.Namespace) -> int:
    data = _load_json(Path(args.path))
    if not isinstance(data, dict):
        _die("SSM document payload must be an object", phase="ssm_document_content_verification")
    validate_ssm_document_content(
        data,
        expected_name=args.name,
        expected_version=args.version,
    )
    print("OK ssm document content")
    return 0


def _cmd_canonical_json(args: argparse.Namespace) -> int:
    data = _load_json(Path(args.path))
    print(canonical_json(data))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("validate-plan")
    sp.add_argument("path")
    sp.set_defaults(func=_cmd_validate_plan)

    sp = sub.add_parser("sha256")
    sp.add_argument("path")
    sp.set_defaults(func=_cmd_sha256)

    sp = sub.add_parser("generate-nonce")
    sp.set_defaults(func=_cmd_generate_nonce)

    sp = sub.add_parser("record-plan-identity")
    sp.add_argument("path")
    sp.add_argument("--work-dir", default=None)
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=_cmd_record_plan_identity)

    sp = sub.add_parser("verify-plan-identity")
    sp.add_argument("path")
    sp.add_argument("--sha256", required=False, default="")
    sp.add_argument("--inode", type=int, default=None)
    sp.add_argument("--size", type=int, default=None)
    sp.add_argument("--dev", type=int, default=None)
    sp.add_argument("--work-dir", default=None)
    sp.add_argument("--identity-file", default=None)
    sp.set_defaults(func=_cmd_verify_plan_identity)

    sp = sub.add_parser("verify-artifact-mode")
    sp.add_argument("path")
    sp.add_argument("--mode", default="600")
    sp.set_defaults(func=_cmd_verify_artifact_mode)

    sp = sub.add_parser("validate-host-evidence")
    sp.add_argument("path")
    sp.add_argument("--phase", required=True, choices=("pre-apply", "post-apply"))
    sp.add_argument("--nonce", default=None)
    sp.add_argument("--repository-sha", default=None)
    sp.add_argument("--max-age-seconds", type=int, default=3600)
    sp.set_defaults(func=_cmd_validate_host_evidence)

    sp = sub.add_parser("retain-host-evidence")
    sp.add_argument("path", help="Validated external/operator-supplied host-evidence JSON")
    sp.add_argument("--work-dir", required=True)
    sp.add_argument("--phase", required=True, choices=("pre-apply", "post-apply"))
    sp.add_argument("--nonce", required=True)
    sp.add_argument("--repository-sha", default=None)
    sp.add_argument("--max-age-seconds", type=int, default=3600)
    sp.set_defaults(func=_cmd_retain_host_evidence)

    sp = sub.add_parser("compare-host-evidence")
    sp.add_argument("pre")
    sp.add_argument("post")
    sp.add_argument("--nonce", default=None)
    sp.add_argument("--repository-sha", default=None)
    sp.set_defaults(func=_cmd_compare_host_evidence)

    sp = sub.add_parser("validate-alb-dns")
    sp.add_argument("dns")
    sp.set_defaults(func=_cmd_validate_alb_dns)

    sp = sub.add_parser("validate-tg-arn")
    sp.add_argument("arn")
    sp.set_defaults(func=_cmd_validate_tg_arn)

    sp = sub.add_parser("validate-iam-allowlist")
    sp.add_argument("path")
    sp.add_argument("--deny-path", default=None)
    sp.add_argument("--deploy-doc", default=SSM_DEPLOY_DOC_NAME)
    sp.add_argument("--rollback-doc", default=SSM_DOC_NAME)
    sp.set_defaults(func=_cmd_validate_iam_allowlist)

    sp = sub.add_parser("validate-ssm-document")
    sp.add_argument("path")
    sp.add_argument("--name", default=SSM_DOC_NAME)
    sp.set_defaults(func=_cmd_validate_ssm_document)

    sp = sub.add_parser("validate-ssm-content")
    sp.add_argument("path")
    sp.add_argument("--name", default=SSM_DOC_NAME)
    sp.add_argument("--version", default=None)
    sp.set_defaults(func=_cmd_validate_ssm_content)

    sp = sub.add_parser("canonical-json")
    sp.add_argument("path")
    sp.set_defaults(func=_cmd_canonical_json)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.cmd == "verify-plan-identity" and not args.identity_file and not args.sha256:
            _die(
                "verify-plan-identity requires --sha256 or --identity-file",
                phase="plan_identity_checksum",
            )
        return int(args.func(args))
    except AssertError as exc:
        print(f"FAIL_PHASE={exc.phase}", file=sys.stderr)
        print(f"FAIL: {exc}", file=sys.stderr)
        return int(exc.code)


if __name__ == "__main__":
    sys.exit(main())
