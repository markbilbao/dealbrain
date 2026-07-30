terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state is mandatory for production.
  # Bootstrap an S3 bucket + DynamoDB lock table out-of-band, then uncomment:
  #
  # backend "s3" {
  #   bucket         = "dealbrain-terraform-state-REPLACE_ME"
  #   key            = "production/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "dealbrain-terraform-locks"
  #   encrypt        = true
  # }
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
  environment = "production"
  name_prefix = "dealbrain-${local.environment}"

  azs = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.aws_availability_zones.available.names, 0, 2)

  common_tags = merge(var.tags, {
    Project     = "dealbrain"
    Environment = local.environment
    ManagedBy   = "terraform"
    Sprint      = "25a"
  })
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

# IAM after RDS so the instance role may read this env's application secrets
# and the AWS-managed RDS master-user secret ARN only (no plaintext values).
module "iam" {
  source = "../../modules/iam"

  name_prefix = local.name_prefix
  environment = local.environment
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
  tags                      = local.common_tags
}
