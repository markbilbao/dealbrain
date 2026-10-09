# Sprint 40.2 — Dependency audit baseline

**Slice status:** Implemented. Not PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `ed666678691522238eb44c395a3bc5273f36fa4b`

This record does not rewrite [`SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md`](SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md) or [`SPRINT_40_1_BODY_IDENTITY_IMPLEMENTATION_2026-10-09.md`](SPRINT_40_1_BODY_IDENTITY_IMPLEMENTATION_2026-10-09.md). The audit matrix classes stay as recorded there. No Included requirement is PROVEN. A CI gate and a lockfile upgrade are not staging or production proof.

## Scanner

The selected scanner is **pip-audit 2.10.1**, pinned in the `dev` extra and in `uv.lock`.

The repository installs with `uv sync` from `pyproject.toml` and `uv.lock`. CI already runs `uv sync --extra dev`. The production image runs `uv sync --no-dev`. pip-audit does not read `uv.lock`. The gate exports that lock with `uv export --frozen --extra dev --no-emit-project`, strips environment markers, and runs `pip-audit --no-deps --disable-pip --strict --vulnerability-service osv`. `--no-deps` audits the locked versions and does not resolve a different tree. Marker stripping keeps Windows-only pins in the Linux CI audit. The OSV service is explicit because that is the database that returned the advisory below. The PyPI advisory service is not the gate.

`uv audit` on uv 0.12.24 reports the same Mako advisory, and it also warns that the command and its JSON schema are experimental and may change without warning. That preview surface is not the required gate. Dependabot opens update pull requests and does not fail this CI workflow. CodeQL is SAST, not the lockfile advisory check this slice is for. Trivy is a larger filesystem and image scanner and would pull in findings outside the locked Python closure.

The gate does not take production credentials and does not deploy. Workflow permissions stay `contents: read`.

## Baseline result

Pre-fix audit of the locked closure, pip-audit 2.10.1 against OSV, found one advisory.

| Package | Locked version | Class | Advisory | Alias | Severity | Fix available |
|---------|----------------|-------|----------|-------|----------|---------------|
| mako | 1.3.12 | transitive, via direct runtime dependency alembic | CVE-2026-102991 | GHSA-5639-2j2p-m4mx | GitHub advisory severity MODERATE. CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:L/A:N. pip-audit 2.10.1 JSON did not include a severity field. | 1.4.2 |

Mako is not declared in `pyproject.toml`. Alembic 1.18.5 depends on Mako with no upper bound. The issue is a Windows `TemplateLookup` path traversal when a template URI contains a drive letter. It is fixed in Mako 1.4.2. Mako 1.4.0 was yanked. Mako 1.4.3 is the current release, requires Python >=3.10, and keeps the 1.4.2 fix. This project requires Python >=3.12. The locked MarkupSafe 3.0.3 already satisfies Mako 1.4's MarkupSafe >=2 floor, and that pin did not change.

`uv.lock` now pins mako 1.4.3. No application code changed for the upgrade. The post-fix audit of all 71 locked third-party distributions, including the dev extra and the pip-audit install itself, reported no known vulnerabilities.

`tests/security/baselines/pip-audit.baseline.json` records `exceptions: []`. An empty allowlist is not an ignore-all. Any advisory fails the gate until a hand-written exception names one package, one locked version, and one advisory id. The checker rejects wildcard package names, versions, and advisory ids. It does not pass `--ignore-vuln`. A baselined advisory does not carry forward to a different version. A stale exception fails the gate.

## CI behavior

`.github/workflows/ci.yml` job `Lint, contracts, and pytest` runs, after the existing secret scan and before the contract tests:

`uv run python scripts/check_pip_audit_baseline.py`

The step has no `continue-on-error` and no `if`. Exit 0 means the export matches `uv.lock`, pip-audit 2.10.1 finished, every locked distribution was reported, and every advisory is absent or listed as one version-scoped exception. Exit 1 means an unbaselined advisory or a stale exception. Exit 2 means export, version pin, skipped package, or advisory-service failure. Any non-zero exit fails the job.

These existing gates stay in the same workflow: Ruff baseline, deterministic secret scan, OpenAPI contract tests, protected-module and architecture-lock tests, full pytest, Terraform fmt and validate, Docker Compose config, and the Docker image build that does not publish. `tests/unit/test_sprint40_2_dependency_audit.py` is on the architecture-lock pytest list and asserts the pip-audit step is present. `tests/unit/test_sprint25a_infrastructure.py` also requires that step and that test module to stay in `ci.yml`.

## What this changes in the finding map

The Sprint 30 MEDIUM row "No Dependabot/CodeQL/Trivy/pip-audit" stays in section I of the gap inventory as the historical map. It is no longer an open absence: CI now requires this pip-audit gate on the locked Python closure. Dependabot, CodeQL, and Trivy are still absent. This slice does not add SAST or image scanning. R6 stays PARTIAL. CSRF not enforced, CSP `'unsafe-inline'`, and incomplete URL validation / SSRF hardening remain the existing MEDIUMs. They are not relabeled launch-blocking. No risk acceptance is recorded.

The open Sprint 40 HIGH remains in-process rate limits only.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0.
- Affiliate behavior was not changed.
- Distributed rate limiting, account lockout, CSP, CSRF, SSRF / URL validation, and body-identity authorization were not changed.

Out of scope and not implemented here: Dependabot, CodeQL, Trivy, container scanning, a distributed limiter, account lockout, CSP changes, CSRF middleware, SSRF / URL-validation changes, pen-test documents, Sprint 41 production work, Sprint 42 paging, Sprint 38 changes, and Sprint 39 changes.
