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

A finding identity is the rule id, severity, exact title, repository path, start and end line, resource address, caller path, caller resource, namespace, and the SHA-256 of that normalized identity. Severity alone is not an identity. Baseline exceptions cannot use wildcards and must carry a fingerprint that matches those fields. Allowed rationales are `false_positive`, `not_applicable`, and `accepted_risk`. `accepted_risk` records one explicit owner acceptance of one exact finding. One exception matches one finding. A leftover exception is stale, or excess when it repeats a finding already matched. The committed baseline is version 1, scanner `trivy`, scope `infra/terraform`, checks `embedded`. It began empty. It now lists the two `api_https` acceptances, the five High treatments, the two AWS-0176 password-authentication acceptances, and the ten Low acceptances recorded below. The VPC flow-log and staging deletion-protection Medium findings were removed in source. The two AWS-0133 findings were removed in source. Enabling Performance Insights without a customer-managed key added two AWS-0078 findings. The owner later accepted both for the PH-first controlled beta. Those rows are recorded below.

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

## AWS-0104 `api_https` classification (2026-10-22)

This section records an owner decision for the two remaining Critical findings. It does not accept the risk. Preserving NAT for the PH-first controlled public beta is under consideration and is not formal acceptance. The baseline stays empty. `RATIONALES` in `scripts/check_iac_security_baseline.py` stays `false_positive` and `not_applicable`. No Terraform, scanner, or gate file changed in this slice. No `terraform apply` was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation.

Recommended classification: real architectural exposure, pending explicit acceptance. The label that can record that acceptance later is `accepted_risk`. That label is absent from the gate. `not_applicable` is untrue here. `false_positive` is untrue here.

### Why outbound HTTPS through NAT is required

The API host is in a private subnet with `associate_public_ip = false`. Staging and production both default `enable_nat_gateway` to true. The private route table sends `0.0.0.0/0` to the NAT gateway. There is no `aws_vpc_endpoint` in `infra/terraform`.

That path is what the host uses for:

- Amazon Linux 2023 `dnf` during bootstrap, including `docker`, `awscli`, and, on production, `amazon-ssm-agent`.
- `https://download.docker.com` for the Docker Inc GPG key and the `docker-compose-plugin` RPM. The host keeps the Amazon Linux `docker` RPM.
- `ghcr.io` login and `docker pull`. `scripts/deploy/host/ghcr-login.sh` reads `dealbrain/<env>/ghcr_pull` from Secrets Manager. Host IAM denies `ecr:*`.
- Public AWS HTTPS APIs that the instance role calls today: Secrets Manager, STS, S3 release bundles and evidence, CloudWatch Logs, SSM (`ssm`, `ssmmessages`, `ec2messages`), and the deploy-time EC2 and load-balancer describe calls.

`api_to_rds` is separate: TCP 5432 to the RDS security group only. The RDS security group keeps `egress = []`. Amazon-provided DNS does not use an API security-group DNS rule. Those paths are outside this finding.

### Why staging and production both report it

`aws_vpc_security_group_egress_rule.api_https` is one resource in `infra/terraform/modules/security_groups/main.tf`. Staging `module.security_groups` and production `module.security_groups` each instantiate that module. Trivy emits one finding per caller. The checked line in both is `cidr_ipv4 = "0.0.0.0/0"` at line 77. Title: "A security group rule should not allow unrestricted egress to any IP address." Namespace: `builtin.aws.ec2.aws0104`. Severity: CRITICAL. Rule: AWS-0104.

| Environment | Caller | Resource | Path | Fingerprint |
|---|---|---|---|---|
| staging | `infra/terraform/environments/staging/main.tf` `module.security_groups` | `aws_vpc_security_group_egress_rule.api_https` | `infra/terraform/modules/security_groups/main.tf` 77–77 | `9e8497f7734dd975357b9c7cb37bf14d95e1267bdbf294098a2aeecfce90c9e9` |
| production | `infra/terraform/environments/production/main.tf` `module.security_groups` | `aws_vpc_security_group_egress_rule.api_https` | `infra/terraform/modules/security_groups/main.tf` 77–77 | `d0ad7490521db278f1841a1efb7c6c40f0656309d04d97c8f8ed345dcfd1d277` |

