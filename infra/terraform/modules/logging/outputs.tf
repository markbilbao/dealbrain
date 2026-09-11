output "api_log_group_name" {
  description = "CloudWatch log group for Compose API application logs."
  value       = aws_cloudwatch_log_group.api.name
}

output "api_log_group_arn" {
  description = "CloudWatch log group ARN (use with :* for stream writes)."
  value       = aws_cloudwatch_log_group.api.arn
}

output "host_log_group_name" {
  description = "CloudWatch log group for host/bootstrap logs."
  value       = aws_cloudwatch_log_group.host.name
}

output "host_log_group_arn" {
  description = "Host CloudWatch log group ARN."
  value       = aws_cloudwatch_log_group.host.arn
}

output "migrate_log_group_name" {
  description = "CloudWatch log group for one-shot migrate service logs."
  value       = aws_cloudwatch_log_group.migrate.name
}

output "migrate_log_group_arn" {
  description = "Migrate CloudWatch log group ARN."
  value       = aws_cloudwatch_log_group.migrate.arn
}

output "log_group_arns" {
  description = "IAM-ready log group ARNs including :* stream suffix."
  value = [
    "${aws_cloudwatch_log_group.api.arn}:*",
    "${aws_cloudwatch_log_group.host.arn}:*",
    "${aws_cloudwatch_log_group.migrate.arn}:*",
  ]
}

output "alb_logs_bucket_name" {
  description = "S3 bucket name for ALB access logs (not Terraform state)."
  value       = aws_s3_bucket.alb_logs.id
  depends_on  = [aws_s3_bucket_policy.alb_logs]
}

output "alb_logs_bucket_arn" {
  description = "S3 bucket ARN for ALB access logs."
  value       = aws_s3_bucket.alb_logs.arn
}

output "alb_logs_prefix" {
  description = "Object key prefix passed to the ALB access_logs block."
  value       = "alb"
}
