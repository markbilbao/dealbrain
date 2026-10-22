# Sprint 40 IaC security scan (2026-10-20)

This record does not rewrite the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, the security-readiness package, the SAST gate, the secret scan, or the container-vulnerability records. It is not named Sprint 40.8. It is not a Sprint 40 reconciliation. It does not declare Sprint 40 ENGINEERING COMPLETE. No Terraform apply was performed. No deploy was performed. No AWS resource was changed.

## Starting point

- Starting `main`: `078d768f2653dc0ac69f94063ea04ff57584fe15`
- PR #207 is merged. This slice does not reuse it.
- Post-merge verification supplied for that commit: CI #517 SUCCESS, Build Image #182 SUCCESS
- Published deployment-authority digest at the start: `ghcr.io/markbilbao/dealbrain@sha256:1eb63088d25251d82331c55c37ff66173e2250a0305e1838187a7475c051a323`
- Container vulnerability scanning at the start: IMPLEMENTED-NOT-PROVEN
- IaC security scanning at the start: absent. `terraform fmt` and `terraform validate` are not this control.
- R6 at the start: PARTIAL
- Sprint 40 at the start: not ENGINEERING COMPLETE

## Scanner

Trivy is pinned at exactly `0.76.0`. That tag was the current stable GitHub release on 2026-10-20 (`published_at` `2026-10-14T11:45:44Z`, not a prerelease, not a draft). The official asset is `trivy_0.76.0_Linux-64bit.tar.gz`. Its SHA-256, taken from `trivy_0.76.0_checksums.txt` on the same release, is `e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7`.

`scripts/security/install_trivy.sh` downloads that archive and the published checksum file over HTTPS, requires the pinned digest to appear in the checksum file, and runs `sha256sum -c` before `tar` extracts `trivy`. The helper refuses a non-linux/amd64 host, refuses archive members that are absolute or contain `..`, and checks that the extracted binary prints `Version: 0.76.0`. It does not use `sudo`, `curl | sh`, `latest`, or an unpinned GitHub Action.

The gate does not use `aquasecurity/trivy-action`, tfsec, or Checkov. tfsec is not a second scanner. The checks bundle tag `mirror.gcr.io/aquasec/trivy-checks:2` is floating, so the gate does not use it. Each run passes `--skip-check-update` and a fresh `--cache-dir`. Trivy then logs `Falling back to embedded checks`. Those embedded checks from the pinned binary are the rule source. A different `ERROR` line, or `Ignore finding` on stderr, fails the gate.

## Scope

The only scan argument is `infra/terraform`. That tree contains `account/`, `environments/staging/`, `environments/production/`, and `modules/`. The command is `trivy config` with `--misconfig-scanners terraform`, `--tf-exclude-downloaded-modules`, `--skip-dirs **/.terraform/**`, and severities `UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL`. `--config=` and `--ignorefile=` are empty, which disables a Trivy config file and a `.trivyignore` file. The gate also rejects those files, and any `trivy:ignore` directive, in the Terraform tree.

The scan does not read Terraform state, does not init a backend, does not run `terraform apply`, and does not call AWS. No production credentials are required.

Trivy 0.76.0 reports one result row for each scanned root and extra rows for module files that have failures. On this tree the result targets are `account`, `environments/production`, `environments/staging`, and the module files that failed. Clean modules such as `ec2`, `iam`, `github_oidc`, `github_deploy_role`, and the SSM document modules are parsed through those roots and do not get their own failure row. The gate fails if any of the three roots is missing, if a result path leaves `infra/terraform`, if state or `.terraform` is a target, or if a Terraform directory is neither a result path nor a local module referenced from the scanned roots.

## Gate

`scripts/check_iac_security_baseline.py` requires Trivy `0.76.0`, parses the JSON itself, and fails closed when the report is missing, malformed, truncated, the wrong schema, the wrong artifact, or the wrong version. `MisconfSummary.Failures` must equal the number of `FAIL` findings in that result. A status other than `FAIL` or `PASS` fails the gate. Exit codes other than 0 fail the gate. Trivy's own exit code is forced to 0 when findings exist so the repository baseline, not the binary's exit code, is the verdict.

A finding identity is the rule id, severity, exact title, repository path, start and end line, resource address, caller path, caller resource, namespace, and the SHA-256 of that normalized identity. Severity alone is not an identity. Baseline exceptions cannot use wildcards, cannot use `accepted_risk`, and must carry a fingerprint that matches those fields. One exception matches one finding. A leftover exception is stale, or excess when it repeats a finding already matched. The committed baseline is version 1, scanner `trivy`, scope `infra/terraform`, checks `embedded`, and `exceptions: []`.

## Initial scan

The first scan, before the source edits below, used the same pinned binary and embedded checks.

