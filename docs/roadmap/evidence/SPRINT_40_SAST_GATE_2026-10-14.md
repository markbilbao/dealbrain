# SAST gate — local Bandit baseline

**Slice status:** Implemented. Not PROVEN. The SAST capability is IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `871e761685fe663c4d0ef4cf3b11094c32ed90b9`

This record does not rewrite the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, or the security-readiness package. It is not named Sprint 40.8. It does not select a later engineering slice. A CI gate is not staging or production proof. No Included requirement is PROVEN.

## Scanner

The selected scanner is bandit 1.9.4. PyPI release 1.9.4 requires Python >=3.10, is not yanked, and publishes a `py3-none-any` wheel. This repository requires Python >=3.12. The pin is `bandit==1.9.4` in the `dev` extra and in `uv.lock`. It is not an unpinned `bandit>=` declaration.

Bandit runs in the GitHub Actions job on the checked-out tree. It does not call GitHub Advanced Security or Code Scanning. The workflow does not upload source or findings. Permissions stay `contents: read`. `security-events: write` is not used.

The gate invokes `python -m bandit` from the same interpreter that imports `bandit`. The module version and the CLI version must both be 1.9.4. The command scans `app` recursively, requests JSON, sets severity and confidence to `all`, passes `--ignore-nosec`, and does not pass `--skip`, `--baseline`, `--exit-zero`, or a config file. Cache and generated directories are excluded explicitly: `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, and Bandit's default VCS and egg directories. A `.bandit` file under `app/` fails the gate. Tests, Terraform, and container contents are not in this scan.

## Scope

The scan scope is `app/**/*.py`. The first run scanned 649 Python files under `app/`. That set matched Bandit's metric file list. `.venv`, third-party dependencies, and generated caches were not scanned.

## Current finding inventory

Bandit 1.9.4 reported 35 findings before any change to application code. There were 0 HIGH, 6 MEDIUM, and 29 LOW. No application source was changed. Findings after review remain 35, each with one exact baseline exception. There is no unresolved blocker.

The Result column uses the review label for this record. The baseline `rationale` field is the more specific allowed value: 32 `false_positive`, 2 `safe_constant`, and 1 `framework_managed`. No exception uses a wildcard path, a wildcard test id, a severity ignore, or `# nosec`. Two B101 rows in `app/auth/service.py` share one fingerprint because the same email-change store invariant is written twice. The baseline holds two exceptions. A third copy would be unbaselined, and deleting one copy would make one exception stale.

