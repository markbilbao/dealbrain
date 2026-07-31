# Sprint 25b.1 — Immutable Image Publication and Release Manifest

**Status:** Implemented as repository workflow + tooling (no live GHCR publish claimed by this document)  
**Branch:** `sprint-25b`  
**Contracts:** [SPRINT_25_PRODUCTION_INFRASTRUCTURE.md](architecture/SPRINT_25_PRODUCTION_INFRASTRUCTURE.md) §8; Sprint 25b architecture design (phase 25b.1)  
**Note:** `docs/architecture/SPRINT_25B_RELEASE_PIPELINE.md` was designed in the Sprint 25b architecture pass but was not present in the repository at implementation time. This document records the 25b.1 slice that was implemented.

## Objective

Create the **build-once** foundation for later staging and production promotion:

1. Build the production image after approved `main` changes
2. Publish to GHCR with an immutable commit tag
3. Capture and verify the image digest
4. Generate a checksummed release manifest artifact
5. Treat digests (not mutable tags) as deployment authority

This phase does **not** deploy to AWS, add OIDC/SSM, or create staging/production deploy workflows.

## Image naming and tagging

| Item | Value |
|------|-------|
| Registry / repository | `ghcr.io/<owner>/<repo>` (lowercase) |
| Immutable tag | `sha-<full_git_sha>` (40-char SHA) |
| Deployment authority | Digest `sha256:<64 lowercase hex>` |
| OCI labels | `org.opencontainers.image.source`, `.revision`, `.created`, `.version` |

### Mutable tag policy

- Mutable tags such as `latest`, `ci-latest`, branch names, or env aliases are **not** deployment authority.
- Sprint 25b.1 publishes **only** the immutable `sha-<full_git_sha>` tag.
- Later phases may update human convenience pointers **after** a successful deploy; deploy jobs must still pull by digest.

## Digest authority

1. `docker/build-push-action` pushes the image and emits `digest`
2. The workflow validates `^sha256:[0-9a-f]{64}$`
3. `docker buildx imagetools inspect <repo>@<digest>` confirms the digest exists in GHCR
4. The release manifest stores `image_repository` + `image_digest` + `image_tag_sha`
5. Future staging/production workflows must consume `@sha256:…` and must **not** rebuild

## Build workflow trigger

Workflow: [`.github/workflows/build-image.yml`](../.github/workflows/build-image.yml)

| Trigger | Behavior |
|---------|----------|
| `workflow_run` of **CI** (`completed`) on `main` | Runs only when CI conclusion is `success` and the triggering event was a `push` to `main` |
| `workflow_dispatch` on `main` | Allowed for controlled reruns; requires an explicit GitHub API check that CI for the same SHA already succeeded |

Fork repositories never publish (`github.event.repository.fork == false`).

### CI-green requirement (chosen mechanism)

**Approach A** for the automatic path: `workflow_run` after successful CI on `main` — avoids racing a simultaneous push-triggered CI job.

**Approach B** for manual dispatch: `gh run list --workflow ci.yml --commit <sha>` must find a successful completed run before publish.

The manifest records `test_workflow_run_id` (CI) and `build_workflow_run_id` (this workflow).

### Concurrency

Group: `release-build-<git-sha>` with `cancel-in-progress: false` so duplicate builds for the same commit do not race and publication is not cancelled mid-push.

### Permissions

- `contents: read`
- `packages: write`
- `actions: read` (required to resolve CI run evidence on `workflow_dispatch`)

No AWS credentials. No application production secrets. No `id-token` in this phase.

## Release manifest lifecycle

| Stage | `final_status` | `environment` | Notes |
|-------|----------------|---------------|-------|
| Image built + published | `built` | `none` | Sprint 25b.1 end state |
| Staging verified | `staging_ok` | `staging` | Deferred (25b.3) |
| Prod approved | `approved` | `production` | Deferred (25b.4) |
| Prod deployed | `production_ok` | `production` | Deferred (25b.4) |
| Failure / rollback | `failed` / `rolled_back` | varies | Deferred (25b.5) |

### Schema and tooling

