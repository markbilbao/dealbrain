output "bucket_name" {
  description = "Staging release-artifacts bucket name."
  value       = aws_s3_bucket.artifacts.id
}

output "bucket_arn" {
  description = "Staging release-artifacts bucket ARN."
  value       = aws_s3_bucket.artifacts.arn
}

output "releases_prefix" {
  description = "Object key prefix for release bundles."
  value       = "releases/"
}

output "evidence_prefix" {
  description = "Object key prefix for staging deploy evidence."
  value       = "evidence/"
}