CI run `39764647224` on head `7c744f7a62315d6d03aa567d929445bcdf2f637e` reported these two fingerprints with the same identities. The Terraform job failed on the empty baseline. The other CI jobs passed.

### Bounded Terraform source fix

No edit limited to this security-group rule can delete `0.0.0.0/0` and keep the current bootstrap and deploy path. A security group matches IP addresses and ports. It cannot name `ghcr.io`, the Amazon Linux mirrors, or `download.docker.com`. Those names are not stable AWS prefix lists. Replacing the CIDR with a snapshot of third-party addresses would break the next address change and would still miss the public AWS APIs unless those APIs moved too.

Interface VPC endpoints for Secrets Manager, STS, CloudWatch Logs, SSM, EC2, and Elastic Load Balancing, plus an S3 gateway endpoint, would move those AWS calls off the public internet. They would leave GHCR, `dnf`, and `download.docker.com` on HTTPS to the internet. The `api_https` rule, and AWS-0104, would remain. Removing that remaining public HTTPS path means a different image and bootstrap design, such as a prebaked AMI or an in-VPC registry. That is an architecture change, outside a bounded source fix.

### Residual risk of TCP 443 to `0.0.0.0/0`

Any process on the API instance can open TCP port 443 to any IPv4 address. NAT translates that connection to the internet. The rule allows no other port and no other protocol. The instance stays unreachable from the internet on this rule: API ingress is TCP 8000 from the ALB security group only, `associate_public_ip` is false, and the subnet is private. A person who already has code execution on that host can use the rule to send HTTPS anywhere, including hosts other than GHCR, the package mirrors, and AWS. The rule cannot limit destinations by hostname.

### Why `not_applicable` cannot describe these findings

AWS-0104 fires because the committed rule sets `cidr_ipv4 = "0.0.0.0/0"`. The scanner read that line correctly, so `false_positive` is untrue. The check's control, "do not allow unrestricted egress," applies to this rule. Keeping the rule is a choice to retain a broad egress path. `not_applicable` would hide that choice. The gate rejects `accepted_risk` today: `test_wildcard_and_malformed_exceptions_are_rejected` expects `load_baseline` to fail when an exception uses that rationale.

### Smallest policy change, not implemented

When the owner explicitly accepts this NAT path, the smallest policy change is:

1. Add `accepted_risk` to `RATIONALES` in `scripts/check_iac_security_baseline.py`.
2. Point the existing rejection test at a different illegal token, so unknown rationales still fail.
3. Add exactly two baseline exceptions, one per identity in the table above, with rationale `accepted_risk` and a one-line reason that names `api_https`, TCP 443, `0.0.0.0/0`, the private host, and the retained NAT path for GHCR, package mirrors, and public AWS APIs.

That change adds no new exception fields, no wildcard, and no rule-wide suppression. It does not load the five previously approved High findings unless a later approval says these Criticals no longer block them. This slice does not make the policy change and does not add the exceptions.

### Cost and architecture

This slice adds no AWS spend. Leaving the current design in place keeps the NAT charges already in the defaults: staging uses one NAT gateway (`single_nat_gateway` default true); production uses one NAT gateway per public subnet (`single_nat_gateway` default false). NAT is billed per gateway-hour and per gigabyte processed. Interface endpoints would add hourly and data charges per endpoint per Availability Zone and would still leave AWS-0104 in place while GHCR and the package mirrors use the public internet. An S3 gateway endpoint has no hourly charge and does not remove this finding by itself.

## Owner acceptance of the two `api_https` findings (2026-10-22)

On October 22, 2026 the owner explicitly accepted the residual outbound HTTPS risk for the two AWS-0104 findings below, and approved retaining outbound TCP 443 to `0.0.0.0/0` through NAT for the current PH-first controlled public beta. That acceptance covers these two findings only. It does not approve unrestricted all-protocol egress. It does not approve the five High findings or any Medium or Low finding.

