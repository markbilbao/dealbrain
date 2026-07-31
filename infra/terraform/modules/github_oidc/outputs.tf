output "oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider."
  value = (
    var.create_provider
    ? aws_iam_openid_connect_provider.github[0].arn
    : data.aws_iam_openid_connect_provider.existing[0].arn
  )
}

output "oidc_provider_url" {
  description = "URL of the GitHub Actions OIDC provider (no https:// prefix in AWS ARN form)."
  value = (
    var.create_provider
    ? aws_iam_openid_connect_provider.github[0].url
    : data.aws_iam_openid_connect_provider.existing[0].url
  )
}

output "arn" {
  description = "Alias for oidc_provider_arn (module contract)."
  value = (
    var.create_provider
    ? aws_iam_openid_connect_provider.github[0].arn
    : data.aws_iam_openid_connect_provider.existing[0].arn
  )
}

output "url" {
  description = "Alias for oidc_provider_url (module contract)."
  value = (
    var.create_provider
    ? aws_iam_openid_connect_provider.github[0].url
    : data.aws_iam_openid_connect_provider.existing[0].url
  )
}
