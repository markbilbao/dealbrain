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
    container here. Runtime DATABASE_URL assembly is Sprint 25b.3.

    ghcr_pull (Sprint 25b.2): container only for a classic PAT with
    read:packages. Expected JSON shape (values out-of-band — never in TF):
      {"username":"REPLACE_ME_OUT_OF_BAND","token":"REPLACE_ME_OUT_OF_BAND"}
    Do not create aws_secretsmanager_secret_version for these credentials.
  EOT
  type        = list(string)
  default = [
    "app_secret_key",
    "openai_api_key",
    "anthropic_api_key",
    "gemini_api_key",
    "cors_origins",
    "monitoring",
    "ghcr_pull",
  ]
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