`accepted_risk` is now an allowed rationale in `scripts/check_iac_security_baseline.py`. The baseline lists exactly two exceptions. Each one uses the full identity from the pinned Trivy 0.76.0 scan, rationale `accepted_risk`, and a one-line reason naming `api_https`, TCP 443 to `0.0.0.0/0`, the private EC2 application host, the NAT egress architecture, the required external HTTPS services, and the explicit owner risk acceptance.

| Environment | Caller | Fingerprint |
|---|---|---|
| staging | `infra/terraform/environments/staging/main.tf` `module.security_groups` | `9e8497f7734dd975357b9c7cb37bf14d95e1267bdbf294098a2aeecfce90c9e9` |
| production | `infra/terraform/environments/production/main.tf` `module.security_groups` | `d0ad7490521db278f1841a1efb7c6c40f0656309d04d97c8f8ed345dcfd1d277` |

Both rows are resource `aws_vpc_security_group_egress_rule.api_https`, path `infra/terraform/modules/security_groups/main.tf` lines 77–77, namespace `builtin.aws.ec2.aws0104`, severity CRITICAL, title "A security group rule should not allow unrestricted egress to any IP address."

Residual risk that remains accepted for this beta: any process on the private API instance can open TCP 443 to any IPv4 address, and NAT translates that connection to the internet. The rule allows no other port and no other protocol. Ingress stays TCP 8000 from the ALB security group. A person who already has code execution on that host can send HTTPS to destinations other than GHCR, the package mirrors, and AWS, because the security group cannot filter by hostname.

Outbound controls need another review before wider production exposure. The five High findings and the Medium and Low findings stay unbaselined. The IaC gate still fails closed on those remaining findings. No `terraform apply` was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation.

## Owner treatment of the five High findings (2026-10-22)

On October 22, 2026 the owner approved narrowly scoped treatment of the five previously reviewed High findings. The two `api_https` exceptions above are unchanged. Medium and Low findings stay unbaselined. No Terraform source changed. No `terraform apply` was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation.

The pinned Trivy 0.76.0 scan still reports 22 findings. These five identities match the current scan.

| Rule | Environment | Rationale | Caller | Lines | Fingerprint |
|---|---|---|---|---|---|
| AWS-0053 | production | `accepted_risk` | `module.alb` | `modules/alb/main.tf` 3–3 | `6f477aef7e895a5e0c234f45d31c8b0c4791d8a63fb952f259b19795222a57f7` |
| AWS-0053 | staging | `accepted_risk` | `module.alb` | `modules/alb/main.tf` 3–3 | `30c2ab0c289c6db05f9c6fb9a75c52dad58ef16b0c927949e296167d0b3f93c1` |
| AWS-0132 | production ALB logs | `not_applicable` | `module.logging` | `modules/logging/main.tf` 90–99 | `04f17ed0a254dd3c106d1b296becd39faa2c1f2bacd5f915d1d8bfd8429e561c` |
| AWS-0132 | staging release artifacts | `accepted_risk` | `module.release_artifacts` | `modules/release_artifacts/main.tf` 42–51 | `2dea7fcaa85f683d00fb3b6fbd6e088ea5636c76575d6da04454777321a24471` |
| AWS-0132 | production release artifacts | `accepted_risk` | `module.release_artifacts` | `modules/release_artifacts/main.tf` 42–51 | `83eddb869b1914609e89ea10a3faf7a45bd71bb9fc805abb0305811a1245fdfe` |

### Production public ALB

`aws_lb.this` sets `internal = false`. That is the public entry for the controlled public beta. The canonical public hostname in the Sprint 41 production plan is `piqsavi.com`. The API instance stays in a private subnet with `associate_public_ip = false`. Its only ingress is TCP 8000 from the ALB security group. The HTTPS listener exists only when `certificate_arn` is non-empty. Port 80 is a redirect to HTTPS only when that certificate is set and `enable_http_redirect` is true. There is no HTTP forward listener.

