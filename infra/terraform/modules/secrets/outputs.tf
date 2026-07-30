output "secret_arns" {
  description = "Map of secret leaf name → ARN."
  value       = { for k, s in aws_secretsmanager_secret.this : k => s.arn }
}

output "secret_names" {
  description = "Map of secret leaf name → full Secrets Manager name."
  value       = { for k, s in aws_secretsmanager_secret.this : k => s.name }
}

output "secrets_path_prefix" {
  description = "IAM-friendly path prefix for this environment."
  value       = "dealbrain/${var.environment}/*"
}
