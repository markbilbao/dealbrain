variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "subnet_id" {
  description = "Subnet for the deployment host (typically private with NAT, or public for bootstrap)."
  type        = string
}

variable "security_group_ids" {
  description = "Security groups attached to the instance."
  type        = list(string)
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t3.small"
}

variable "ami_id" {
  description = "AMI ID. Empty uses the latest Amazon Linux 2023 x86_64."
  type        = string
  default     = ""
}

variable "iam_instance_profile_name" {
  description = "IAM instance profile name for Secrets Manager / CloudWatch access."
  type        = string
}

variable "target_group_arn" {
  description = "ALB target group ARN to register the instance against."
  type        = string
}

variable "associate_public_ip" {
  description = "Associate a public IP (only when placed in a public subnet for bootstrap)."
  type        = bool
  default     = false
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size in GiB."
  type        = number
  default     = 30
}

variable "user_data" {
  description = "Optional cloud-init / user-data script (Docker install deferred to deploy phase)."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
