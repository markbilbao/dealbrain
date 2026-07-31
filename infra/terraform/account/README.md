# Account-level Terraform root (Sprint 25b.2)

Owns the **single** GitHub Actions OIDC provider for the AWS account:

`https://token.actions.githubusercontent.com`

## Apply order

1. Bootstrap remote state (S3 + DynamoDB) out-of-band if not already done
2. Apply **this** root (`account/`)
3. Apply `environments/staging` and `environments/production` with
   `github_oidc_provider_arn` set to this root’s `oidc_provider_arn` output
   (or via `terraform_remote_state` once backends are live)

## Validate (no apply)

```bash
cd infra/terraform/account
terraform init -backend=false
terraform validate
```

## Import (if provider already exists)

```bash
terraform import 'module.github_oidc.aws_iam_openid_connect_provider.github[0]' \
  arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com
```

Or set `create_provider = false` and pass `existing_provider_arn`.

## Boundaries

- Do **not** create this provider from staging or production roots
- Do **not** store AWS access keys or GHCR tokens here
- This root does **not** create deploy roles (those are environment-owned)
