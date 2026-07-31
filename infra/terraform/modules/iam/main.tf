data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_host" {
  name               = "${var.name_prefix}-api-host"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-host-role"
  })
}

data "aws_iam_policy_document" "api_host" {
  statement {
    sid    = "ReadEnvironmentSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = var.secret_arns
  }

  # Explicit deny of the other environment's secret path — defense in depth.
  statement {
    sid    = "DenyOtherEnvironmentSecrets"
    effect = "Deny"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:PutSecretValue",
      "secretsmanager:UpdateSecret",
      "secretsmanager:DeleteSecret",
    ]
    resources = [
      "arn:aws:secretsmanager:*:*:secret:dealbrain/${var.environment == "staging" ? "production" : "staging"}/*",
    ]
  }

  dynamic "statement" {
    for_each = length(var.log_group_arns) > 0 ? [1] : []
    content {
      sid    = "WriteCloudWatchLogs"
      effect = "Allow"
      actions = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams",
      ]
      resources = var.log_group_arns
    }
  }

  statement {
    sid    = "ECRPullNotUsed"
    effect = "Deny"
    actions = [
      "ecr:*",
    ]
    resources = ["*"]
    # Images come from GHCR; no ECR access required for Sprint 25a.
  }

  # Sprint 25b.3 — staging host downloads release bundles and uploads evidence.
  dynamic "statement" {
    for_each = trimspace(var.release_artifacts_bucket_arn) != "" ? [var.release_artifacts_bucket_arn] : []
    content {
      sid    = "ReadReleaseBundles"
      effect = "Allow"
      actions = [
        "s3:GetObject",
      ]
      resources = [
        "${statement.value}/releases/*",
      ]
    }
  }

  dynamic "statement" {
    for_each = trimspace(var.release_artifacts_bucket_arn) != "" ? [var.release_artifacts_bucket_arn] : []
    content {
      sid    = "PutStagingEvidence"
      effect = "Allow"
      actions = [
        "s3:PutObject",
      ]
      resources = [
        "${statement.value}/evidence/*",
      ]
    }
  }

  dynamic "statement" {
    for_each = trimspace(var.release_artifacts_bucket_arn) != "" ? [var.release_artifacts_bucket_arn] : []
    content {
      sid    = "ListReleaseBundlesPrefix"
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

  # Host IAM also needs GetObject on the command-id binder under evidence/.
  dynamic "statement" {
    for_each = trimspace(var.release_artifacts_bucket_arn) != "" ? [var.release_artifacts_bucket_arn] : []
    content {
      sid    = "ReadEvidenceBinderObjects"
      effect = "Allow"
      actions = [
        "s3:GetObject",
      ]
      resources = [
        "${statement.value}/evidence/*",
      ]
    }
  }

  # Host verifies Environment/Role/Project tags and ALB target health during deploy.
  dynamic "statement" {
    for_each = trimspace(var.release_artifacts_bucket_arn) != "" ? [1] : []
    content {
      sid    = "StagingHostDescribeForDeploy"
      effect = "Allow"
      actions = [
        "ec2:DescribeTags",
        "elasticloadbalancing:DescribeTargetHealth",
      ]
      resources = ["*"]
    }
  }
}

resource "aws_iam_role_policy" "api_host" {
  name   = "${var.name_prefix}-api-host-policy"
  role   = aws_iam_role.api_host.id
  policy = data.aws_iam_policy_document.api_host.json
}

# Sprint 25b.2 — SSM managed-instance capability for later Run Command deploys.
# Preserves Secrets Manager allow/deny and ECR deny above. No SSH.
resource "aws_iam_role_policy_attachment" "api_host_ssm_managed_instance" {
  role       = aws_iam_role.api_host.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "api_host" {
  name = "${var.name_prefix}-api-host"
  role = aws_iam_role.api_host.name
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-host-profile"
  })
}
