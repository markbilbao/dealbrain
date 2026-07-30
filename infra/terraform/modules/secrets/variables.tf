variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "environment" {
  description = "Environment name (staging|production). Isolates secret path prefix."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "secret_names" {
  description = <<-EOT
    Logical secret leaf names under dealbrain/<env>/.
    RDS master credentials are AWS-managed separately (see rds module
    manage_master_user_password) — do not add a conflicting database_url
    container here. Runtime DATABASE_URL assembly is Sprint 25b.
  EOT
  type        = list(string)
  default = [
    "app_secret_key",
    "openai_api_key",
    "anthropic_api_key",
    "gemini_api_key",
    "cors_origins",
    "monitoring",
  ]
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