Residual exposure: once a certificate is present, any internet client that can reach the ALB can open the public listener. `allowed_ingress_cidrs` still defaults to `0.0.0.0/0`. Production DNS cutover remains a later gate. The owner accepts that public exposure for this beta.

### Staging public ALB

Public staging is required by existing evidence, so this finding is `accepted_risk`.

`https://staging.piqsavi.com` is the documented public staging hostname, and the 2026-09-10 launch-readiness record maps it to the staging ALB. Owner browser checks, identity-email links (`PUBLIC_APP_BASE_URL=https://staging.piqsavi.com`), and Shopify fetches of the public UCP profile use that hostname from the internet. An internal load balancer would remove those paths. The same private-host, ALB-only ingress, and certificate-gated listener controls apply. Staging does not pass a separate `internal` flag; the shared module sets `internal = false`.

Residual exposure: staging ingress also defaults to `0.0.0.0/0`. Anyone on the internet can reach the staging listener when a certificate is configured. The Terraform `domain_name` default is still the placeholder `staging.dealbrain.example`. The live hostname evidence is the staging DNS and browser record above, not that placeholder.

### Production ALB access-log bucket

This bucket is `module.logging`, and production passes its name to `module.alb` as `access_logs_bucket`. Its default encryption is SSE-S3 (`AES256`). Current AWS Application Load Balancer documentation, [Enable access logs for your Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/enable-access-logging.html), says the only supported server-side encryption option for that destination is Amazon S3-managed keys (SSE-S3). The troubleshooting section says a bucket that uses an unsupported encryption option must be changed back to SSE-S3. A customer-managed KMS key would make this destination invalid for ALB log delivery, so the CMK recommendation does not apply. The exception rationale is `not_applicable`. Staging does not enable this bucket.

### Release-artifacts buckets

Staging and production each instantiate `module.release_artifacts`. Both buckets use SSE-S3, block all four public-access settings, enable versioning, and deny non-TLS transport. The module contract is integrity-checked deploy bundles and append-only deploy evidence. Application secrets are Secrets Manager resources. No Terraform backend in this repository targets these buckets. Host IAM is limited to `releases/*` and `evidence/*`.

The bucket-policy comment mentions denying use as Terraform state. The policy statement itself is `DenyInsecureTransport` only. That statement does not add a separate state-key deny.

The owner accepts SSE-S3 for the controlled beta on both buckets. Residual limitation: the account cannot attach a key policy, disable the key, or record separate KMS decrypt events for these objects. Encryption at rest remains Amazon S3-managed AES-256.

## Owner treatment of the five Medium findings (2026-10-22)

On October 22, 2026 the owner approved a limited treatment of the five Medium findings. The seven earlier exceptions are unchanged. No Low finding was baselined. No `terraform apply` was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation and it does not start Sprint 41 or Sprint 42.

### AWS-0178 REJECT flow logs

Staging and production each get one VPC-level flow log from `module.networking`. `traffic_type` is `REJECT`. The destination is a dedicated S3 bucket in that module, not the ALB access-log bucket. The bucket blocks public access, denies non-TLS transport, and expires current and noncurrent objects after 14 days. Delivery is limited to `delivery.logs.amazonaws.com` `s3:PutObject` on `AWSLogs/<account>/*` and `s3:GetBucketAcl` on the bucket, each conditioned on `aws:SourceAccount`, `aws:SourceArn`, and, for the write, `s3:x-amz-acl = bucket-owner-full-control`. The API instance role gains no permission.

SSE-S3 on this bucket produced a new High AWS-0132 in a pinned Trivy 0.76.0 probe. That design was not committed. VPC flow logs can use a customer-managed key, unlike ALB access logs, so the bucket uses SSE-KMS with the key ARN, annual rotation, and a delivery key-policy statement for the same service principal and source conditions. The account root keeps `kms:*` on that key so IAM can administer it. The rescan of this tree added no new Critical or High finding.

