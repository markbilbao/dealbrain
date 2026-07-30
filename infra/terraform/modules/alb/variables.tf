variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB."
  type        = list(string)
}

variable "security_group_id" {
  description = "ALB security group ID."
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Empty string disables HTTPS listener (HTTP only for bootstrap)."
  type        = string
  default     = ""
}

variable "health_check_path" {
  description = "Target group health check path. Must be /ready per Sprint 25 contract."
  type        = string
  default     = "/ready"

  validation {
    condition     = var.health_check_path == "/ready"
    error_message = "ALB health check path must be /ready (Sprint 22 readiness contract)."
  }
}

variable "target_port" {
  description = "API container/host port."
  type        = number
  default     = 8000
}

variable "enable_http_redirect" {
  description = "When certificate_arn is set, redirect HTTP to HTTPS."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
