# Account-level GitHub Actions OIDC provider.
# Owned only by infra/terraform/account/ — environment roots must never create
# a second aws_iam_openid_connect_provider for token.actions.githubusercontent.com.

locals {
  oidc_url = "https://token.actions.githubusercontent.com"
}

data "tls_certificate" "github" {
  count = var.create_provider ? 1 : 0
  url   = local.oidc_url
}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_provider ? 1 : 0

  url             = local.oidc_url
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github[0].certificates[0].sha1_fingerprint]

  tags = merge(var.tags, {
    Name = "github-actions-oidc"
    Role = "github-oidc"
  })

  lifecycle {
    prevent_destroy = true
  }
}

data "aws_iam_openid_connect_provider" "existing" {
  count = var.create_provider ? 0 : 1
  arn   = var.existing_provider_arn
}