| Item | Count |
|---|---|
| Terraform files | 70 |
| Findings | 30 |
| Critical | 6 |
| High | 9 |
| Medium | 5 |
| Low | 10 |
| Unknown | 0 |

Rule ids: `AWS-0017` (3), `AWS-0053` (2), `AWS-0054` (2), `AWS-0089` (3), `AWS-0098` (2), `AWS-0104` (4), `AWS-0132` (3), `AWS-0133` (2), `AWS-0164` (4), `AWS-0176` (2), `AWS-0177` (1), `AWS-0178` (2).

No exception was written from that inventory.

## Fixes

Two findings were source defects that did not change the documented architecture. They were edited and the tree was scanned again. Nothing was applied.

- `AWS-0164` (High, four results). Public subnets set `map_public_ip_on_launch = true`. Those subnets exist so the internet-facing ALB and the NAT gateway have a route to the internet gateway. Neither of those resources uses this flag. The API instance is in a private subnet with `associate_public_ip = false`. The flag is now `false`, so an instance launched in a public subnet does not receive a public address by default. An instance can still set its own association explicitly.
- `AWS-0104` on `aws_vpc_security_group_egress_rule.alb_all` (Critical, staging and production). The rule was all protocols to `0.0.0.0/0`. Its comment said the ALB egress was for VPC targets. The only target is the API security group on TCP 8000, which is already the API ingress pair. The rule is now `aws_vpc_security_group_egress_rule.alb_to_api`: TCP 8000 to that security group. The next Terraform apply, which this slice does not run, would replace the old rule address.

The rescan no longer reports `AWS-0164` or the ALB `AWS-0104` results.

## Findings left for an owner decision

The baseline is still empty. These 24 findings are unbaselined. They were not risk-accepted. Critical and High findings were not given a convenience exception. False-positive and not-applicable notes below are proposals only.

| Rule | Severity | Count | Resource | Classification |
|---|---|---|---|---|
| AWS-0054 | Critical | 2 | `aws_lb_listener.http_forward` via `module.alb`, lines 83–94, staging and production | Real. Both environments default `alb_certificate_arn` to empty. Staging documents that empty value as the HTTP bootstrap. Production says the ARN is required before public traffic, but the committed default is still empty, so the listener forwards HTTP. Removing it, or inventing a certificate, changes that bootstrap. Not fixed. Not baselined. |
| AWS-0104 | Critical | 2 | `aws_vpc_security_group_egress_rule.api_all`, line 73, staging and production | Real. The API security group allows all egress to `0.0.0.0/0`. `docs/architecture/SPRINT_25B2_AWS_OIDC_AND_DEPLOY_IAM.md` records that egress as required for GHCR, Secrets Manager, SSM, and RDS while NAT is the path. Closing it needs VPC endpoints or an equivalent architecture change. Not fixed. Not baselined. |
| AWS-0053 | High | 2 | `aws_lb.this` `internal = false`, staging and production | Real public exposure, and it is the documented internet-facing ALB. Making the load balancer internal removes public ingress. Not fixed. Not baselined. |
| AWS-0132 | High | 1 | production ALB access-log bucket, lines 90–99, SSE-S3 `AES256` | Not applicable as a CMK change. The check text says SSE-KMS is not supported for an S3 server access-log destination and that SSE-S3 should be used there. The bucket already uses SSE-S3, blocks public access, and denies insecure transport. Switching it to a CMK would fight the delivery path. Proposed only. Not baselined. |
| AWS-0132 | High | 2 | release-artifacts bucket, lines 42–51, staging and production | Real hardening choice. The buckets are already encrypted with SSE-S3. A customer managed key changes the key policy and the host role that reads bundles. Not fixed. Not baselined. |
| AWS-0178 | Medium | 2 | VPC has no flow log, staging and production | Real visibility gap. Adding a flow log is a new log destination and a cost. Operational monitoring remains Sprint 42. Not shown here to be a separate launch-blocking defect. Not fixed. Not suppressed. |
| AWS-0176 | Medium | 2 | RDS IAM database authentication off, staging and production | Real optional control. The instance uses `manage_master_user_password`. The application path is that secret, not IAM database authentication. Turning the flag on does not replace that design. Not fixed. Not baselined. |
| AWS-0177 | Medium | 1 | `deletion_protection` on staging only, line 35 | Real for staging, and the staging variable default is `false`. Production's default is `true`, and Trivy did not report production. Forcing staging on changes the documented staging destroy posture. Not fixed. Not baselined. |
| AWS-0017 | Low | 3 | production CloudWatch log groups, lines 22–33, 35–46, and 48–59 | Real CMK request. The groups use AWS default encryption. A customer managed key is new key management. Not fixed. Not baselined. |
| AWS-0089 | Low | 3 | ALB log bucket (production) and release-artifacts bucket (staging and production) | Real access-logging request. The ALB bucket is the log destination. Another bucket would be required to log it. Not fixed. Not baselined. |
| AWS-0133 | Low | 2 | RDS Performance Insights off, staging and production | Real monitoring add-on. It is not a network or encryption defect. Not fixed. Not baselined. |
| AWS-0098 | Low | 2 | Secrets Manager secrets with no `kms_key_id`, staging and production | Real CMK request. The resources do not select a weaker custom key; AWS applies its default key when `kms_key_id` is omitted. A customer managed key is new key management. Not fixed. Not baselined. |

