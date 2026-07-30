output "alb_security_group_id" {
  description = "ALB security group ID."
  value       = aws_security_group.alb.id
}

output "api_security_group_id" {
  description = "API/EC2 security group ID."
  value       = aws_security_group.api.id
}

output "rds_security_group_id" {
  description = "RDS security group ID."
  value       = aws_security_group.rds.id
}
