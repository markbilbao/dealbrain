# Secret *containers* only — values are set out-of-band (console/CLI).
# Never put plaintext secret values in Terraform configuration or state
# intentionally. Do NOT add aws_secretsmanager_secret_version here for app
# keys or GHCR credentials — populate with AWS CLI/console after apply.
#
# RDS master credentials are NOT created here: the RDS module enables
# manage_master_user_password so AWS stores the generated password in Secrets
# Manager. Runtime DATABASE_URL assembly is deferred to Sprint 25b.3.
#
# ghcr_pull (Sprint 25b.2): classic PAT with read:packages only; host reads
# dealbrain/<env>/ghcr_pull. Expected shape (placeholders only in docs):
#   {"username":"REPLACE_ME_OUT_OF_BAND","token":"REPLACE_ME_OUT_OF_BAND"}

locals {
  prefix = "dealbrain/${var.environment}"
}

resource "aws_secretsmanager_secret" "this" {
  for_each = toset(var.secret_names)

  name                    = "${local.prefix}/${each.value}"
  description             = "DealBrain ${var.environment} secret: ${each.value}"
  recovery_window_in_days = var.environment == "production" ? 30 : 7

  tags = merge(var.tags, {
    Name        = "${local.prefix}/${each.value}"
    SecretPath  = "${local.prefix}/${each.value}"
    Environment = var.environment
  })
}
