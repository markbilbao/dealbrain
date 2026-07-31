variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "environment" {
  description = "Environment name (staging|production)."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "secret_arns" {
  description = "Secrets Manager ARNs this environment's instance role may read."
  type        = list(string)
}

variable "log_group_arns" {
  description = "CloudWatch log group ARNs the instance may write to (empty until 25c)."
  type        = list(string)
  default     = []
}

variable "release_artifacts_bucket_arn" {
  description = <<-EOT
    Optional staging release-artifacts bucket ARN. When set, the staging host may:
    read release bundle objects under releases/*; read the SSM command-ID binding
    under the scoped evidence/* prefix; and write host-authored deployment
    evidence under evidence/* (Sprint 25b.3/25b.4a). Production must leave empty.
  EOT
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
