variable "create_provider" {
  description = <<-EOT
    When true, create the account-level GitHub Actions OIDC provider.
    Set false and pass existing_provider_arn if the provider already exists
    in the account and should be referenced instead of created.
  EOT
  type        = bool
  default     = true
}

variable "existing_provider_arn" {
  description = <<-EOT
    ARN of a pre-existing GitHub Actions OIDC provider. Required when
    create_provider is false. Import path when adopting an existing provider
    into the account root (module is not count-indexed):
      terraform import 'module.github_oidc.aws_iam_openid_connect_provider.github[0]' \
        arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com
  EOT
  type        = string
  default     = ""

  validation {
    condition = (
      var.create_provider
      || (length(trimspace(var.existing_provider_arn)) > 0)
    )
    error_message = "existing_provider_arn is required when create_provider is false."
  }
}

variable "tags" {
  description = "Common tags for the OIDC provider."
  type        = map(string)
  default     = {}
}
