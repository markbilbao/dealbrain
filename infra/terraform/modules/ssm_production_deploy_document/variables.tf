variable "environment" {
  description = "DealBrain environment. Production-only custom deploy document."
  type        = string

  validation {
    condition     = var.environment == "production"
    error_message = "ssm_production_deploy_document module is production-only."
  }
}

variable "document_name" {
  description = "SSM document name."
  type        = string
  default     = "DealBrain-ProductionDeploy"

  validation {
    condition     = var.document_name == "DealBrain-ProductionDeploy"
    error_message = "Production deploy document_name must be DealBrain-ProductionDeploy."
  }
}

variable "timeout_seconds" {
  description = "Document default timeout for the host deploy script."
  type        = number
  default     = 2400

  validation {
    condition     = var.timeout_seconds == 2400
    error_message = "Production deploy timeout_seconds must be 2400."
  }
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
