variable "environment" {
  description = "DealBrain environment. Staging-only for Sprint 25b.3."
  type        = string

  validation {
    condition     = var.environment == "staging"
    error_message = "release_artifacts module is staging-only in Sprint 25b.3."
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
