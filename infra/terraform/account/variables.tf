variable "aws_region" {
  description = "AWS region for the account-level root provider."
  type        = string
  default     = "us-east-1"
}

variable "create_provider" {
  description = <<-EOT
    Create the GitHub Actions OIDC provider (default true).
    Set false and supply existing_provider_arn if the provider already exists.
  EOT
  type        = bool
  default     = true
}

variable "existing_provider_arn" {
  description = <<-EOT
    Existing OIDC provider ARN when create_provider is false.
    Import example (when adopting a pre-existing provider into this root):
      terraform import 'module.github_oidc.aws_iam_openid_connect_provider.github[0]' \
        arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com
  EOT
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags."
  type        = map(string)
  default     = {}
}
