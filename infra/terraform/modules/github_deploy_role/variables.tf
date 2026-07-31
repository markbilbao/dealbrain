variable "environment" {
  description = "DealBrain environment (staging|production). Pins OIDC subject and tags."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "github_repository_owner" {
  description = "GitHub repository owner (organization or user). Mandatory — no wildcards."
  type        = string

  validation {
    condition     = length(trimspace(var.github_repository_owner)) > 0
    error_message = "github_repository_owner is required and must be non-empty."
  }
}

variable "github_repository_name" {
  description = "GitHub repository name. Mandatory — no wildcards."
  type        = string

  validation {
    condition     = length(trimspace(var.github_repository_name)) > 0
    error_message = "github_repository_name is required and must be non-empty."
  }
}

variable "github_oidc_provider_arn" {
  description = "ARN of the account-level GitHub Actions OIDC provider (from account root)."
  type        = string

  validation {
    condition     = length(trimspace(var.github_oidc_provider_arn)) > 0
    error_message = "github_oidc_provider_arn is required and must be non-empty."
  }
}

variable "aws_region" {
  description = "AWS region used to scope SSM document ARNs."
  type        = string
  default     = "us-east-1"
}

variable "max_session_duration" {
  description = "Maximum OIDC session duration in seconds."
  type        = number
  default     = 3600

  validation {
    condition     = var.max_session_duration == 3600
    error_message = "Sprint 25b.2 requires max_session_duration = 3600."
  }
}

variable "allowed_ssm_document_arns" {
  description = <<-EOT
    Extension point: SSM document ARNs the deploy role may invoke via SendCommand.
    When empty (the environment-root default), only AWS-RunShellScript is permitted.
    Custom DealBrain documents remain Sprint 25b.3; do not widen this list in 25b.2.
  EOT
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