Trivy did not report the staging and production ingress default `0.0.0.0/0` on ports 80 and 443. That default is unchanged. This record does not invent a finding for it.

`AWS-0054` has no source-resource occurrence in the JSON. The gate keeps Trivy's caller resource `module.alb` plus the file and line range. The other rows above use the occurrence resource when Trivy emitted one.

## Final scan

```
iac_security_gate: FAIL
scanner=trivy
scanner_version=0.76.0
scope=infra/terraform
checks=embedded
sha256=e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7
terraform_files=70
findings=24
exceptions=0
critical=4
high=5
medium=5
low=10
unknown=0
```

Exit code 1. Every remaining finding is unbaselined. The gate did not pass.

## Local tests

`tests/unit/test_sprint40_iac_security_baseline.py` covers the pinned version, a wrong version, malformed JSON, missing results, a wrong artifact and a missing root, state outside the tree, an unknown finding, an exact exception, a stale exception, an excess duplicate exception, wildcard and malformed exceptions, severity counts, path and resource identity, and a `trivy:ignore` directive or ignore file. The committed baseline is empty. A synthetic finding fails that baseline.

Local commands on this tree:

| Check | Result |
|---|---|
| IaC gate | FAIL, exit 1. 70 Terraform files, 24 findings, 0 exceptions, 4 Critical, 5 High, 5 Medium, 10 Low, 0 Unknown |
| IaC gate unit tests | Passed inside the full pytest run |
| `terraform fmt -check -recursive infra/terraform` | Pass, Terraform 1.15.8 |
| `terraform validate` account | Success, `-backend=false` |
| `terraform validate` staging | Success, `-backend=false` |
| `terraform validate` production | Success, `-backend=false` |
| Ruff baseline | OK. check 91, unformatted 82, no new regressions |
| Secret scan | OK. 815 files, 650 application Python files, 8 findings, 8 exceptions |
| pip-audit 2.10.1 | OK. 73 packages, 0 vulnerabilities, 0 exceptions |
| Bandit 1.9.4 | OK. 650 files, 34 findings, 34 exceptions |
| Full pytest | 4585 passed, 8 skipped, and 1 failed. The failure was `test_reviewed_demo_exceptions_are_exact_and_a_new_credential_fails` expecting 813 scanned files. The gate script and installer are two new files under `scripts/`, so the scan reads 815. The assertion was updated to 815. No new secret finding was reported. The secret-scan file and the IaC gate tests then passed together (26). The CI architecture-lock set passed (303). The full suite was not repeated after that one-line count change. |
| Docker Compose config | Pass for production and staging. `docker compose config` exited 0 for both overlays. |

No image was published.

## CI

`.github/workflows/ci.yml` keeps Terraform fmt, Terraform validate, Ruff, contracts, pytest, the secret scan, pip-audit, Bandit, the Grype container scan, and Compose validation. The Terraform job installs Trivy 0.76.0 and runs `python scripts/check_iac_security_baseline.py` after validate. The job has no AWS credentials and no production secrets. A failing gate fails the job. `build-image.yml` is unchanged and does not run this scan.

Because the baseline is empty and 24 findings remain, the Terraform job fails closed. That is the verdict. IaC security scanning is implemented and fail-closed. It is not a passing control. It is not PROVEN. It is not IMPLEMENTED-NOT-PROVEN, because this slice uses that label only when the gate is in CI and CI passes.

GitHub Actions run `39415287343` on draft PR #208 finished with conclusion `failure` at head `f21612defeb8ac1a8e14f09f597143f1b66e650a`. The Terraform job installed Trivy 0.76.0, passed fmt and the three validates, and failed on `python scripts/check_iac_security_baseline.py`. The step log matches the local gate: 70 Terraform files, 24 findings, 0 exceptions, 4 Critical, 5 High, 5 Medium, 10 Low, 0 Unknown. Docker image build, Docker Compose config, and Lint, contracts, and pytest succeeded. The pytest job includes the secret scan, pip-audit, Bandit, contract tests, architecture-lock tests, and the full suite.

## R6

Secret scanning, dependency scanning, SAST, and container vulnerability scanning stay as they were on the starting commit. Container vulnerability scanning stays IMPLEMENTED-NOT-PROVEN. The Terraform class now has one pinned scanner in CI, and that scanner does not pass. R6 stays PARTIAL. No Included requirement is PROVEN. Sprint 40 stays Planned and is not ENGINEERING COMPLETE. This record does not select Sprint 41.

