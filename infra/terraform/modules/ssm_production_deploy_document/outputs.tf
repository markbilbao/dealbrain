output "document_name" {
  description = "SSM document name."
  value       = aws_ssm_document.production_deploy.name
}

output "document_arn" {
  description = "SSM document ARN for deploy-role allowlisting."
  value       = aws_ssm_document.production_deploy.arn
}

output "timeout_seconds" {
  description = "Document default timeout."
  value       = var.timeout_seconds
}