| Test ID | Path | Severity | Confidence | Result |
|---|---|---|---|---|
| B101 | `app/analytics/service.py` | LOW | HIGH | reviewed false positive + `c625cb258d99d2a1836af9f76808fadd519ea67b5a544dff673de32b1f20700a` |
| B101 | `app/auth/service.py` | LOW | HIGH | reviewed false positive + `02b51bb6a9e3881642f4c9834285b588ddf0f3e74e25c55d29575f87c03b50a6` |
| B101 | `app/auth/service.py` | LOW | HIGH | reviewed false positive + `79de92d7b98367270546f9886b722ad131fe865e53757377ad7d647b5b9bc098` |
| B101 | `app/auth/service.py` | LOW | HIGH | reviewed false positive + `e468161264919cb0747cf5d44fdfd310d35b9598ebe1f904456b41dbaaf791c5` |
| B101 | `app/auth/service.py` | LOW | HIGH | reviewed false positive + `e468161264919cb0747cf5d44fdfd310d35b9598ebe1f904456b41dbaaf791c5` |
| B105 | `app/auth/service.py` | LOW | MEDIUM | reviewed false positive + `0a192a382af2cf366355a99856eb8d5895523304d0f7c07ba7b73379427f53f8` |
| B105 | `app/auth/service.py` | LOW | MEDIUM | reviewed false positive + `1c406772adb09d0f7b146d0c3a2ea911eb9dd371fe87470c1111b898345701c4` |
| B105 | `app/auth/service.py` | LOW | MEDIUM | reviewed false positive + `71f51b374c016ce424423688659ae42d7ce79a86b30abec4265dd3ca9aa2171a` |
| B104 | `app/core/config.py` | MEDIUM | MEDIUM | reviewed false positive + `26edf520ac1d731040ab1dc9507acefc33411957e58a471b2183654ea5c3c0b5` |
| B101 | `app/core/dependencies.py` | LOW | HIGH | reviewed false positive + `56812ddee4936e4a72c736e2444c49ff56661c3b98c7f2c2c86a51d749a9439a` |
| B104 | `app/core/validation.py` | MEDIUM | MEDIUM | reviewed false positive + `a3c838590bb02be02ca514065ae2b47ed214b854da8f8204fd1065f5d3e81c21` |
| B105 | `app/core/validation.py` | LOW | MEDIUM | reviewed false positive + `889a49adbd3d26eae8da2f077733c5ac51b04b5f4b68312d8a306eb9ddf46632` |
| B105 | `app/domain/entities/user_platform.py` | LOW | MEDIUM | reviewed false positive + `644c1127c31845693a71ae0a1692df7e05113cc8283242766ff80960209655ba` |
| B101 | `app/infrastructure/database/repositories/price_history_repository.py` | LOW | HIGH | reviewed false positive + `7fed9f58878f71bc0b56b7d273c397c56df1a4ae628df783d45bad293bc9c009` |
| B101 | `app/infrastructure/database/repositories/price_history_repository.py` | LOW | HIGH | reviewed false positive + `b8cac90b55e259e60517ed839dbef5dd4cbe9fd5e38dba2680343a27dde12604` |
| B101 | `app/infrastructure/persistence/codec.py` | LOW | HIGH | reviewed false positive + `1af4c8f932038aea343097096cdbcecc0f16d772a3fe91ee6ec3adf8cd6f7fc9` |
| B105 | `app/infrastructure/persistence/stores.py` | LOW | MEDIUM | reviewed false positive + `c48a018ba3c5f89f0e54c50fbc0f98a646d90a6057a9b1d856cc99387a54f922` |
| B112 | `app/intelligence/community/collector.py` | LOW | HIGH | reviewed false positive + `f2fe6187d4ded02b8dfadfe8b8a126efeaffb1a9f227b6539161b9e5db06a489` |
| B101 | `app/intelligence/personal/fixtures.py` | LOW | HIGH | reviewed false positive + `d7bb37529e0d7cd8d5bbc2bc74180660c3b5df68abe8e4d14c7c98f88c512ff6` |
| B112 | `app/intelligence/shopping_assistant/orchestrator.py` | LOW | HIGH | reviewed false positive + `d01235e039ad590900becefeef909d0f840953cd86d39c22a526e372c035d94a` |
| B105 | `app/launch/internal_auth.py` | LOW | MEDIUM | reviewed false positive + `bdee2cd56f6b5b2c58ec6cef1e03e88298e52e172608fef5898bbcb02cce0457` |
| B101 | `app/merchant/security/validation.py` | LOW | HIGH | reviewed false positive + `231ae75e0be03ef5dd4719119ebf121c4ca9b45a3c2a53b425c7d47b38f0aaff` |
| B105 | `app/privacy/inventory.py` | LOW | MEDIUM | reviewed false positive + `384000e727f662802022bc309ad53f804cc529a29f2d68886972c8dc0511ec3f` |
| B105 | `app/privacy/inventory.py` | LOW | MEDIUM | reviewed false positive + `873dc6dd628390fd7eaaba3367abd3a0e3f1534b4301486a3c350dbc391dac10` |
| B108 | `app/research/public_web_extract.py` | MEDIUM | MEDIUM | reviewed false positive + `0a13ea00642ff38e01415ead5efb02301ef4240c7e0878704a6e41f2d8b98ce0` |
| B108 | `app/research/public_web_extract.py` | MEDIUM | MEDIUM | reviewed false positive + `7e3cd5b7f90dfb6afb5a98f622d0ac3b7587357957506212586f1d4e60d2f8c1` |
| B101 | `app/research/shopify_global_catalog_execution.py` | LOW | HIGH | reviewed false positive + `0d26b29b00c4b22777862304c10931f2da3c940e209b0accae56f1e4c8e7b8c3` |
| B101 | `app/research/shopify_global_catalog_execution.py` | LOW | HIGH | reviewed false positive + `faebc5d12af720643cac313aeb81b017aba5bf704b54103723bde497b4206261` |
| B108 | `app/research/shopify_global_catalog_ph_probe.py` | MEDIUM | MEDIUM | reviewed false positive + `5dbed22dc35365a26e5af6d3ddb1781096b65075f9c1ac2d5766e990de1dea02` |
| B110 | `app/services/deal_recommendation_service.py` | LOW | HIGH | reviewed false positive + `35a38ab9f76d28488e0365f3bae4eacf26093b668edc215a0f3dd187026a8660` |
| B112 | `app/services/knowledge_graph_service.py` | LOW | HIGH | reviewed false positive + `f2fe6187d4ded02b8dfadfe8b8a126efeaffb1a9f227b6539161b9e5db06a489` |
| B101 | `app/services/marketplace_data_service.py` | LOW | HIGH | reviewed false positive + `d854f3c4063bda7344d12e1197613325fc4e098c803a6f13d8777f5df8fd0a67` |
| B101 | `app/services/price_history_service.py` | LOW | HIGH | reviewed false positive + `e8219ab42961a8a1da6966836833c8403af66ebb4ac50d52a908f098b9f5314f` |
| B104 | `app/ucp/agent_profile.py` | MEDIUM | MEDIUM | reviewed false positive + `d8296968beb58e8a879385de89f8640d7c680790fb0a2d618874fb11a54fd262` |
| B105 | `app/user/fixtures.py` | LOW | MEDIUM | reviewed false positive + `c54d0263577a78fafb7b9e82018cd4c87ae24768f04e6a7d7b5ed15f3090f18f` |

### Reviewed MEDIUM results

