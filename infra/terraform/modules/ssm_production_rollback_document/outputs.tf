output "document_name" {
  description = "SSM rollback document name."
  value       = aws_ssm_document.production_rollback.name
}

output "document_arn" {
  description = "SSM rollback document ARN for deploy-role allowlisting."
  value       = aws_ssm_document.production_rollback.arn
}

output "timeout_seconds" {
  description = "Document default timeout."
  value       = var.timeout_seconds
}
