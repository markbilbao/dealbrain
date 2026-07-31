# GitHub Actions deploy orchestration role (Sprint 25b.2).
# Trust: Exact repo + exact GitHub Environment subject via OIDC.
# Permissions: SSM SendCommand prep + describe APIs only.
# Explicitly withheld: secret value reads, IAM admin, Terraform/state,
# rds:CreateDBSnapshot (deferred to 25b.4), SSH, PassRole.

data "aws_caller_identity" "current" {}

locals {
  role_name = "dealbrain-${var.environment}-gha-deploy"

  github_repository = "${var.github_repository_owner}/${var.github_repository_name}"
  expected_sub      = "repo:${local.github_repository}:environment:${var.environment}"

  opposite_environment = var.environment == "staging" ? "production" : "staging"

  # Default: AWS managed RunShellScript document in the configured region.
  # Account ID is empty for AWS-owned public documents.
  default_ssm_document_arns = [
    "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript",
  ]
  ssm_document_arns = length(var.allowed_ssm_document_arns) > 0 ? var.allowed_ssm_document_arns : local.default_ssm_document_arns

  account_id = data.aws_caller_identity.current.account_id
}

data "aws_iam_policy_document" "trust" {
  statement {
    sid     = var.environment == "staging" ? "GitHubActionsStagingEnvironment" : "GitHubActionsProductionEnvironment"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.expected_sub]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:repository"
      values   = [local.github_repository]
    }
  }
}

resource "aws_iam_role" "gha_deploy" {
  name                 = local.role_name
  description          = "DealBrain ${var.environment} GitHub Actions deploy orchestration (OIDC; no static keys)."
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  max_session_duration = var.max_session_duration

  tags = merge(var.tags, {
    Name        = local.role_name
    Environment = var.environment
    Role        = "gha-deploy"
    Project     = "dealbrain"
    ManagedBy   = "terraform"
  })
}

# ---------------------------------------------------------------------------
# Allow — orchestration only (Sprint 25b.2)
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "deploy_allow" {
  # SendCommand against the approved SSM document only.
  statement {
    sid    = "SendCommandApprovedDocument"
    effect = "Allow"
    actions = [
      "ssm:SendCommand",
    ]
    resources = local.ssm_document_arns
  }

  # SendCommand against EC2 instances tagged for this environment.
  # ssm:resourceTag/* is the supported condition key for SSM instance targets.
  statement {
    sid    = "SendCommandEnvironmentTaggedInstances"
    effect = "Allow"
    actions = [
      "ssm:SendCommand",
    ]
    resources = [
      "arn:aws:ec2:${var.aws_region}:${local.account_id}:instance/*",
    ]
    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/Environment"
      values   = [var.environment]
    }
    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/Project"
      values   = ["dealbrain"]
    }
  }

  # Result observation — GetCommandInvocation requires Resource "*".
  # ListCommands / ListCommandInvocations unused by deploy workflow (removed 25b.4a).
  statement {
    sid    = "ObserveSsmCommands"
    effect = "Allow"
    actions = [
      "ssm:GetCommandInvocation",
    ]
    resources = ["*"]
  }

  # Targeting describe APIs — AWS documents Resource "*" only.
  # ALB target health is verified on the host (DescribeTargetHealth lives on host IAM).
  # Target group ARN is supplied via GitHub Environment var (no DescribeTargetGroups).
  statement {
    sid    = "DescribeForTargeting"
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
      "ec2:DescribeInstanceStatus",
      "rds:DescribeDBInstances",
    ]
    resources = ["*"]
  }

  # Sprint 25b.3 — staging release-artifacts bucket (bundles + evidence). Absent for production.
  dynamic "statement" {
    for_each = trimspace(var.release_artifacts_bucket_arn) != "" ? [var.release_artifacts_bucket_arn] : []
    content {
      sid    = "ReleaseArtifactsObjectAccess"
      effect = "Allow"
      actions = [
        "s3:PutObject",
        "s3:GetObject",
      ]
      resources = [
        "${statement.value}/releases/*",
        "${statement.value}/evidence/*",
      ]
    }
  }

  dynamic "statement" {
    for_each = trimspace(var.release_artifacts_bucket_arn) != "" ? [var.release_artifacts_bucket_arn] : []
    content {
      sid    = "ReleaseArtifactsListBucket"
      effect = "Allow"
      actions = [
        "s3:ListBucket",
      ]
      resources = [statement.value]
      condition {
        test     = "StringLike"
        variable = "s3:prefix"
        values = [
          "releases/",
          "releases/*",
          "evidence/",
          "evidence/*",
        ]
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Deny — hard boundaries (both environments)
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "deploy_deny" {
  statement {
    sid    = "DenyIamMutationAndPassRole"
    effect = "Deny"
    actions = [
      "iam:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DenyOrganizationsMutation"
    effect = "Deny"
    actions = [
      "organizations:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DenySecretsManagerValueAccess"
    effect = "Deny"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:PutSecretValue",
      "secretsmanager:DeleteSecret",
      "secretsmanager:UpdateSecret",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DenyRdsMutationAndSnapshot"
    effect = "Deny"
    actions = [
      "rds:CreateDBSnapshot",
      "rds:DeleteDBInstance",
      "rds:ModifyDBInstance",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DenyDangerousEc2Mutation"
    effect = "Deny"
    actions = [
      "ec2:TerminateInstances",
      "ec2:StopInstances",
      "ec2:ModifyInstanceAttribute",
      "ec2:RunInstances",
    ]
    resources = ["*"]
  }

  # Opposite-environment SSM targeting deny (defense in depth).
  statement {
    sid    = "DenySendCommandOppositeEnvironment"
    effect = "Deny"
    actions = [
      "ssm:SendCommand",
    ]
    resources = [
      "arn:aws:ec2:${var.aws_region}:${local.account_id}:instance/*",
    ]
    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/Environment"
      values   = [local.opposite_environment]
    }
  }

  # Opposite-environment secret path ARN deny (stable path pattern).
  statement {
    sid    = "DenyOppositeEnvironmentSecretArns"
    effect = "Deny"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:PutSecretValue",
      "secretsmanager:UpdateSecret",
      "secretsmanager:DeleteSecret",
    ]
    resources = [
      "arn:aws:secretsmanager:*:*:secret:dealbrain/${local.opposite_environment}/*",
    ]
  }

  # Block Terraform remote-state style S3 writes (deploy role must not apply TF).
  statement {
    sid    = "DenyTerraformStateWrites"
    effect = "Deny"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:PutObjectAcl",
    ]
    resources = [
      "arn:aws:s3:::dealbrain-terraform-state-*/*",
      "arn:aws:s3:::dealbrain-terraform-state-*",
    ]
  }
}

resource "aws_iam_role_policy" "deploy_allow" {
  name   = "${local.role_name}-allow"
  role   = aws_iam_role.gha_deploy.id
  policy = data.aws_iam_policy_document.deploy_allow.json
}

resource "aws_iam_role_policy" "deploy_deny" {
  name   = "${local.role_name}-deny"
  role   = aws_iam_role.gha_deploy.id
  policy = data.aws_iam_policy_document.deploy_deny.json
}
