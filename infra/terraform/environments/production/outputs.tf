output "environment" {
  value = local.environment
}

output "aws_region" {
  value = var.aws_region
}

output "vpc_id" {
  value = module.networking.vpc_id
}

output "public_subnet_ids" {
  value = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.networking.private_subnet_ids
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "alb_target_group_arn" {
  value = module.alb.target_group_arn
}

output "api_instance_id" {
  value = module.ec2.instance_id
}

output "api_private_ip" {
  value = module.ec2.private_ip
}

output "rds_endpoint" {
  value = module.rds.db_endpoint
}

output "rds_port" {
  value = module.rds.db_port
}

output "rds_db_name" {
  value = module.rds.db_name
}

output "rds_master_user_secret_arn" {
  description = "AWS-managed RDS master-user secret ARN (identifier only; no password)."
  value       = module.rds.master_user_secret_arn
  sensitive   = true
}

output "secrets_path_prefix" {
  description = "Application Secrets Manager path prefix for this environment."
  value       = module.secrets.secrets_path_prefix
}

output "secret_arns" {
  description = "Application secret ARNs under dealbrain/production/* (no values)."
  value       = module.secrets.secret_arns
  sensitive   = true
}

output "api_host_role_arn" {
  value = module.iam.api_host_role_arn
}

output "domain_name" {
  value = var.domain_name
}

output "image_reference" {
  value = var.image_reference
}

output "log_retention_days" {
  value = var.log_retention_days
}