| Path | Test ID | Baseline rationale | Why it is not a vulnerability here |
|---|---|---|---|
| `app/core/config.py` | B104 | `framework_managed` | The string is the settings default for the container listen address. This line does not open a socket. The image command binds that address so the container can receive traffic from the ALB. |
| `app/core/validation.py` | B104 | `false_positive` | The string is one entry in the production database-host denylist. It is not a bind. |
| `app/ucp/agent_profile.py` | B104 | `false_positive` | The string is a marker used to detect internal addresses in profile text. It is not a bind. |
| `app/research/public_web_extract.py` | B108 | `false_positive` | Two documented private local artifact paths. Tests require them to stay outside the repository. They are not request-path temporary files. |
| `app/research/shopify_global_catalog_ph_probe.py` | B108 | `false_positive` | The same private local artifact directory pattern for the catalog probe. It is not a request-path temporary file. |

### Reviewed LOW constants

`app/launch/internal_auth.py` B105 uses rationale `safe_constant`. The value is the published launch-readiness demo gate string. It is not a production credential store. Replacing that gate is an authentication change with its own tests and is outside this scanner slice. Changing the string changes the fingerprint, so the current exception cannot approve a replacement.

`app/user/fixtures.py` B105 uses rationale `safe_constant`. The value is the published in-memory demo password. Production forbids seeding demo users and forbids the memory user-platform backend. The baseline does not copy the value.

The other LOW results are asserts that narrow an invariant already enforced by the surrounding code, user-facing text whose name contains "token", a redaction placeholder, an OAuth scheme label, a schema identifier, or an optional provider failure that does not authorize a request. None is an authorization bypass.

## Baseline policy

`tests/security/baselines/bandit.baseline.json` is version 1. `scanner` is `bandit`. `scanner_version` is `1.9.4`. `scope` is `app/**/*.py`. `exceptions` has 35 objects.

Each exception names one relative path, one `B###` test id, one severity, one confidence, and one SHA-256. The hash covers the normalized source of Bandit's `line_range`, with line-number prefixes removed, plus Bandit's `issue_text` so two findings in one AST node stay distinct. The hash does not include the line number. Moving the same source keeps the exception. Changing the source makes the old exception stale and the new finding unbaselined. One exception matches one finding. The file stores the hash, not the source snippet.

Allowed `rationale` values are `false_positive`, `safe_constant`, `test_only_behavior`, and `framework_managed`. Each exception also has a one-line `reason`. This file is not a Sprint 44 risk acceptance. No finding is PROVEN from CI alone.

## Fail-closed conditions

The gate exits 2 when it cannot finish, and exits 1 when the comparison does not match. Finish failures include:

- scanner exit other than 0 or 1
- timeout
- invalid JSON, a non-object payload, or a missing `results`, `errors`, `metrics`, or `generated_at` field
- a scan error, a `# nosec` count, or skipped Bandit tests
- result totals that do not match the metric counters
- a scanned file set that is not exactly `app/**/*.py`
- a missing source snippet or a snippet that does not cover `line_range`
- installed Bandit version other than 1.9.4
- missing, malformed, wrong-version, wrong-scope, or wildcard baseline
- an unbaselined current finding
- a stale baseline exception

Exit 1 from Bandit means findings were found. The gate reads the JSON and does not treat that exit as a crash. Output names the path, test id, severity, confidence, and hash. It does not print source snippets.

## CI integration

`.github/workflows/ci.yml` job `Lint, contracts, and pytest` runs this step after the pip-audit gate and before the OpenAPI contract tests:

`uv run python scripts/check_sast_baseline.py`

The step name is `SAST (Bandit baseline gate)`. It has no `continue-on-error` and no `if`. `tests/unit/test_sprint40_sast_baseline.py` is on the architecture-lock pytest list. Workflow permissions remain `contents: read`.

## Dependency and lockfile

`pyproject.toml` dev extra gained `bandit==1.9.4`. `uv.lock` added bandit 1.9.4 and stevedore 5.9.1. Existing pins were not loosened. The production image still installs with `uv sync --no-dev`, so Bandit is not in the runtime image.

pip-audit 2.10.1 against the updated frozen dev closure reported 73 packages, 0 vulnerabilities, 0 exceptions. The previous closure was 71 packages. The two added distributions are bandit and stevedore. No advisory was bypassed.

## R6

Before this slice, R6 was PARTIAL. Secret scanning and pip-audit were present. SAST, container vulnerability scanning, and IaC security scanning were absent.

After this slice, R6 stays PARTIAL. SAST over `app/**/*.py` is IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning and IaC security scanning are still absent. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. R6 is not complete. Sprint 40 is not ENGINEERING COMPLETE.

The historical MEDIUM `No Dependabot/CodeQL/Trivy/pip-audit` stays CLOSED BY IMPLEMENTATION for the original no-dependency-scanner condition. This record does not rewrite it into a SAST finding. The new SAST capability belongs to R6.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- No deploy was performed. No Shopify call was made. Routing stays 0. Real Shopify calls stay 0. Affiliate activation is unchanged. Live research stays off.
- No container vulnerability scanning, IaC security scanning, Dependabot, hosted code scanning, prompt isolation, rate-limit redesign, guest revocation, CAPTCHA, WAF, CSRF token scheme, or provider activation was added.
