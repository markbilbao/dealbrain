output "oidc_provider_arn" {
  description = "ARN of the account-level GitHub Actions OIDC provider."
  value       = module.github_oidc.oidc_provider_arn
}

output "oidc_provider_url" {
  description = "URL of the account-level GitHub Actions OIDC provider."
  value       = module.github_oidc.oidc_provider_url
}
