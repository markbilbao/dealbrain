variable "aws_region" {
  description = "AWS region (frozen at 25a kickoff)."
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "Optional explicit AZs. Empty selects the first two available."
  type        = list(string)
  default     = []
}

variable "vpc_cidr" {
  description = "Production VPC CIDR (isolated from staging)."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs for ALB."
  type        = list(string)
  default     = ["10.20.0.0/24", "10.20.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs for RDS and API host."
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "enable_nat_gateway" {
  description = "NAT for private subnet egress."
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Prefer false for production HA; true is cost-sensitive."
  type        = bool
  default     = false
}

variable "allowed_ingress_cidrs" {
  description = "CIDRs allowed to reach the ALB. Restrict when possible."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "instance_type" {
  description = "EC2 instance type for the Compose host."
  type        = string
  default     = "t3.medium"
}

variable "ami_id" {
  description = "Optional AMI override. Empty = latest Amazon Linux 2023."
  type        = string
  default     = ""
}

variable "root_volume_size_gb" {
  description = "Root volume size."
  type        = number
  default     = 40
}

variable "rds_engine_version" {
  description = "PostgreSQL 16.x engine version."
  type        = string
  default     = "16.4"
}

variable "rds_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage GiB."
  type        = number
  default     = 50
}

variable "rds_max_allocated_storage" {
  description = "RDS storage autoscaling max GiB."
  type        = number
  default     = 200
}

variable "db_name" {
  description = "Database name."
  type        = string
  default     = "dealbrain"
}

variable "db_username" {
  description = "Database master username (not a secret). Password is AWS-managed."
  type        = string
  default     = "dealbrain"
}

variable "backup_retention_days" {
  description = "RDS backup retention (production ≥30)."
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retention_days >= 30
    error_message = "Production backup retention must be at least 30 days."
  }
}

variable "deletion_protection" {
  description = "RDS deletion protection (fail-safe production default)."
  type        = bool
  default     = true
}

variable "multi_az" {
  description = "RDS Multi-AZ (production default on)."
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Must remain false for production."
  type        = bool
  default     = false

  validation {
    condition     = var.skip_final_snapshot == false
    error_message = "Production must not skip the final RDS snapshot."
  }
}

variable "alb_certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Required before public traffic."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Public hostname placeholder (DNS cutover deferred)."
  type        = string
  default     = "api.dealbrain.example"
}

variable "image_reference" {
  description = "GHCR image digest placeholder (promote exact digest from staging)."
  type        = string
  default     = "ghcr.io/EXAMPLE_ORG/dealbrain@sha256:REPLACE_ME"
}

variable "log_retention_days" {
  description = "Intended CloudWatch log retention (log groups created in Sprint 25c)."
  type        = number
  default     = 30
}

variable "github_repository_owner" {
  description = "GitHub repository owner for OIDC trust (mandatory; no wildcards)."
  type        = string

  validation {
    condition     = length(trimspace(var.github_repository_owner)) > 0
    error_message = "github_repository_owner is required and must be non-empty."
  }
}

variable "github_repository_name" {
  description = "GitHub repository name for OIDC trust (mandatory; no wildcards)."
  type        = string

  validation {
    condition     = length(trimspace(var.github_repository_name)) > 0
    error_message = "github_repository_name is required and must be non-empty."
  }
}

variable "github_oidc_provider_arn" {
  description = <<-EOT
    ARN of the account-level GitHub Actions OIDC provider created by
    infra/terraform/account/. Prefer terraform_remote_state once backends
    exist; until then pass the account root output explicitly.
  EOT
  type        = string

  validation {
    condition     = length(trimspace(var.github_oidc_provider_arn)) > 0
    error_message = "github_oidc_provider_arn is required and must be non-empty."
  }
}

variable "tags" {
  description = "Additional tags."
  type        = map(string)
  default     = {}
}
