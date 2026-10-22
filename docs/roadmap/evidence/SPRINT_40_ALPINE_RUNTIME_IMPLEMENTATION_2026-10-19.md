# Committed Alpine runtime (2026-10-19)

The owner approved the glibc to musl move and the exact reviewed exception set. This note records the committed Dockerfile. Earlier notes describe temporary candidates and are not rewritten.

The image tag built from this Dockerfile is `dealbrain:ci-local`. It is not a published GHCR image. No deploy was performed.

## Dockerfile

`FROM python:3.12-alpine3.24`. That official tag resolved to Alpine 3.24.2 and image digest `sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4`, the same supported family as the temporary `python:3.12-alpine` experiments.

`uv` and `uvx` are copied from `ghcr.io/astral-sh/uv:latest` only in the dependency stage. That stage runs `uv sync --no-dev --no-install-project`. The runtime stage does not copy `/bin/uv` or `/bin/uvx`.

The runtime stage runs `apk upgrade --no-cache zlib` and deletes the global pip paths. It does not upgrade the rest of Alpine. The non-root user, production environment, PATH, copied application and Alembic files, healthcheck, and uvicorn command are unchanged. Dependencies in `uv.lock` are unchanged.

## Built image

| Item | Value |
|---|---|
| Image id | `sha256:d88c38e892f96b5dc1d3fe8adde96bf1f438591725cb7069ecb4deff01b45b39` |
| Image size | 62,848,237 bytes |
| Python | 3.12.15 (main, Oct 1 2026, 21:45:39) |
| Alpine | 3.24.2 |
| zlib | 1.3.2-r1 |
| busybox, busybox-binsh, ssl_client | 1.37.0-r31 |
| Process user | uid 100, gid 101, name dealbrain |
| `/bin/uv` | absent |
| `/bin/uvx` | absent |
| global pip binaries | absent |
| `python -m pip` | unavailable |
| `/app/.venv/bin/uvicorn` | present |
| `/app/.venv/bin/alembic` | present |

`uv sync` installed 31 locked packages from downloaded wheels. Native distributions and tags, with no `direct_url.json`:

| Package | Tag |
|---|---|
| asyncpg 0.31.0 | `cp312-cp312-musllinux_1_2_x86_64` |
| psycopg-binary 3.3.4 | `cp312-cp312-musllinux_1_2_x86_64` |
| uvloop 0.22.1 | `cp312-cp312-musllinux_1_2_x86_64` |
| greenlet 3.5.4 | `cp312-cp312-musllinux_1_2_x86_64` |
| pydantic-core 2.46.4 | `cp312-cp312-musllinux_1_1_x86_64` |

No package in that set was compiled from source during the build.

## Grype before exceptions

Grype 0.120.1 scanned `dealbrain:ci-local` from the local Docker daemon with `scripts/security/grype.yaml` before the baseline was loaded. The database schema is `v6.1.10`, built `2026-10-19T06:39:15Z`. Gathered packages: 70. Findings: 10. Critical 0, High 0, Medium 9, Low 0, Negligible 1.

Every finding identity matched the reviewed proposal: vulnerability id, package, version, type, PURL, severity, fix state, fixed versions, and fingerprint. The empty BusyBox fix state normalized to `unknown`. No new Medium appeared. The approved objects were then copied into `tests/security/baselines/grype-image.baseline.json`.

## Gate after the load

```
container_vuln_gate: OK
scanner=grype
scanner_version=0.120.1
target=docker:dealbrain:ci-local
packages=70
findings=10
exceptions=10
critical=0
high=0
medium=9
low=0
negligible=1
db_built=2026-10-19T06:39:15Z
db_schema=v6.1.10
db_checksum=sha256:13a192236b248579678bbf06cefb2a07a5dcbd00da110cfb5c3e26eb68a7ce58
```

The ten loaded exceptions are GRYPE-001 through GRYPE-010. GRYPE-001, GRYPE-002, and GRYPE-003 are CVE-2025-60876 on busybox, busybox-binsh, and ssl_client, rationale `not_applicable`. GRYPE-004 through GRYPE-009 are the reviewed Python Medium rows, rationale `not_applicable`. GRYPE-010 is CVE-2026-3479, rationale `false_positive`. Fingerprints are the values in the baseline file. No wildcard and no accepted-risk rationale.

## Runtime

Imports succeeded for urllib, httpx, asyncpg, psycopg, uvicorn, SQLAlchemy, Alembic, `app.main`, and `app.auth.email_resend`. `alembic --version` is 1.18.5. Against PostgreSQL 16 on `127.0.0.1:5433`, `alembic current` and `alembic upgrade head` report `a7b8c9d0e1f2 (head)`.

The image's production environment, with no secrets, exits 3. The error is `ConfigurationValidationError` and names `APP_SECRET_KEY`. Uvicorn does not stay up.

Development startup with `APP_ENV=development` and `APP_DEBUG=true` logs `startup_validation ok environment=development`. `GET /live` returned 200. `GET /ready` returned 503 with `"ready": false` and `"database": "down"` when PostgreSQL was absent. Docker health status became `healthy`. The healthcheck command inside the container succeeded. `docker stop` logged `Shutting down`, `Application shutdown complete`, `Database connections closed`, and `Shutting down PiqSavi`.

A second development process, pointed at the migrated database, returned `GET /live` 200 and `GET /ready` 200 with `"ready": true` and `"database": "up"`.

## Tests

Host pytest: 4577 passed, 5 skipped. Ruff baseline, secret scan, pip-audit, and Bandit SAST gates passed. Compose production and staging config passed. Terraform 1.15.8 `fmt -check` and `validate` passed for account, staging, and production. Provider lockfiles were not changed.

## Status

GitHub CI run https://github.com/markbilbao/dealbrain/actions/runs/39221691578 on `b2b2e9150c6408224b9dabcdfe8ebced1b821cf3` succeeded. Lint, contracts, pytest, Compose, Terraform, and the image job passed. The image job printed `container_vuln_gate: OK` with critical 0 and high 0. Container vulnerability scanning is IMPLEMENTED-NOT-PROVEN. This is not production proof. R6 stays PARTIAL because IaC security scanning is absent. Sprint 40 stays Planned and is not ENGINEERING COMPLETE. No image was published and no deploy was performed.

## Pinned base (2026-10-22)

This section does not rewrite the 2026-10-19 build above. The Dockerfile base is now the same tag with an immutable digest:

`python:3.12-alpine3.24@sha256:92abd2ba1bdfb48b1e2ac224b582dd1558d0d4bb11c903b126b5bf9c448fd656`

That digest is the official manifest list from `registry-1.docker.io` for `library/python:3.12-alpine3.24`, verified on 2026-10-22. The linux/amd64 manifest is `sha256:9b98a8d37794ca093ba8d5afe1ffac52f5a15168b9b4e67594d86c20e14fa681`. The image reports CPython 3.12.15 and Alpine 3.24.3. Python and Alpine stay in the 3.12 and 3.24 families. `uv.lock` changes only `certifi` from 2026.7.22 to 2026.10.19. The three CVE-2025-60876 exceptions keep the same vulnerability, packages, version `1.37.0-r31`, and rationale. Their PURLs now say `alpine-3.24.3`. No image was published and no deploy was performed.