The same rescan added two Low AWS-0089 results, one per environment, on `aws_s3_bucket.flow_logs` at `modules/networking/main.tf` lines 184–191. Staging fingerprint `125d716eb7d515ffd2e36df7fd025653ab36496e3ca7f2a708eeb56415427cf6`. Production fingerprint `35e2f7db63b0a19ff5dfa5ab45d65e74c339c3eb5301f62771d615a711a948b9`. They are not baselined. A second bucket for server access logs would move the same Low, and an SSE-S3 logging bucket would reintroduce AWS-0132. Security settings were not weakened to clear it.

REJECT-only flow logs do not monitor successful outbound HTTPS. Accepted NAT traffic to GHCR, package mirrors, and AWS APIs is absent from these logs. Successful outbound traffic monitoring and alerting remain an explicit future operational requirement. This slice does not implement that monitoring and does not complete Sprint 42.

These resources are source only. A later apply would create two customer-managed keys and two buckets and would start vended-log delivery charges. This slice does not apply them and does not incur those charges.

### AWS-0176 password authentication

`iam_database_authentication_enabled` stays unset. The application still builds `DATABASE_URL` from the AWS-managed RDS master secret in Secrets Manager. Enabling the RDS flag would not switch that path, and granting `rds_iam` to the master user would make IAM authentication take precedence over the password.

The owner accepts that password design temporarily for the controlled beta. The baseline adds exactly two `accepted_risk` rows for the current identities. Both are `module.rds`, `modules/rds/main.tf` lines 10–48, namespace `builtin.aws.rds.aws0176`, title "RDS IAM Database Authentication Disabled".

| Environment | Caller | Fingerprint |
|---|---|---|
| staging | `infra/terraform/environments/staging/main.tf` `module.rds` | `22c9faba3fe761322af784f2c7ca20c9ec8930fcb5a14b0e5463bec325ab4af2` |
| production | `infra/terraform/environments/production/main.tf` `module.rds` | `116e42aeb1fd6b8967dd296973a5e58f2ed29d7461f3b4525aa864134d45acbb` |

Residual risk: the master password in the AWS-managed secret remains the application credential. A least-privileged application DB credential must be reviewed before launch. A future IAM database authentication migration is a separate decision and is not implemented here.

### AWS-0177 staging deletion safety

Staging `deletion_protection` now defaults to `true`, and staging `skip_final_snapshot` now defaults to `false`. Production behavior is unchanged. Staging backup retention stays 7 days. Staging Multi-AZ stays off. The staging example tfvars matches those defaults. No staging teardown script required the old skip.

Deletion now requires deliberate operator intervention: protection must be turned off before destroy, and destroy writes a final snapshot. That snapshot may incur storage charges. The pinned scan no longer reports AWS-0177.

## Owner treatment of the twelve Low findings (2026-10-22)

On October 22, 2026 the owner approved ten exact `accepted_risk` exceptions and a source fix for the two AWS-0133 findings. The nine earlier exceptions are unchanged. No `terraform apply` was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation and it does not start Sprint 41.

### AWS-0017 CloudWatch log groups

Production `module.logging` keeps service-managed encryption on `aws_cloudwatch_log_group.api`, `host`, and `migrate`. The baseline adds three `accepted_risk` rows. Each names the controlled beta, records that customer-managed encryption keys are absent on that CloudWatch log group, and requires review before wider production exposure.

| Group | Lines | Fingerprint |
|---|---|---|
| api | 22–33 | `56153c2beb2134bc7eb835981d509c7a240aa18e30636480971ddaba6cfea0f6` |
| host | 35–46 | `318f0c59debc260c5579c753143c6fdf6427d85b31a053a3685fb8ae845f1c79` |
| migrate | 48–59 | `be8af6d106f002fa5417333c2867abaab914e87f64ae63f565a13013760ecf81` |

### AWS-0089 S3 server access logging

