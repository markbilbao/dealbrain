# Sprint 40 runtime-base comparison (2026-10-17)

This note does not rewrite the container-gate record. It does not baseline a finding, accept risk, or select IaC scanning. It is not named Sprint 40.8. The committed `Dockerfile` is unchanged. No image was published. No deploy was performed.

Starting `main` is `6ed3662d520d9e41a4bdc3df5ccc56b49c520300`. Comparison head before this note is `f4320919cbb84dcd2e9552e558bbdc535326f298`. Every candidate used that source, `pyproject.toml`, `uv.lock`, and the uv 0.13.1 musl binary already present in `dealbrain:ci-local`. Grype 0.120.1 scanned each full runtime image from the local Docker daemon. The vulnerability database was schema `v6.1.10`, built `2026-10-16T06:29:51Z`, and was already current (`No vulnerability database update available`). Temporary Dockerfiles lived outside the repository.

## Matrix

Raw Grype match counts. Duplicate package rows are included.

| Candidate | OS | Packages | Critical | High | Medium | Low | Negligible |
|---|---|---:|---:|---:|---:|---:|---:|
| A. `python:3.12-slim` control | Debian 13.7 | 1182 | 0 | 55 | 59 | 11 | 47 |
| B. `python:3.12-slim-bookworm` | Debian 12.15 | 1200 | 3 | 79 | 98 | 18 | 87 |
| C. Bookworm plus `apt-get upgrade` | Debian 12.15 | 1200 | 3 | 79 | 98 | 18 | 87 |
| D. `python:3.12-alpine` measurement | Alpine 3.24.2 | 1133 | 0 | 1 | 14 | 1 | 1 |

Unique vulnerability IDs: control 80, Bookworm 129, Bookworm upgrade 129, Alpine 15. Bookworm and the upgrade image have the same match multiset. `apt-get upgrade` did not change a package version that Grype reports.

Image sizes: control 103,823,873 bytes, Bookworm 108,280,700, Bookworm upgrade 108,281,423, Alpine 81,767,283.

## Control HIGH

14 unique HIGH IDs. None lists a fixed version. 54 matches are `wont-fix`. `CVE-2026-85091` on `zlib1g` `1:1.3.dfsg+really1.3.1-1+b1` is `not-fixed`.

| Root | IDs | Packages |
|---|---|---|
| util-linux | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 | bsdutils, libblkid1, liblastlog2-2, libmount1, libsmartcols1, libuuid1, login, mount, util-linux |
| gcc runtime | CVE-2026-102010, CVE-2026-95619 | gcc-14-base, libgcc-s1, libstdc++6 |
| glibc | CVE-2026-19499, CVE-2026-5435 | libc-bin, libc6 |
| ncurses | CVE-2025-69720 | libncursesw6, libtinfo6, ncurses-base, ncurses-bin |
| acl | CVE-2026-54369, CVE-2026-54370 | libacl1 |
| perl | CVE-2026-82560, CVE-2026-9538 | perl-base |
| zlib | CVE-2026-85091 | zlib1g |

`wont-fix` is not treated as a false positive.

## Bookworm

Bookworm does not reach 0 HIGH. It adds 3 Critical matches (`CVE-2025-7458` on `libsqlite3-0`, `CVE-2026-5450` on `libc-bin` and `libc6`) and raises HIGH from 55 to 79. Unique Critical/HIGH IDs: 25. None lists a fixed version. Extra HIGH package families include krb5, gzip, and OpenSSL, plus the same zlib, glibc, ncurses, gcc, acl, perl, and util-linux roots on Debian 12 versions. The upgrade experiment matches Bookworm exactly, so it is not committed.

## Alpine measurement

Alpine is not selected. The locked dependencies downloaded musl wheels (`asyncpg`, `psycopg-binary`, `uvloop`, `greenlet`, `pydantic-core`). The build did not compile those packages from source. `uvloop` in the Alpine image is `loop.cpython-312-x86_64-linux-musl.so`, linked with `libc.musl`. The control image uses `loop.cpython-312-x86_64-linux-gnu.so` and `libc.so.6`. That is a libc change.

Imports of urllib, httpx, asyncpg, psycopg, uvicorn, SQLAlchemy, Alembic, `app.main`, and `app.auth.email_resend` succeeded, and `alembic --version` printed 1.18.5. The process user is uid 100. Those checks do not make musl the production libc.

Alpine still has one HIGH match: `CVE-2026-85091` on `zlib` `1.3.2-r0`, fix state `fixed`, listed fix `1.3.2-r1`. Critical is 0. The remaining Alpine matches are Medium, Low, or Negligible, including the same Python 3.12.15 NVD CPE matches and global pip 25.0.1.

## Runtime tools

Production startup is `uvicorn` from `/app/.venv/bin`. Compose migration is `alembic upgrade head` from that venv. Deploy workflows install jsonschema with the runner's pip. They do not call `/bin/uv`, `/bin/uvx`, or the image's global pip.

A temporary Debian 13 image copied uv only into the dependency stage and deleted global pip from the runtime stage. `/bin/uv`, `/bin/uvx`, and `/usr/local/bin/pip` were absent. Imports and Alembic still succeeded. Grype reported 119 packages, 166 matches, Critical 0, High 55, Medium 54, Low 10, Negligible 47. The six pip advisories disappeared. The 55 HIGH Debian matches remained, including `CVE-2026-85091`. The control's 1182 package count includes contents of the static uv binary. Removing uv and pip is compatible and does not clear HIGH, so the committed Dockerfile still contains both.

## Python binary matches

The control's Python findings are NVD CPE matches on the `python` binary `3.12.15`. They are Medium or Negligible. Listed fixed versions are on 3.13, 3.14, or 3.15 only. Grype does not list a 3.12 fix. That is not a reason to change the Python major version, and it is not a baseline exception.

## Decision

No candidate reaches Critical 0 and High 0 on a glibc Debian runtime. Bookworm is worse than `python:3.12-slim`. Alpine is a musl migration and still has one HIGH zlib match. The committed Dockerfile stays `python:3.12-slim`. The Grype gate, its pin, checksum, database checks, local-image rule, and scan-before-push order are unchanged. No exception was added.

With `APP_ENV=development`, the control image served `GET /live` 200 and `GET /ready` 503 because PostgreSQL was absent. With the image's production defaults and no secrets, startup failed closed in configuration validation and did not serve `/live`.

## Status

Container vulnerability scanning stays fail-closed and is not PROVEN. R6 stays PARTIAL. IaC security scanning stays absent. Sprint 40 stays Planned and is not ENGINEERING COMPLETE. Sprint 38, Sprint 39, and Sprint 41 are unchanged. No Shopify call, live research, affiliate activation, or deploy was performed. Full pytest on this unchanged application tree: 4566 passed, 5 skipped.
