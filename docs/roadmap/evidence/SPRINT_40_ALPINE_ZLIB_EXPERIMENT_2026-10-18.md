# Alpine zlib remediation experiment (2026-10-18)

This note records a temporary image. It does not change the committed `Dockerfile`, add a vulnerability exception, accept risk, publish an image, or deploy. The Grype pin, checksum, database policy, local Docker source, baseline behavior, and scan-before-push order are unchanged.

The temporary Dockerfile was `/tmp/cve-candidates/Dockerfile.alpine-zlib`. It is the existing Alpine measurement image plus one package command. The dependency layer was reused from that measurement, so the Python environment is the same locked set.

## Package change

Base: `python:3.12-alpine`, Alpine 3.24.2.

Command, run as root before the `dealbrain` user is created:

```
apk upgrade --no-cache zlib
```

Build output:

```
(1/1) Upgrading zlib (1.3.2-r0 -> 1.3.2-r1)
OK: 13.5 MiB in 38 packages
```

`apk info -v` differs by one line: `zlib-1.3.2-r0` becomes `zlib-1.3.2-r1`. Installed files are `usr/lib/libz.so.1` and `usr/lib/libz.so.1.3.2`. No other Alpine package changed.

Image size: unpatched Alpine 81,767,283 bytes; patched Alpine 81,862,368 bytes. The Debian 13 control image is 103,823,873 bytes.

## Grype

Scanner: Grype 0.120.1. Database: schema `v6.1.10`, built `2026-10-16T06:29:51Z`, the same snapshot as the 2026-10-17 comparison. The experimental scan held that snapshot (`auto-update: false` only in `/tmp/cve-candidates/grype.same-db.yaml`). `scripts/security/grype.yaml` is unchanged and still updates the database on CI runs.

Package catalog: 1133 before and after (CycloneDX library plus application components).

| Image | Matches | Critical | High | Medium | Low | Negligible |
|---|---:|---:|---:|---:|---:|---:|
| Alpine 3.24.2, zlib 1.3.2-r0 | 17 | 0 | 1 | 14 | 1 | 1 |
| Alpine 3.24.2, zlib 1.3.2-r1 | 16 | 0 | 0 | 14 | 1 | 1 |

The only match that disappeared is `CVE-2026-85091` on `zlib` `1.3.2-r0`. Nothing was added. Critical is 0. High is 0. No HIGH finding was baselined.

Remaining matches are Medium, Low, or Negligible: Python 3.12.15 NVD CPE matches, busybox `CVE-2025-60876` on three busybox packages, and six pip 25.0.1 advisories (five Medium, one Low).

## Native wheels

`uv sync` was a cache hit from the prior Alpine build. None of these distributions has `direct_url.json`. Each wheel tag is a prebuilt musl wheel:

| Package | Distribution | Wheel tag |
|---|---|---|
| asyncpg | asyncpg 0.31.0 | `cp312-cp312-musllinux_1_2_x86_64` |
| psycopg-binary | psycopg_binary 3.3.4 | `cp312-cp312-musllinux_1_2_x86_64` |
| uvloop | uvloop 0.22.1 | `cp312-cp312-musllinux_1_2_x86_64` |
| greenlet | greenlet 3.5.4 | `cp312-cp312-musllinux_1_2_x86_64` |
| pydantic-core | pydantic_core 2.46.4 | `cp312-cp312-musllinux_1_1_x86_64` |

The extension filenames end in `cpython-312-x86_64-linux-musl.so`. No package in this set was compiled from source during the image build.

## Runtime checks inside the patched image

The default process user is `uid=100(dealbrain) gid=101(dealbrain)`. `python` is 3.12.15. `urllib.request` imports. These imports succeed: `httpx`, `asyncpg`, `psycopg`, `uvicorn`, `sqlalchemy`, `alembic`, `app.main`, `app.auth.email_resend`.

`alembic --version` prints `alembic 1.18.5`. Alembic loads `alembic.ini`, script location `alembic`, head `a7b8c9d0e1f2`, 7 revisions.

With the image's production environment and no secrets, `run_startup_validation()` raises `ConfigurationValidationError`. The message names `APP_SECRET_KEY`, `RESEND_API_KEY`, `DATABASE_URL`, `TRANSACTIONAL_EMAIL_PROVIDER`, `TRANSACTIONAL_EMAIL_FROM`, `PUBLIC_APP_BASE_URL`, `LAUNCH_STRICT_STARTUP`, and `LAUNCH_ADMIN_TOKEN`. Starting the default command exits 3 during startup. Uvicorn does not report that it is running, and `/live` is not served.

With `APP_ENV=development` and `APP_DEBUG=true`, startup validation logs `startup_validation ok environment=development`. `GET /live` returns 200 and `{"live": true}`. `GET /docs` returns 200. `GET /openapi.json` returns 200 with 210 paths, including `/live`, `/ready`, and `/health`. `GET /ready` returns 503 with `"ready": false` and `"database": "down"` when PostgreSQL is absent. Docker's recorded health status for that container was `healthy`. `docker exec` of the image healthcheck command succeeded. `docker stop` produced `Shutting down`, `Application shutdown complete`, `Database connections closed`, and `Shutting down PiqSavi`. A later start served `/live` 200 again. The running process remained uid 100.

`alembic upgrade head` with `DATABASE_URL` pointed at PostgreSQL 16.15 applied all seven revisions through `a7b8c9d0e1f2` and created `alembic_version`, `products`, `canonical_products`, `canonical_product_relations`, `price_snapshots`, `operational_entities`, `rate_limit_counters`, `failed_login_locks`, and `shopping_assistant_submissions`. The same image, still uid 100, then served `GET /live` 200 and `GET /ready` 200 with `"ready": true` and `"database": "up"`.

Compose still expects `uvicorn` as the API command and `["alembic", "upgrade", "head"]` for the migrate service. Both executables are on `PATH` (`/app/.venv/bin/uvicorn`, `/app/.venv/bin/alembic`), and the migrate command completed against PostgreSQL. This environment dropped packets between user-defined bridge containers, so the database was reached on a host-published port. That is an environment constraint, not a change to the Compose command.

## Runtime tools

`/bin/uv`, `/bin/uvx`, and `/usr/local/bin/pip` (pip 25.0.1) are still in this image. The venv interpreter has no `pip` module. Startup, `/live`, `/ready`, and `alembic upgrade head` did not invoke uv, uvx, or global pip. Removing them is not required to reach Critical 0 and High 0. The six remaining pip advisories are five Medium and one Low. They are not a reason to add a removal step to this decision.

## Application tests

Host pytest on this unchanged tree: 4566 passed, 5 skipped. That suite runs on the host interpreter. The container results above are the Alpine evidence: boot, routing, `/live`, `/ready` without a database, `/ready` after migrations, production fail-closed startup, Alembic, imports, non-root execution, healthcheck, and shutdown.

## Recommendation

Alpine 3.24.2 plus `apk upgrade --no-cache zlib` is the leading migration candidate. It is the first measured full runtime image with Critical 0 and High 0, and the production checks in this note passed. The committed `Dockerfile` stays `python:3.12-slim` until an owner accepts the move from glibc to musl. Do not baseline the remaining Medium, Low, or Negligible matches.

Container vulnerability scanning on the committed Debian image stays fail-closed and is not PROVEN. R6 stays PARTIAL. IaC security scanning stays absent. Sprint 40 stays Planned and is not ENGINEERING COMPLETE. Sprint 38, Sprint 39, and Sprint 41 are unchanged. No Shopify call, live research, affiliate activation, or deploy was performed.