Five buckets stay without S3 server access logging. The baseline adds five `accepted_risk` rows. Each records that S3 server access logging is absent and requires review before wider production exposure.

| Bucket | Caller | Lines | Fingerprint |
|---|---|---|---|
| ALB access logs | production `module.logging` | 61–71 | `4abda7579a6361f0a0734027b9318a9080c6aac7a64d34236db70c4a888d9c07` |
| release artifacts | staging `module.release_artifacts` | 12–23 | `e3053edc21bbd18841654e03ca7d06626d22befbbb7cd36ff2d71fa3aaf51c89` |
| release artifacts | production `module.release_artifacts` | 12–23 | `e8bf73e72445f0b5b33db881b99caf497172d76b624a35e33f195b18818fe05c` |
| VPC flow logs | staging `module.networking` | 184–191 | `125d716eb7d515ffd2e36df7fd025653ab36496e3ca7f2a708eeb56415427cf6` |
| VPC flow logs | production `module.networking` | 184–191 | `35e2f7db63b0a19ff5dfa5ab45d65e74c339c3eb5301f62771d615a711a948b9` |

### AWS-0098 Secrets Manager

Both secret modules keep the AWS managed key `aws/secretsmanager`. The baseline adds two `accepted_risk` rows. Each records that customer-managed encryption keys are absent on the Secrets Manager resources and requires review before wider production exposure. These rows do not cover the RDS-managed master secret.

| Environment | Fingerprint |
|---|---|
| staging | `f3bc24f32f07b4e1a9e962d8ca96b42c6dd233a0a1b4b9ce6e51904adbfa0894` |
| production | `c297fffc3fbf710a044d003d8cffe64be9fb0c5fc814d70b744399f4b2207ae1` |

### AWS-0133 Database Insights Standard

The locked AWS provider is `5.100.0` in the account, staging, and production lock files. That provider's `aws_db_instance` schema includes `database_insights_mode` (`standard` or `advanced`), `performance_insights_enabled`, and `performance_insights_retention_period`. Retention `7` is an allowed value. None of those three attributes is `ForceNew`. Create and modify both send them on `CreateDBInstance` and `ModifyDBInstance`. The module sets Standard mode, Performance Insights on, and seven-day retention for the shared RDS module used by staging and production. It does not set Advanced mode, a retention above 7 days, `performance_insights_kms_key_id`, Enhanced Monitoring, or `apply_immediately`.

PostgreSQL authentication, instance classes, backup retention, deletion protection, final snapshots, storage encryption, and the private network settings are unchanged. The `aws_db_instance.this` block remains lines 10–48, so the two AWS-0176 identities stay the same.

AWS documents that modifying a DB instance to enable Database Insights Standard does not cause downtime. The provider update path is `ModifyDBInstance`, so a later apply is an in-place change rather than a replacement. `apply_immediately` stays unset. This slice does not apply that change.

The pinned Trivy 0.76.0 rescan no longer reports AWS-0133. It reports two new Low AWS-0078 findings, one per environment, on the same `module.rds` block at lines 10–48. The title is "Performance Insights encryption should use Customer Managed Keys." Staging fingerprint `fb297b059e4a46f9e77f937c731e042d1c4697d9e5e1095b8ee94006b79f3c86`. Production fingerprint `9af8c32be9274932eb861ec51721436edea85898f8dca8ab727ad6ee909771a7`. The check fires because `performance_insights_kms_key_id` is unset and RDS uses its AWS managed key. A customer-managed key was not added.

### AWS-0078 Performance Insights encryption

On October 22, 2026 the owner explicitly accepted AWS-managed KMS encryption for Database Insights Standard in staging and production during the PH-first controlled beta. The baseline adds exactly two `accepted_risk` rows. The nineteen earlier exceptions are unchanged. No KMS key was added. The RDS module is unchanged. Database Insights Standard remains enabled. Performance Insights retention is seven days. Data is encrypted with an AWS-managed KMS key. The owner accepts the lack of customer-managed key controls for the beta. Key-management requirements need review before wider production exposure. This is not a Sprint 40 reconciliation and it does not start Sprint 41.

