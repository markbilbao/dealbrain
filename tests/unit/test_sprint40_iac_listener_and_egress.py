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
