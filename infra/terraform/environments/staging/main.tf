terraform {
  required_version = ">= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  environment = "staging"
  name_prefix = "dealbrain-${local.environment}"

  azs = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.aws_availability_zones.available.names, 0, 2)

  common_tags = merge(var.tags, {
    Project     = "dealbrain"
    Environment = local.environment
    ManagedBy   = "terraform"
    Sprint      = "25a"
  })

  # Sprint 25b.3 — idempotent AL2023 bootstrap + thin SSM entrypoint (no secrets).
  staging_user_data = file("${path.module}/../../../ec2/user_data/staging.sh")
}

module "networking" {
  source = "../../modules/networking"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = local.azs
  enable_nat_gateway   = var.enable_nat_gateway
  single_nat_gateway   = var.single_nat_gateway
  tags                 = local.common_tags
}

module "security_groups" {
  source = "../../modules/security_groups"

  name_prefix           = local.name_prefix
  vpc_id                = module.networking.vpc_id
  allowed_ingress_cidrs = var.allowed_ingress_cidrs
  tags                  = local.common_tags
}

module "secrets" {
  source = "../../modules/secrets"

  name_prefix = local.name_prefix
  environment = local.environment
  tags        = local.common_tags
}

module "alb" {
  source = "../../modules/alb"

  name_prefix       = local.name_prefix
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
  security_group_id = module.security_groups.alb_security_group_id
  certificate_arn   = var.alb_certificate_arn
  health_check_path = "/ready"
  tags              = local.common_tags
}

module "rds" {
  source = "../../modules/rds"

  name_prefix           = local.name_prefix
  private_subnet_ids    = module.networking.private_subnet_ids
  security_group_ids    = [module.security_groups.rds_security_group_id]
  engine_version        = var.rds_engine_version
  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  db_name               = var.db_name
  db_username           = var.db_username
  backup_retention_days = var.backup_retention_days
  deletion_protection   = var.deletion_protection
  multi_az              = var.multi_az
  skip_final_snapshot   = var.skip_final_snapshot
  tags                  = local.common_tags
}

# Sprint 25b.3 — staging release-artifacts bucket (bundles + evidence).
module "release_artifacts" {
  source = "../../modules/release_artifacts"

  environment = local.environment
  name_prefix = local.name_prefix
  tags = merge(local.common_tags, {
    Sprint = "25b.3"
  })
}

# Sprint 25b.3 — custom SSM Command document for staging deploy.
# Replaces the interim managed RunShellScript allowlist entry on staging.
module "ssm_deploy_document" {
  source = "../../modules/ssm_deploy_document"

  environment = local.environment
  tags = merge(local.common_tags, {
    Sprint = "25b.3"
  })
}

# IAM after RDS so the instance role may read this env's application secrets
# and the AWS-managed RDS master-user secret ARN only (no plaintext values).
module "iam" {
  source = "../../modules/iam"

  name_prefix                  = local.name_prefix
  environment                  = local.environment
  release_artifacts_bucket_arn = module.release_artifacts.bucket_arn
  secret_arns = compact(concat(
    values(module.secrets.secret_arns),
    [module.rds.master_user_secret_arn],
  ))
  tags = local.common_tags
}

module "ec2" {
  source = "../../modules/ec2"

  name_prefix               = local.name_prefix
  subnet_id                 = module.networking.private_subnet_ids[0]
  security_group_ids        = [module.security_groups.api_security_group_id]
  instance_type             = var.instance_type
  ami_id                    = var.ami_id
  iam_instance_profile_name = module.iam.api_host_instance_profile_name
  target_group_arn          = module.alb.target_group_arn
  associate_public_ip       = false
  root_volume_size_gb       = var.root_volume_size_gb
  user_data                 = local.staging_user_data
  tags                      = local.common_tags
}

# Sprint 25b.2/25b.3 — GitHub Actions OIDC deploy role.
# Staging: custom DealBrain-StagingDeploy document only (no managed RunShellScript allow).
# Operationally approved only after GitHub Environment hard gates are live.
module "github_deploy_role" {
  source = "../../modules/github_deploy_role"

  environment                  = local.environment
  github_repository_owner      = var.github_repository_owner
  github_repository_name       = var.github_repository_name
  github_oidc_provider_arn     = var.github_oidc_provider_arn
  aws_region                   = var.aws_region
  allowed_ssm_document_arns    = [module.ssm_deploy_document.document_arn]
  release_artifacts_bucket_arn = module.release_artifacts.bucket_arn
  tags = merge(local.common_tags, {
    Sprint = "25b.3"
  })
}