| Environment | Fingerprint |
|---|---|
| staging | `fb297b059e4a46f9e77f937c731e042d1c4697d9e5e1095b8ee94006b79f3c86` |
| production | `9af8c32be9274932eb861ec51721436edea85898f8dca8ab727ad6ee909771a7` |

## uv image pin (2026-10-22)

The dependency stage no longer copies `ghcr.io/astral-sh/uv:latest`. It copies the official Astral image `ghcr.io/astral-sh/uv:0.13.5` by immutable manifest-list digest. The Python base digest is unchanged. `uv.lock`, application dependencies, Alpine, Terraform, and the Trivy baseline are unchanged. This is not a Sprint 40 reconciliation and it does not start Sprint 41.

| Field | Value |
|---|---|
| Version | uv 0.13.5 (`x86_64-unknown-linux-musl` in the linux/amd64 image) |
| Tag | `0.13.5` |
| Registry | `ghcr.io/astral-sh/uv` |
| Source | `https://github.com/astral-sh/uv` |
| GitHub release | `https://github.com/astral-sh/uv/releases/tag/0.13.5`, published 2026-10-22T01:35:54Z, not a prerelease |
| Image revision | `46776a95d6686ac0160c10611327ce491e6b202f` (the release target commit) |
| Index digest | `sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff` |
| linux/amd64 manifest | `sha256:a12ede1e6dc90d3b3e600d0901731e71f0ab0f4d72683ea097b76c19c43cc8df` |
| linux/arm64 manifest | `sha256:d3a8362fee5c061dd78452b5915598fc8fbd15050db3a3d919fba5f2e38c629a` |

Verification on 2026-10-22: an anonymous `ghcr.io` pull token was used. `curl` and a separate Python client both received `Docker-Content-Digest: sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff` for tag `0.13.5`, and that value matched the SHA-256 of the raw OCI index bytes. The index `org.opencontainers.image.version` is `0.13.5`. The index contains a `linux/amd64` manifest. The platform config blob `sha256:2ded3f959e5d71c0de7340c3dba896a4c03ecbc00c24f2720f9a560ec5ec4b1c` is `architecture: amd64`, `os: linux`, entrypoint `/uv`, and the same version and revision labels. The linux/amd64 layer `sha256:7c79a68fb7de557c5181ba22e4558a1efd745dfdcdb341514122d5690616b057` contains `uv` and `uvx`. The extracted `uv` binary prints `uv 0.13.5 (x86_64-unknown-linux-musl)`. At verification time, tag `latest` resolved to the same index digest. The pin uses the version tag plus the index digest.

The official GitHub musl archive `uv-x86_64-unknown-linux-musl.tar.gz` matched release checksum `57ef9d9ccb01fb1bd998df995b0dd221b52f7d7841fbea93f2d4463bf61fb7a9`. The binary inside that archive is not byte-identical to the binary in the GHCR image (archive binary `1981106dde7ff09d000678bbaa0049deee68bd5d3560856f9f112f8d576dc9bc`, image binary `783ddacbd62bce7d3201bd1d0c2287ac3aa63813ce91f97292c83f26d6227a26`). The image binary is a non-PIE static executable. The archive binary is static-PIE. Both report version 0.13.5. The pinned reference is the official GHCR image, identified by the registry digest and OCI labels.

`uv 0.13.5` `lock --check` against the committed `uv.lock` (version 1, revision 5) exited 0 and left the lock bytes unchanged. `uv sync --no-dev --no-install-project` in a copy of `pyproject.toml` and `uv.lock` installed the 31 locked runtime packages and left the lock bytes unchanged. A follow-up `uv sync --no-dev --no-install-project --locked --offline` also succeeded.

The dependency install is now `uv sync --locked --no-dev --no-install-project`. `--locked` fails the build when `uv.lock` would change. `uv.lock` and the application dependencies are unchanged. This is not a Sprint 40 reconciliation and it does not start Sprint 41.
