variable "environment" {
  description = "DealBrain environment. Staging-only custom document in Sprint 25b.3."
  type        = string

  validation {
    condition     = var.environment == "staging"
    error_message = "ssm_deploy_document module is staging-only in Sprint 25b.3."
  }
}

variable "document_name" {
  description = "SSM document name."
  type        = string
  default     = "DealBrain-StagingDeploy"

  validation {
    condition     = var.document_name == "DealBrain-StagingDeploy"
    error_message = "Sprint 25b.3 requires document_name = DealBrain-StagingDeploy."
  }
}

variable "timeout_seconds" {
  description = "Document default timeout for the host deploy script."
  type        = number
  default     = 2400

  validation {
    condition     = var.timeout_seconds == 2400
    error_message = "Sprint 25b.3 requires timeout_seconds = 2400."
  }
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
