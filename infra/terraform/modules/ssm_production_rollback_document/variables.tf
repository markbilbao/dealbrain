variable "environment" {
  description = "DealBrain environment. Production-only custom rollback document."
  type        = string

  validation {
    condition     = var.environment == "production"
    error_message = "ssm_production_rollback_document module is production-only."
  }
}

variable "document_name" {
  description = "SSM document name."
  type        = string
  default     = "DealBrain-ProductionRollback"

  validation {
    condition     = var.document_name == "DealBrain-ProductionRollback"
    error_message = "Production rollback document_name must be DealBrain-ProductionRollback."
  }
}

variable "timeout_seconds" {
  description = "Document default timeout for the host rollback script."
  type        = number
  default     = 2400

  validation {
    condition     = var.timeout_seconds == 2400
    error_message = "Production rollback timeout_seconds must be 2400."
  }
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
