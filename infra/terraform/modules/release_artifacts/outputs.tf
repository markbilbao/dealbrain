output "bucket_name" {
  description = "Environment release-artifacts bucket name."
  value       = aws_s3_bucket.artifacts.id
}

output "bucket_arn" {
  description = "Release-artifacts bucket ARN."
  value       = aws_s3_bucket.artifacts.arn
}

output "releases_prefix" {
  description = "Object key prefix for release bundles."
  value       = "releases/"
}

output "evidence_prefix" {
  description = "Object key prefix for deploy evidence."
  value       = "evidence/"
}
