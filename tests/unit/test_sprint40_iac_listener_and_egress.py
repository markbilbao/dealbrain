"""Static guards for the Sprint 40 ALB listener and API egress decisions.

The HTTP-forward listener and the all-protocol API egress rule are source
defects. These tests read the committed Terraform and fail if either returns.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALB = ROOT / "infra/terraform/modules/alb/main.tf"
ALB_VARIABLES = ROOT / "infra/terraform/modules/alb/variables.tf"
SECURITY_GROUPS = ROOT / "infra/terraform/modules/security_groups/main.tf"
EC2 = ROOT / "infra/terraform/modules/ec2/main.tf"
LOGGING = ROOT / "infra/terraform/modules/logging/main.tf"
NETWORKING = ROOT / "infra/terraform/modules/networking/main.tf"
IAM = ROOT / "infra/terraform/modules/iam/main.tf"
RDS = ROOT / "infra/terraform/modules/rds/main.tf"
STAGING_EXAMPLE = ROOT / "infra/terraform/environments/staging/terraform.tfvars.example"
RELEASE_ARTIFACTS = ROOT / "infra/terraform/modules/release_artifacts/main.tf"
STAGING = ROOT / "infra/terraform/environments/staging/main.tf"
PRODUCTION = ROOT / "infra/terraform/environments/production/main.tf"
STAGING_VARIABLES = ROOT / "infra/terraform/environments/staging/variables.tf"
PRODUCTION_VARIABLES = ROOT / "infra/terraform/environments/production/variables.tf"

_RESOURCE = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', re.MULTILINE)


def _blocks(text: str) -> list[tuple[str, str, str]]:
    """Return resource type, name, and body for each top-level resource."""
    found: list[tuple[str, str, str]] = []
    for match in _RESOURCE.finditer(text):
        start = match.end()
        depth = 1
        index = start
        while index < len(text) and depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        found.append((match.group(1), match.group(2), text[start : index - 1]))
    return found


def _one(blocks: list[tuple[str, str, str]], resource_type: str, name: str) -> str:
    matches = [
        body
        for kind, resource_name, body in blocks
        if kind == resource_type and resource_name == name
    ]
    assert len(matches) == 1, f"{resource_type}.{name} count is {len(matches)}"
    return matches[0]


def test_http_forward_listener_cannot_return() -> None:
    text = ALB.read_text(encoding="utf-8")
    assert "http_forward" not in text
    blocks = _blocks(text)
    listeners = {name: body for kind, name, body in blocks if kind == "aws_lb_listener"}
    assert set(listeners) == {"https", "http_redirect"}

    https = listeners["https"]
    assert 'count = var.certificate_arn != "" ? 1 : 0' in https
    assert "port              = 443" in https
    assert 'protocol          = "HTTPS"' in https
    assert 'type             = "forward"' in https

    redirect = listeners["http_redirect"]
    assert "count = local.http_redirect ? 1 : 0" in redirect
    assert "port              = 80" in redirect
    assert 'protocol          = "HTTP"' in redirect
    assert 'type = "redirect"' in redirect
    assert 'type             = "forward"' not in redirect
    assert 'port        = "443"' in redirect
    assert 'protocol    = "HTTPS"' in redirect
    assert 'http_redirect = var.certificate_arn != "" && var.enable_http_redirect' in text

    variables = ALB_VARIABLES.read_text(encoding="utf-8")
    assert "HTTP only" not in variables
    assert "HTTP-only" not in variables
    for path in (STAGING_VARIABLES, PRODUCTION_VARIABLES):
        description = path.read_text(encoding="utf-8")
        assert "HTTP-only bootstrap" not in description
        assert "HTTP only for bootstrap" not in description


def test_unrestricted_api_egress_cannot_return() -> None:
    text = SECURITY_GROUPS.read_text(encoding="utf-8")
    assert "api_all" not in text
    assert 'ip_protocol       = "-1"' not in text
    assert 'protocol        = "-1"' not in text
    assert 'protocol    = "-1"' not in text
    blocks = _blocks(text)
    api_egress = {
        name: body
        for kind, name, body in blocks
        if kind == "aws_vpc_security_group_egress_rule"
        and re.search(
            r"(?m)^\s*security_group_id\s+=\s+aws_security_group\.api\.id\s*$",
            body,
        )
    }
    assert set(api_egress) == {"api_https", "api_to_rds"}

    https = api_egress["api_https"]
    assert 'ip_protocol       = "tcp"' in https
    assert "from_port         = 443" in https
    assert "to_port           = 443" in https
    assert 'cidr_ipv4         = "0.0.0.0/0"' in https
    assert "referenced_security_group_id" not in https

    database = api_egress["api_to_rds"]
    assert 'ip_protocol                  = "tcp"' in database
    assert "from_port                    = 5432" in database
    assert "to_port                      = 5432" in database
    assert "referenced_security_group_id = aws_security_group.rds.id" in database
    assert "cidr_ipv4" not in database

    for body in api_egress.values():
        assert "from_port" in body
        assert re.search(r"from_port\s+=\s+53\b", body) is None
        assert re.search(r"to_port\s+=\s+53\b", body) is None
    rds = _one(blocks, "aws_security_group", "rds")
    assert "egress = []" in rds
    assert "0.0.0.0/0" not in rds


def test_alb_is_the_public_entry_and_api_host_stays_private() -> None:
    alb_blocks = _blocks(ALB.read_text(encoding="utf-8"))
    load_balancer = _one(alb_blocks, "aws_lb", "this")
    assert "internal           = false" in load_balancer
    assert 'load_balancer_type = "application"' in load_balancer

    groups = _blocks(SECURITY_GROUPS.read_text(encoding="utf-8"))
    api_ingress = [
        (name, body)
        for kind, name, body in groups
        if kind == "aws_vpc_security_group_ingress_rule" and "aws_security_group.api.id" in body
    ]
    assert [name for name, _body in api_ingress] == ["api_from_alb"]
    body = api_ingress[0][1]
    assert "from_port                    = 8000" in body
    assert "to_port                      = 8000" in body
    assert "referenced_security_group_id = aws_security_group.alb.id" in body
    assert "cidr_ipv4" not in body
    assert "0.0.0.0/0" not in body

    ec2 = EC2.read_text(encoding="utf-8")
    assert "associate_public_ip_address = var.associate_public_ip" in ec2
    for path in (STAGING, PRODUCTION):
        environment = path.read_text(encoding="utf-8")
        assert "associate_public_ip       = false" in environment
        assert 'module "alb"' in environment
        assert 'module "ec2"' in environment
        assert "cidr_ipv4" not in environment.split('module "ec2"', 1)[1].split("module ", 1)[0]


def test_release_artifacts_stay_limited_to_bundles_and_evidence() -> None:
    text = RELEASE_ARTIFACTS.read_text(encoding="utf-8")
    assert "Never stores Terraform state or secrets." in text
    assert "DenyInsecureTransport" in text
    assert 'sse_algorithm = "AES256"' in text
    assert "aws:kms" not in text
    assert "kms_key_id" not in text
    assert "block_public_acls       = true" in text
    assert "restrict_public_buckets = true" in text
    assert 'status = "Enabled"' in text
    lowered = text.lower()
    assert "terraform.tfstate" not in lowered
    assert "secret_string" not in lowered
    for path in (STAGING, PRODUCTION):
        environment = path.read_text(encoding="utf-8")
        assert 'module "release_artifacts"' in environment
        assert "environment = local.environment" in environment


def test_alb_access_log_bucket_stays_on_sse_s3() -> None:
    blocks = _blocks(LOGGING.read_text(encoding="utf-8"))
    encryption = _one(
        blocks,
        "aws_s3_bucket_server_side_encryption_configuration",
        "alb_logs",
    )
    assert 'sse_algorithm = "AES256"' in encryption
    assert "aws:kms" not in encryption
    assert "kms_master_key_id" not in encryption


def _assignment(text: str, name: str) -> str:
    match = re.search(rf'(?m)^variable "{name}" \{{(.*?)^\}}', text, re.DOTALL)
    assert match is not None, name
    default = re.search(r"(?m)^\s*default\s+=\s+(.+)$", match.group(1))
    assert default is not None, name
    return default.group(1).strip()


def test_reject_flow_logs_use_a_dedicated_encrypted_bucket() -> None:
    text = NETWORKING.read_text(encoding="utf-8")
    assert "successful outbound HTTPS" in text
    assert "not the" in text and "API instance role" in text
    blocks = _blocks(text)
    flow_logs = [name for kind, name, _body in blocks if kind == "aws_flow_log"]
    assert flow_logs == ["reject"]
    flow = _one(blocks, "aws_flow_log", "reject")
    assert "vpc_id               = aws_vpc.this.id" in flow
    assert 'traffic_type         = "REJECT"' in flow
    assert 'log_destination_type = "s3"' in flow
    assert "log_destination      = aws_s3_bucket.flow_logs.arn" in flow
    assert "aws_s3_bucket.alb_logs" not in text
    assert "iam_role" not in flow

    bucket = _one(blocks, "aws_s3_bucket", "flow_logs")
    assert "vpc-flow-logs" in bucket
    public = _one(blocks, "aws_s3_bucket_public_access_block", "flow_logs")
    assert "block_public_acls       = true" in public
    assert "block_public_policy     = true" in public
    assert "ignore_public_acls      = true" in public
    assert "restrict_public_buckets = true" in public
    encryption = _one(blocks, "aws_s3_bucket_server_side_encryption_configuration", "flow_logs")
    assert 'sse_algorithm     = "aws:kms"' in encryption
    assert "kms_master_key_id = aws_kms_key.flow_logs.arn" in encryption
    lifecycle = _one(blocks, "aws_s3_bucket_lifecycle_configuration", "flow_logs")
    assert "days = 14" in lifecycle
    assert "noncurrent_days = 14" in lifecycle
    policy = _one(blocks, "aws_s3_bucket_policy", "flow_logs")
    assert "DenyInsecureTransport" in policy
    assert "delivery.logs.amazonaws.com" in policy
    assert "s3:PutObject" in policy
    assert "s3:GetBucketAcl" in policy
    assert "s3:ListBucket" not in policy
    assert "AWSLogs/${local.account_id}/*" in policy
    assert "aws:SourceAccount" in policy
    assert "aws:SourceArn" in policy
    assert "bucket-owner-full-control" in policy
    key = _one(blocks, "aws_kms_key", "flow_logs")
    assert "enable_key_rotation     = true" in key
    assert "AllowVpcFlowLogDelivery" in key
    assert "delivery.logs.amazonaws.com" in key
    iam = IAM.read_text(encoding="utf-8")
    assert "flow_logs" not in iam
    assert "delivery.logs.amazonaws.com" not in iam
    for path in (STAGING, PRODUCTION):
        environment = path.read_text(encoding="utf-8")
        assert environment.count('module "networking"') == 1


def test_staging_rds_requires_protection_and_a_final_snapshot() -> None:
    staging = STAGING_VARIABLES.read_text(encoding="utf-8")
    production = PRODUCTION_VARIABLES.read_text(encoding="utf-8")
    assert _assignment(staging, "deletion_protection") == "true"
    assert _assignment(staging, "skip_final_snapshot") == "false"
    assert _assignment(staging, "backup_retention_days") == "7"
    assert _assignment(staging, "multi_az") == "false"
    assert "storage charges" in staging
    assert _assignment(production, "deletion_protection") == "true"
    assert _assignment(production, "skip_final_snapshot") == "false"
    assert "skip_final_snapshot == false" in production
    assert "backup_retention_days >= 30" in production
    assert _assignment(production, "multi_az") == "true"
    example = STAGING_EXAMPLE.read_text(encoding="utf-8")
    assert "deletion_protection = true" in example
    assert "skip_final_snapshot = false" in example
    assert "backup_retention_days = 7" in example
    assert "multi_az            = false" in example
    rds = RDS.read_text(encoding="utf-8")
    assert "iam_database_authentication_enabled" not in rds
    assert "manage_master_user_password = true" in rds
    assert "deletion_protection       = var.deletion_protection" in rds
    assert "skip_final_snapshot       = var.skip_final_snapshot" in rds
    assert 'database_insights_mode                = "standard"' in rds
    assert "performance_insights_enabled          = true" in rds
    assert "performance_insights_retention_period = 7" in rds
    assert "performance_insights_kms_key_id" not in rds
    assert "monitoring_interval" not in rds
    assert '"advanced"' not in rds
