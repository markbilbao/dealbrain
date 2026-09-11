variable "environment" {
  description = "DealBrain environment. Production Early Access wires this module; staging remains optional."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "name_prefix" {
  description = "Resource name prefix (e.g. dealbrain-production)."
  type        = string
}

variable "aws_region" {
  description = "AWS region (frozen at 25a kickoff: us-east-1)."
  type        = string
  default     = "us-east-1"
}

variable "log_retention_days" {
  description = "CloudWatch Logs and ALB access-log object retention in days."
  type        = number
  default     = 30

  validation {
    condition     = contains([14, 30, 60, 90, 120, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a CloudWatch Logs allowed retention value."
  }
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
