# Application secret scan — deterministic gate over `app/**/*.py`

**Slice status:** Implemented. Not PROVEN. The secret-scanning capability is IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `57fe37173b2ef94545b7b2bac075dcb7d1a739d6`

This record does not rewrite the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, the security-readiness package, the SAST gate record, or the secret-scan scope correction. It is not named Sprint 40.8. It does not select a later engineering slice. A CI gate is not staging or production proof. No Included requirement is PROVEN.

## Scope

Old `SCAN_GLOBS`:

- `infra/**/*`
- `.env*.example`
- `scripts/**/*`
- `.github/workflows/**/*`

New `SCAN_GLOBS`:

- `infra/**/*`
- `.env*.example`
- `scripts/**/*`
- `.github/workflows/**/*`
- `app/**/*.py`

The previous locations stay in the same scanner. This slice does not replace that scanner with a hosted service. It does not add container vulnerability scanning or IaC security scanning.

Repository exclusions stay `.git`, `.venv`, `.terraform`, `__pycache__`, `node_modules`, and the binary, image, and archive suffixes already skipped. No `app/` directory was added to the exclusion list. The scanner still skips its own source path, `scripts/secret_scan_25a.py`, so pattern text in that file is not a self-match. Other files under `scripts/` stay in scope.

## Detection

The existing high-confidence rules are unchanged:

- `aws_access_key_id`
- `private_key_pem`
- `aws_secret_access_key_assignment`
- `plaintext_password_assignment`
- `forbidden_credential_input_name` for the forbidden Terraform password input names

Application Python adds `python_credential_literal`. The rule calls `ast.parse` only. It does not import application modules and it does not execute the file. It inspects `Assign` and `AnnAssign` targets, plus function, async-function, and lambda parameter defaults. A finding requires both a credential-sensitive identifier and a non-empty string literal.

Identifier matching uses name segments. A segment of `password`, `passwd`, `token`, `secret`, or `credential` matches. Adjacent segments `api` + `key`, `private` + `key`, and `access` + `key` match. Ordinary prose that contains the word token does not match, and an empty literal such as a configuration default of `""` does not match. A non-empty `Field(default="...")` literal on a credential-sensitive name matches. A Python syntax error, an unreadable scanned file, or a parser failure fails the gate. Malformed application Python is not skipped.

## Exception design

`tests/security/baselines/secret-scan.baseline.json` is version 1. `scanner` is `secret_scan_25a`. `scope` is the glob list above. `exceptions` has one object per current finding.

Each exception names one relative path, one rule id, one symbol, one `source_fingerprint`, one rationale, and one reason. There is no wildcard path, wildcard rule, directory exception, module skip, or glob exception. One exception matches one finding. Duplicate copies use multiset comparison: one exception cannot cover two identical findings, and a repeated exception beyond the current count fails.

Allowed rationale values are `safe_demo_constant`, `documented_placeholder`, and `false_positive`. This file is not a Sprint 44 risk acceptance. It records a reviewed scanner exception for a known safe constant or a reviewed false positive. It does not accept a vulnerability.

The fingerprint is a SHA-256 of the rule id, the relative path, the symbol, and a normalized form of the credential-bearing source. For an AST finding, the normalized form is `ast.dump` of the statement or default, with each non-empty string constant replaced by a SHA-256 of that constant and with line numbers omitted. For a regex finding, the matched line is used after the match text is replaced by a SHA-256 of the match. Moving the same statement keeps the fingerprint. Changing the literal or the identifier changes it. The baseline stores the outer fingerprint, not the literal and not the inner hash.

The gate fails closed on an unbaselined finding, a stale exception, a duplicate exception that exceeds the finding count, a wildcard path or rule, a malformed baseline, an unsupported baseline version, an unknown rationale, a path outside the repository, a missing `app/**/*.py` scope, a scanner or parser failure, a Python syntax error in a scanned application file, and an unreadable required file.

## Current finding inventory

The expanded scanner read 809 files. 649 of those are application Python files. It reported 9 findings before review. No application source was changed. Findings after review remain 9. Each one has one exact exception. There is no unresolved blocker. No genuine production credential or private key was found.

Credential-named dict values were reviewed separately and are not findings of this rule. They are redaction markers, export-exclusion descriptions, an anonymous-catalog stage label, and an OAuth scheme label inside a serializer. None is a credential literal assigned to an identifier.

