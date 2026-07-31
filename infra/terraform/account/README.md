# Account-level Terraform root (Sprint 25b.2)

Owns the **single** GitHub Actions OIDC provider for the AWS account:

`https://token.actions.githubusercontent.com`

## Apply order

1. Bootstrap the encrypted S3 Terraform state bucket out-of-band if not already done
   (locking: S3 native lockfiles via `use_lockfile = true`; **not** DynamoDB)
2. Apply **this** root (`account/`) with a configured remote backend
3. Apply `environments/staging` (and later production) with
   `github_oidc_provider_arn` set to this root’s `oidc_provider_arn` output
   (or via `terraform_remote_state` once backends are live)

## Backend initialization

This root uses a partial S3 backend. Supply bucket/key/region at init:

```bash
cd infra/terraform/account
terraform init \
  -backend-config="bucket=dealbrain-terraform-state-<ACCOUNT_OR_SUFFIX>" \
  -backend-config="key=account/terraform.tfstate" \
  -backend-config="region=us-east-1"
terraform validate
# Operator only: terraform apply
```

See [../README.md](../README.md) for staging init and production deferral notes.

## Validate (CI / no apply)

```bash
cd infra/terraform/account
terraform init -backend=false
terraform validate
```

`-backend=false` is for validation and CI only — not for shared apply.

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
