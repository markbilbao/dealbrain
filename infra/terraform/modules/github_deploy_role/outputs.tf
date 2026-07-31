output "gha_deploy_role_arn" {
  description = "ARN of the environment GitHub Actions deploy role."
  value       = aws_iam_role.gha_deploy.arn
}

output "gha_deploy_role_name" {
  description = "Name of the environment GitHub Actions deploy role."
  value       = aws_iam_role.gha_deploy.name
}

output "expected_oidc_sub" {
  description = "Exact OIDC subject claim required to assume this role."
  value       = local.expected_sub
}

output "github_repository" {
  description = "Exact repository claim (owner/name) pinned in trust."
  value       = local.github_repository
}
