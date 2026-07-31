provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  common_tags = merge(var.tags, {
    Project   = "dealbrain"
    ManagedBy = "terraform"
    Sprint    = "25b.2"
    Scope     = "account"
  })
}

# Exactly one GitHub Actions OIDC provider for this AWS account.
# Staging and production roots consume the ARN; they must never create another.
module "github_oidc" {
  source = "../modules/github_oidc"

  create_provider       = var.create_provider
  existing_provider_arn = var.existing_provider_arn
  tags                  = local.common_tags
}
