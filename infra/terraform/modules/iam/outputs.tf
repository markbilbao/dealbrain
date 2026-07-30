output "api_host_role_arn" {
  description = "IAM role ARN for the API EC2 host."
  value       = aws_iam_role.api_host.arn
}

output "api_host_role_name" {
  description = "IAM role name for the API EC2 host."
  value       = aws_iam_role.api_host.name
}

output "api_host_instance_profile_name" {
  description = "Instance profile name for EC2 attachment."
  value       = aws_iam_instance_profile.api_host.name
}
