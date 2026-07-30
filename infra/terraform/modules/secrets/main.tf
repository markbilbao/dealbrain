# Secret *containers* only — values are set out-of-band (console/CLI/CI).
# Never put plaintext secret values in Terraform configuration or state
# intentionally; use aws_secretsmanager_secret_version outside of Git when needed.
#
# RDS master credentials are NOT created here: the RDS module enables
# manage_master_user_password so AWS stores the generated password in Secrets
# Manager. Runtime DATABASE_URL assembly is deferred to Sprint 25b.

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