## Supply chain, left for the later reconciliation

The Docker dependency stage still copies from `ghcr.io/astral-sh/uv:latest` (`Dockerfile`, `COPY --from=ghcr.io/astral-sh/uv:latest`). That floating build-tool reference was not changed. The later Sprint 40 reconciliation should evaluate it against the supply-chain and immutable-build requirement. It did not block this IaC scan.

## What this slice did not do

- No `terraform apply`
- No deploy
- No AWS mutation, account creation, secret rotation, or live resource scan
- No staging or production configuration
- No Shopify activation, live research, routing change, or affiliate change
- No image publication
- No second IaC scanner
- No baseline exception

## Owner decisions applied (2026-10-22)

This section does not rewrite the inventory above. It records the owner decisions applied on the same draft branch. No Terraform apply was performed. No deploy was performed. No AWS resource was changed. The baseline is still empty.

`AWS-0054` was fixed in source. `infra/terraform/modules/alb/main.tf` no longer has `aws_lb_listener.http_forward`. The HTTPS listener still exists only when `certificate_arn` is non-empty. Port 80 is `aws_lb_listener.http_redirect`, and only when `certificate_arn` is non-empty and `enable_http_redirect` is true. An empty certificate creates no public application listener. Variable descriptions in the ALB module, staging, and production, plus the Terraform README, `docs/SPRINT_25A_INFRASTRUCTURE.md`, the staging deploy pipeline note, and the production cutover runbook, no longer say that an empty certificate means an HTTP-only bootstrap.

`AWS-0104` on `aws_vpc_security_group_egress_rule.api_all` was removed. API egress is now two rules: `api_https` (TCP 443 to `0.0.0.0/0`) and `api_to_rds` (TCP 5432 to the RDS security group). There is no `ip_protocol = "-1"` rule. No DNS egress rule was added. The RDS security group still has `egress = []`.

The pinned Trivy 0.76.0 rescan, with the baseline still empty, reported 22 findings: 2 Critical, 5 High, 5 Medium, 10 Low, 0 Unknown. Both `AWS-0054` findings are gone. Both `api_all` findings are gone. The rescan added two new Critical findings:

| Rule | Severity | Resource | Caller | Lines | Fingerprint |
|---|---|---|---|---|---|
| AWS-0104 | Critical | `aws_vpc_security_group_egress_rule.api_https` | `environments/staging/main.tf` `module.security_groups` | `modules/security_groups/main.tf` 77–77 | `9e8497f7734dd975357b9c7cb37bf14d95e1267bdbf294098a2aeecfce90c9e9` |
| AWS-0104 | Critical | `aws_vpc_security_group_egress_rule.api_https` | `environments/production/main.tf` `module.security_groups` | `modules/security_groups/main.tf` 77–77 | `d0ad7490521db278f1841a1efb7c6c40f0656309d04d97c8f8ed345dcfd1d277` |

Title: "A security group rule should not allow unrestricted egress to any IP address." The checked line is `cidr_ipv4 = "0.0.0.0/0"` on TCP 443. That is the owner-required HTTPS egress for GHCR, Secrets Manager, SSM, and CloudWatch APIs. It is a new Critical finding. It was not baselined. The five approved High exceptions were not loaded, because this rescan did not leave only those High findings. The gate stays fail-closed.

The five High findings that the owner had approved, and that this rescan still reports unchanged, are not exceptions in the baseline:

| Rule | Caller | Fingerprint |
|---|---|---|
| AWS-0053 | staging `module.alb` | `30c2ab0c289c6db05f9c6fb9a75c52dad58ef16b0c927949e296167d0b3f93c1` |
| AWS-0053 | production `module.alb` | `6f477aef7e895a5e0c234f45d31c8b0c4791d8a63fb952f259b19795222a57f7` |
| AWS-0132 | production `module.logging` ALB access-log bucket, lines 90–99 | `04f17ed0a254dd3c106d1b296becd39faa2c1f2bacd5f915d1d8bfd8429e561c` |
| AWS-0132 | staging `module.release_artifacts`, lines 42–51 | `2dea7fcaa85f683d00fb3b6fbd6e088ea5636c76575d6da04454777321a24471` |
| AWS-0132 | production `module.release_artifacts`, lines 42–51 | `83eddb869b1914609e89ea10a3faf7a45bd71bb9fc805abb0305811a1245fdfe` |

Medium and Low findings are unchanged from the 24-finding rescan: AWS-0178 (2), AWS-0176 (2), AWS-0177 (1), AWS-0017 (3), AWS-0089 (3), AWS-0133 (2), AWS-0098 (2). None were baselined.