| Rule ID | Path | Symbol | Result |
|---|---|---|---|
| `python_credential_literal` | `app/auth/service.py` | `INVALID_EMAIL_CHANGE_TOKEN` | false positive + `dd79f35163f5375e898506f2871352adcf0e95eccad6bfc4d4f4a360dd4f7af1` |
| `python_credential_literal` | `app/auth/service.py` | `INVALID_RESET_TOKEN` | false positive + `9fd17a14f3e585b0fc5716b690ddbd0041c4564c879540b70ffbf01a66b7095b` |
| `python_credential_literal` | `app/auth/service.py` | `INVALID_VERIFY_TOKEN` | false positive + `099500a7ec0221122a7653a5a0bafc6796b761cf5417edbfcc0c6e74c5a3f9e1` |
| `python_credential_literal` | `app/domain/entities/connector_reliability.py` | `CREDENTIAL` | false positive + `1f3275e95ec94b2457bb6b72edc468a27cecb6e440b52eef7e3420fc42d77a73` |
| `python_credential_literal` | `app/infrastructure/persistence/stores.py` | `PASSWORD_RESETS` | false positive + `6b46a0db79858adf08a8dd55265f4823cc2e7e9e3c5611b8f96666625c5c9c61` |
| `python_credential_literal` | `app/launch/internal_auth.py` | `INTERNAL_LAUNCH_ADMIN_TOKEN` | reviewed safe demo constant + `3a8c7c8abe4a19f3000ca39db29062c9d5452664f89a6c7ed396f238cadb98b2` |
| `python_credential_literal` | `app/schemas/user_platform.py` | `token_type` | false positive + `c3b0af0a4c21897cca4dfc6abccd0313ae9490be26428bf81be8d3054e4769df` |
| `plaintext_password_assignment` | `app/user/fixtures.py` | `DEMO_PASSWORD` | reviewed safe demo constant + `01c384f8501bd9f392d569fdde996826033c4e49daf096c365e7523d8d81b66b` |
| `python_credential_literal` | `app/user/fixtures.py` | `DEMO_PASSWORD` | reviewed safe demo constant + `f81198d6c77a454c70cc906e34bc6680733428ea7a10ef919d49b2732f8f5ffd` |

`DEMO_PASSWORD` produces two findings because the preserved password-assignment regex and the new AST rule both match that one assignment. Each has its own exception. `INTERNAL_LAUNCH_ADMIN_TOKEN` is the published internal demo gate, not a production credential store. Replacing either constant would change product behavior, so both stay in source and are covered by `safe_demo_constant`. Changing the literal changes the fingerprint, so the current exception cannot approve a replacement.

The three `INVALID_*_TOKEN` names are user-facing error text. `CREDENTIAL` is an enum discriminant whose value is the category name. `PASSWORD_RESETS` is a persistence namespace. `token_type` is the OAuth scheme label. Those six use `false_positive`. No exception uses `documented_placeholder`.

| Rationale | Count |
|---|---|
| `safe_demo_constant` | 3 |
| `false_positive` | 6 |
| `documented_placeholder` | 0 |
| Total exceptions | 9 |

## Raw values

Scanner stdout and stderr identify a finding by rule id, relative path, symbol, and source fingerprint. They do not print the literal. The committed baseline does not contain the demo password or the internal demo token. Tests import those constants only to assert their absence from the baseline file and from scanner output.

Current scanner result:

```text
secret_scan_25a: OK
secret_scan_25a: files=809 application_python=649 findings=9 exceptions=9
```

## CI

`.github/workflows/ci.yml` keeps the existing step `Secret scan (deterministic)`:

`uv run python scripts/secret_scan_25a.py`

The step stays before the OpenAPI contract tests and the full pytest gate. It has no `continue-on-error`. Workflow permissions remain `contents: read`. `security-events: write` is not used. The job does not upload source, matches, hashes, or findings. `tests/unit/test_sprint40_application_secret_scan.py` is on the architecture-lock pytest list. No second secret-scanner job was added.

## R6

Before this slice, R6 was PARTIAL. Deterministic secret scanning existed and did not read `app/`. pip-audit was present. SAST over `app/**/*.py` was IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning and IaC security scanning were absent.

After this slice, the secret-scanning capability is IMPLEMENTED-NOT-PROVEN. R6 stays PARTIAL. SAST stays IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning and IaC security scanning remain absent. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. R6 is not PROVEN. Sprint 40 is not ENGINEERING COMPLETE.

The historical MEDIUM `No Dependabot/CodeQL/Trivy/pip-audit` stays CLOSED BY IMPLEMENTATION for the original no-dependency-scanner condition. This record does not broaden that finding. The secret-scan scope change belongs to R6.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- No deploy was performed. No Shopify call was made. Routing stays 0. Real Shopify calls stay 0. Affiliate activation is unchanged. Live research stays off.
- No container scanner, IaC security scanner, prompt isolation, per-session limit, guest revocation, guest-to-account rebind, CAPTCHA, WAF, click-fraud scoring, CSRF token scheme, merchant-host allowlist, or provider activation was added.
- Runtime feature behavior is unchanged.
