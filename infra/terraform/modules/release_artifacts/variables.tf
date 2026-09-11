variable "environment" {
  description = "DealBrain environment. Isolated per-environment release/evidence bucket."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "release_artifacts environment must be staging or production."
  }
}

variable "name_prefix" {
  description = "Resource name prefix (e.g. dealbrain-staging)."
  type        = string
}

variable "object_retention_days" {
  description = "Optional object expiry in days (0 disables). Incomplete multipart cleanup always enabled."
  type        = number
  default     = 90

  validation {
    condition     = var.object_retention_days == 0 || var.object_retention_days >= 30
    error_message = "object_retention_days must be 0 (disabled) or >= 30."
  }
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
