variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the DB subnet group."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups for the RDS instance."
  type        = list(string)
}

variable "engine_version" {
  description = "PostgreSQL engine version (16.x)."
  type        = string
  default     = "16.4"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "allocated_storage" {
  description = "Allocated storage in GiB."
  type        = number
  default     = 50
}

variable "max_allocated_storage" {
  description = "Autoscaling max storage in GiB (0 disables)."
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "dealbrain"
}

variable "db_username" {
  description = "Master username. Password is AWS-managed (Secrets Manager); never a Terraform input."
  type        = string
  default     = "dealbrain"
}

variable "backup_retention_days" {
  description = "Automated backup retention in days."
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Enable RDS deletion protection."
  type        = bool
  default     = true
}

variable "multi_az" {
  description = "Enable Multi-AZ. Recommended for production; optional for staging cost."
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on destroy. Must be false for production."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
