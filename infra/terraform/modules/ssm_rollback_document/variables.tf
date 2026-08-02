variable "environment" {
  description = "DealBrain environment. Staging-only custom rollback document in Sprint 25b.5."
  type        = string

  validation {
    condition     = var.environment == "staging"
    error_message = "ssm_rollback_document module is staging-only in Sprint 25b.5."
  }
}

variable "document_name" {
  description = "SSM document name."
  type        = string
  default     = "DealBrain-StagingRollback"

  validation {
    condition     = var.document_name == "DealBrain-StagingRollback"
    error_message = "Sprint 25b.5 requires document_name = DealBrain-StagingRollback."
  }
}

variable "timeout_seconds" {
  description = "Document default timeout for the host rollback script."
  type        = number
  default     = 2400

  validation {
    condition     = var.timeout_seconds == 2400
    error_message = "Sprint 25b.5 requires timeout_seconds = 2400."
  }
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
