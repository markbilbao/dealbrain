variable "name_prefix" {
  description = "Resource name prefix (e.g. dealbrain-staging)."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (ALB). One per AZ."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) >= 2
    error_message = "At least two public subnets are required for ALB high availability."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (RDS / optional private hosts). One per AZ."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_cidrs) >= 2
    error_message = "At least two private subnets are required for RDS subnet groups."
  }
}

variable "availability_zones" {
  description = "Availability zones matching subnet CIDR lists by index."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least two availability zones are required."
  }
}

variable "enable_nat_gateway" {
  description = "Create a NAT gateway for private-subnet egress (image pulls, Secrets Manager)."
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use one NAT gateway (cost-sensitive). Prefer false for production HA."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to all networking resources."
  type        = map(string)
  default     = {}
}
