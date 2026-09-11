# GitHub Environment `production` — owner UI steps

**Owner-controlled.** Workflows and Terraform do **not** create this Environment,
populate its variables, or attach reviewers. Create it in the GitHub UI after
merge, before any production deploy dispatch.

Do **not** put application secrets, database passwords, or GHCR tokens in GitHub.
Those belong in AWS Secrets Manager `dealbrain/production/*` (values out-of-band).

This document does not print secret values.

## After merge (required before Deploy Production)

Repository: `markbilbao/dealbrain`.

1. Open **Settings → Environments → New environment**.
2. Name it exactly `production` (lowercase). Save.
3. **Deployment branches and tags:** restrict to **`main` only** (custom branch
   policy / selected branches, not all branches).
4. **Required reviewers:** enable if the org plan supports it. Add at least one
   human owner. Deploy Production and Rollback Production both use
   `environment: production`, so a reviewer gate covers both.
5. **Prevent self-review** if the UI offers it.
6. **Allow administrators to bypass configured protection rules:** disable when
   the UI allows. If org policy forces admin bypass to remain on, record a written
   audit exception — do not treat that as equivalent to required reviewers.
7. Wait timer: optional (5–10 minutes). Not required for Early Access foundation.
8. Do **not** configure environment **secrets**. The workflows use OIDC only
   (`id-token: write` + `vars.AWS_ROLE_ARN`). There must be no
   `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` on this Environment.
9. Add Environment **variables** (names only; values come from the owner’s AWS
   account after production Terraform apply — this PR does not apply Terraform):

   | Name | Source after owner apply |
   |------|--------------------------|
   | `AWS_ROLE_ARN` | Terraform output `gha_deploy_role_arn` (`dealbrain-production-gha-deploy`) |
   | `AWS_REGION` | `us-east-1` |
   | `AWS_ACCOUNT_ID` | Twelve-digit production AWS account id |
   | `PRODUCTION_TARGET_GROUP_ARN` | Terraform output `alb_target_group_arn` |

10. Confirm the Environment is **not** named `prod`, `Production`, or `live`.
    OIDC trust is `repo:markbilbao@309556720/dealbrain@1314423275:environment:production`.
11. Confirm **Deploy Production** and **Rollback Production** remain
    `workflow_dispatch` on `refs/heads/main` only.

## What the owner must still do outside GitHub

- Apply isolated production Terraform (S3 backend `production/terraform.tfstate`,
  `use_lockfile = true`). Not this PR.
- Populate `dealbrain/production/*` secret **values** in AWS (never GitHub).
- Issue ACM (or origin TLS) and DNS cutover only when authorized. Not this PR.

## Verification (read-only)

After the Environment exists, `GET /repos/markbilbao/dealbrain/environments/production`
should return 200. Until then, production workflows cannot assume the OIDC role.