| Path | Role |
|------|------|
| `schemas/release-manifest.schema.json` | Binding JSON Schema loaded by runtime validation |
| `scripts/release/manifest.py` | Schema + semantic validate, create, deterministic checksum |
| `scripts/release/create_release_manifest.py` | CLI used by the build workflow |
| `scripts/release/validate_release_manifest.py` | CLI: JSON Schema + semantic + checksum integrity |

### Validation flow

1. Reject secret-like field names and mutable-tag authority markers
2. Validate against `schemas/release-manifest.schema.json` via `jsonschema` (Draft 2020-12)
3. Apply semantic checks (git SHA ↔ `image_tag_sha`, built-state invariants, run IDs, …)
4. Recompute and verify `manifest_sha256`

### Checksum model

1. Canonicalize JSON with `sort_keys=True`, compact separators, `manifest_sha256` set to `null`
2. Compute SHA-256 hex of that UTF-8 payload
3. Write `manifest_sha256` on the final object
4. Validator recomputes the same canonical payload and rejects mismatches

Secret-like field names (`password`, `token`, `database_url`, …) are rejected.

## Artifact and retention

| Artifact | Contents | Retention |
|----------|----------|-----------|
| `release-manifest-<release_id>` | `release-manifest.json` + `release-manifest.json.sha256` | **90 days** |

Workflow job summary includes release ID, git SHA, immutable tag, digest, manifest checksum, and build/test run IDs.

No GitHub Release object is created in 25b.1.

## Relationship to CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) continues to:

- lint (Ruff **baseline** gate), secret scan, contracts, architecture tests, full pytest
- Terraform fmt/validate
- Compose config validation
- Docker **build without push** (PR and branch validation)

CI **no longer** publishes GHCR images. Releasable publication is owned only by `build-image.yml`.

## Manual reruns and superseded builds

- Prefer `workflow_dispatch` on `main` with the target SHA after CI is green
- Re-running publish for the same SHA overwrites the mutable registry tag pointer for `sha-<sha>` only if the digest changes (content-addressed digest remains the authority)
- A newer `main` commit produces a new release ID and digest; older manifests remain as artifacts until retention expiry
- Superseded digests are not deleted by this workflow

## Failure handling

| Failure | Behavior |
|---------|----------|
| CI not green | `workflow_run` does not publish; dispatch exits before build |
| Digest format invalid | Job fails after push attempt; investigate Buildx output |
| Digest missing from GHCR | `imagetools inspect` fails the job |
| Manifest validation fails | Artifact is not uploaded (`if-no-files-found: error` on upload) |
| Fork / non-main | Job `if` skips publication |

## Deferred — Sprint 25b.2–25b.5

| Phase | Focus |
|-------|-------|
| **25b.2** | Terraform GitHub OIDC provider, staging/production deploy IAM roles |
| **25b.3** | Staging deploy via SSM, host `DATABASE_URL` assembly, migrate + verify |
| **25b.4** | Production GitHub Environment approval, same-digest promotion |
| **25b.5** | Rollback workflow, extended release-evidence validation |

Also deferred: S3 evidence bucket, live AWS verification, production dry run, traffic cutover, backup restore drills (25d).

## Local validation

```bash
# Manifest tooling
uv run python scripts/release/create_release_manifest.py \
  --git-sha 0123456789abcdef0123456789abcdef01234567 \
  --image-repository ghcr.io/example-org/dealbrain \
  --image-digest sha256:$(printf 'a%.0s' {1..64}) \
  --build-workflow-run-id 1 \
  --test-workflow-run-id 2 \
  --created-at 2026-07-31T12:00:00Z \
  --output /tmp/release-manifest.json

uv run python scripts/release/validate_release_manifest.py /tmp/release-manifest.json

# Tests
uv run pytest tests/unit/test_sprint25b1_image_publication.py tests/unit/test_sprint25a_infrastructure.py -q
```

A successful local run of these commands does **not** mean an image was published to GHCR. Publication occurs only when `build-image.yml` executes on GitHub Actions against `main`.

## Architecture locks

Sprint 25b.1 does not modify DealScore, Recommendation, Marketplace ranking, Shopping Assistant ranking, Personal AI, affiliate/merchant neutrality, Sprint 22 probe semantics, Sprint 23 adapters/schema, Sprint 24 API contracts, Sprint 25a Terraform isolation, RDS secret model, or Compose `api`/`migrate` ownership. No `/api/v2`.
