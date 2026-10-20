# Minimized Alpine review (2026-10-19)

This note reviews a temporary image. It does not change the committed `Dockerfile`, add a baseline exception, publish an image, or deploy. The Grype pin, checksum, database policy, local Docker source, JSON parser, and scan-before-push order are unchanged.

The temporary Dockerfile is `/tmp/cve-candidates/Dockerfile.alpine-min`. It is not committed.

## Construction

Base: `python:3.12-alpine`, Alpine 3.24.2, CPython 3.12.15.

`uv` is copied only into the dependency stage. The runtime stage does not contain `/bin/uv` or `/bin/uvx`.

```
apk upgrade --no-cache zlib
```

Build output: `(1/1) Upgrading zlib (1.3.2-r0 -> 1.3.2-r1)`. `apk info -v` shows `zlib-1.3.2-r1`. No other Alpine package changed in that command.

Global pip removal, runtime stage only:

- `/usr/local/bin/pip`, `pip3`, and `pip3.12`
- `/usr/local/lib/python3.12/site-packages/pip` and `pip-25.0.1.dist-info`
- `/usr/local/lib/python3.12/ensurepip/_bundled/pip-25.0.1-py3-none-any.whl`

The virtualenv has no pip module. `python -m pip` reports `No module named pip`. Locked dependencies were not changed. `uv sync` downloaded prebuilt wheels. Wheel tags, with no `direct_url.json`:

| Package | Tag |
|---|---|
| asyncpg 0.31.0 | `cp312-cp312-musllinux_1_2_x86_64` |
| psycopg-binary 3.3.4 | `cp312-cp312-musllinux_1_2_x86_64` |
| uvloop 0.22.1 | `cp312-cp312-musllinux_1_2_x86_64` |
| greenlet 3.5.4 | `cp312-cp312-musllinux_1_2_x86_64` |
| pydantic-core 2.46.4 | `cp312-cp312-musllinux_1_1_x86_64` |

## Sizes and package counts

Grype 0.120.1 `--verbose` reports `gathered packages`. Both scans below use database schema `v6.1.10`, built `2026-10-18T06:27:17Z`.

| Image | Bytes | Gathered packages |
|---|---:|---:|
| Debian 13 control `dealbrain:ci-local` | 103,823,873 | 1182 (prior gate run) |
| Alpine plus zlib, uv and pip still present | 81,862,368 | 1133 |
| Minimized Alpine | 62,836,950 | 70 |

The package-count drop is mostly the static uv binary, which Grype inventories as embedded packages. The vulnerability-match drop is only the pip advisories.

## Scan

Same image pair, same updated database:

| Image | Findings | Critical | High | Medium | Low | Negligible |
|---|---:|---:|---:|---:|---:|---:|
| Alpine plus zlib, uv and pip present | 16 | 0 | 0 | 14 | 1 | 1 |
| Minimized Alpine | 10 | 0 | 0 | 9 | 0 | 1 |

Removed, and nothing else:

| ID | Package | Version | Severity |
|---|---|---|---|
| GHSA-4xh5-x5gv-qwph | pip | 25.0.1 | Medium |
| GHSA-58qw-9mgm-455v | pip | 25.0.1 | Medium |
| GHSA-jp4c-xjxw-mgf9 | pip | 25.0.1 | Medium |
| GHSA-qwm4-qh6w-59xr | pip | 25.0.1 | Medium |
| GHSA-wf93-45jw-7689 | pip | 25.0.1 | Medium |
| GHSA-6vgw-5pg2-w6jp | pip | 25.0.1 | Low |

`scripts/check_container_vuln_baseline.py --image docker:dealbrain:cand-alpine-min` did not finish the comparison. It failed closed with `grype match CVE-2025-60876 has an unexpected fix state`. Grype emitted `fix.state=""` and `fix.versions=[]` for the three BusyBox rows. The parser allows only `fixed`, `not-fixed`, `wont-fix`, and `unknown`. The parser was not changed. The counts above come from that same Grype 0.120.1 JSON report, local Docker source, and the committed `scripts/security/grype.yaml` policy. The baseline still has zero exceptions.

## Remaining findings

| Vulnerability | Package | Installed | Type | Severity | Fix state | Fixed version | Applicability | Action |
|---|---|---|---|---|---|---|---|---|
| CVE-2025-60876 | busybox | 1.37.0-r31 | apk | Medium | empty | none listed | wget applet is in `/bin/busybox`; `/usr/bin/wget` points at it | real vulnerability with no current safe fix |
| CVE-2025-60876 | busybox-binsh | 1.37.0-r31 | apk | Medium | empty | none listed | package contains only `/bin/sh` | not applicable |
| CVE-2025-60876 | ssl_client | 1.37.0-r31 | apk | Medium | empty | none listed | separate 14,384-byte TLS helper, not the wget request builder | not applicable |
| CVE-2025-12781 | python | 3.12.15 | binary | Medium | fixed | 3.13.10, 3.14.1, 3.15.0a2 | `base64` is present; app calls `urlsafe_b64decode` | real vulnerability with no current safe fix |
| CVE-2025-15366 | python | 3.12.15 | binary | Medium | fixed | 3.13.15, 3.14.7, 3.15.0a6 | `imaplib` is present; application code does not import it | real vulnerability with no current safe fix |
| CVE-2025-15367 | python | 3.12.15 | binary | Medium | fixed | 3.15.0a6 | `poplib` is present; application code does not import it | real vulnerability with no current safe fix |
| CVE-2026-3446 | python | 3.12.15 | binary | Medium | fixed | 3.13.13, 3.14.4, 3.15.0a8 | `b64decode('YQ==YQ==')` returns `b'a'` in this image | real vulnerability with no current safe fix |
| CVE-2026-12345 | python | 3.12.15 | binary | Medium | fixed | 3.15.0rc3 | `tempfile.TemporaryDirectory` is in the image; application code does not use it | real vulnerability with no current safe fix |
| CVE-2026-6019 | python | 3.12.15 | binary | Medium | fixed | 3.13.14, 3.14.5rc1, 3.15.0b1 | `Morsel.js_output` does not base64-encode; application code does not call it | real vulnerability with no current safe fix |
| CVE-2026-3479 | python | 3.12.15 | binary | Negligible | fixed | 3.13.13, 3.14.4, 3.15.0a8 | disputed; CNA says there is no vulnerability | false positive |

No row is safely fixable inside Alpine 3.24 without a major Python upgrade or a BusyBox package that the 3.24 and edge repositories do not ship. No exception was added.

## BusyBox

`CVE-2025-60876`: BusyBox wget accepts raw CR, LF, other C0 bytes, and a raw space in the HTTP request-target, splitting the request line. NVD's CPE bound is up to and including 1.37.0. The prose says "1.3.7"; the CPE and Alpine tracker use 1.37.0. Alpine's tracker lists `busybox` `1.37.0-r31` on edge-main as possibly vulnerable. Buildroot carries a wget patch for this CVE. That patch is not an Alpine package.

Installed packages:

| Package | Version | Files |
|---|---|---|
| busybox | 1.37.0-r31 | `/bin/busybox` (804,616 bytes). `busybox --list` includes `wget`. `/usr/bin/wget` is a symlink to `/bin/busybox`. |
| busybox-binsh | 1.37.0-r31 | `/bin/sh` symlink to `/bin/busybox` |
| ssl_client | 1.37.0-r31 | `/usr/bin/ssl_client` only |

`apk policy` on Alpine v3.24 main shows `1.37.0-r31` as both installed and the repository version. `apk upgrade -s busybox busybox-binsh ssl_client` changes nothing. No rescan after a BusyBox upgrade was possible, because no newer package is available. Severity Medium. Fix state empty. No fixed version listed.

The `busybox` row is a real Medium with no current safe fix. The shell and TLS-helper rows are duplicate CPE matches on packages that do not contain the wget request builder.

## Python 3.12.15

The image binary is official CPython 3.12.15 (`main, Oct 1 2026, 21:45:39`). Python 3.12.15, released with the 2026-10-01 security set, is the newest 3.12 release found. Its published security list does not include the CVEs below. There is no 3.12.16 to install. Fixes listed by Grype are on 3.13, 3.14, or 3.15. This review does not change the Python major version. Matches are NVD CPE matches on `/usr/local/bin/python3.12` and `/usr/local/lib/libpython3.12.so.1.0`, not Alpine `apk` records, so an Alpine Python rebuild is not what this image is running.

| ID | Affected range from the CNA / Grype constraint | 3.12.15 affected | 3.12 backport in this image | Module present | Classification |
|---|---|---|---|---|---|
| CVE-2025-12781 | 0 before 3.13.10; 3.14.0 before 3.14.1; 3.15.0a1 before 3.15.0a2 | yes | no. `b64decode` still translates `altchars` and then accepts `+/`. `urlsafe_b64decode('YQ+/')` returns bytes. The upstream change deprecates that behavior; it is not in this file | `base64`. `app/consumer/decision_owner.py` and `app/analytics/preference.py` call `urlsafe_b64decode` | real, no safe 3.12 fix |
| CVE-2025-15366 | 0 before 3.13.15; 3.14.0 before 3.14.7; 3.15.0a1 before 3.15.0a6 | yes | no. `imaplib.IMAP4._command` appends arguments and does not reject CR/LF | `imaplib`. Application code does not import it | real, no safe 3.12 fix |
| CVE-2025-15367 | before 3.15.0a6 | yes | no. `poplib.POP3._putcmd` sends the line plus CRLF and does not reject embedded newlines | `poplib`. Application code does not import it | real, no safe 3.12 fix |
| CVE-2026-3446 | before 3.13.13; 3.14.0 before 3.14.4; 3.15.0a1 before 3.15.0a8 | yes | no. `b64decode('YQ==YQ==')` returns `b'a'`; `validate=True` raises | `base64` | real, no safe 3.12 fix |
| CVE-2026-12345 | before 3.15.0rc3 | yes | no 3.12/3.13/3.14 version is listed | `tempfile.TemporaryDirectory`. Application code does not use it. Tests and scripts do | real, no safe 3.12 fix |
| CVE-2026-6019 | before 3.13.14; 3.14.0a1 before 3.14.5rc1; 3.15.0a1 before 3.15.0b1 | yes | no. `Morsel.js_output` rejects control characters and escapes quotes. It does not base64-encode the cookie value | `http.cookies`. Application code does not call `js_output` | real, no safe 3.12 fix |
| CVE-2026-3479 | before 3.13.13; 3.14.0 before 3.14.4; 3.15.0a1 before 3.15.0a8 | disputed | documentation clarification, not a code fix required for safety | `pkgutil.get_data` still joins the resource path. The CNA says the documented rejection of `..` was wrong and the function has the same model as `open()`. CVSS 0.0 | false positive |

Fedora's `python3.12-3.12.12-4` changelog records distro patches for CVE-2025-15366 and CVE-2025-15367. Red Hat's `python3.12-3.12.14-1.hum1` advisory lists CVE-2026-3446, CVE-2026-3479, and CVE-2026-6019. Those are vendor rebuilds. The files in this official 3.12.15 image do not contain those mitigations.

## Compatibility

Process user `uid=100(dealbrain)`. Python 3.12.15. urllib imports. Imports succeed for httpx, asyncpg, psycopg, uvicorn, SQLAlchemy, Alembic, `app.main`, and `app.auth.email_resend`. `alembic --version` is 1.18.5. `alembic current` against PostgreSQL 16 reports `a7b8c9d0e1f2 (head)`. `alembic upgrade head` completes.

Production defaults exit 3 with `ConfigurationValidationError` naming `APP_SECRET_KEY`. Uvicorn does not stay up. Development startup serves `GET /live` 200. `GET /ready` is 503 with `"database": "down"` without PostgreSQL, and 200 with `"ready": true` and `"database": "up"` after the migrated database is reachable. Docker health status was `healthy`. The healthcheck command succeeded. `docker stop` logged `Shutting down PiqSavi` and `Application shutdown complete`.

`/bin/uv`, `/bin/uvx`, and global pip are absent. Startup and Alembic use `/app/.venv/bin/uvicorn` and `/app/.venv/bin/alembic`.

## Proposed Dockerfile, not committed

Keep the current runtime shape, with these differences:

- `FROM python:3.12-alpine`
- copy `/bin/uv` only in the dependency stage
- `RUN apk upgrade --no-cache zlib` and delete the global pip paths listed above
- leave the locked dependency set, non-root user, healthcheck, and `uvicorn` command as they are

## Decision

Critical is 0 and High is 0 on the minimized image, and the compatibility checks passed. Adoption stops here. Real Medium findings remain with no safe remediation that stays on Python 3.12 and Alpine 3.24: `CVE-2025-60876` on `busybox` `1.37.0-r31`, and CVE-2025-12781, CVE-2025-15366, CVE-2025-15367, CVE-2026-3446, CVE-2026-12345, and CVE-2026-6019 on Python 3.12.15. The committed Dockerfile stays `python:3.12-slim`. No exception is proposed for a real finding. The false-positive and not-applicable rows above are not added to the baseline.

The strict gate also cannot currently record the BusyBox rows, because their fix state is empty. That is fail-closed parser behavior, not a reason to widen the allowed states in this pass.

Container vulnerability scanning on the committed Debian image stays fail-closed and is not PROVEN. R6 stays PARTIAL. IaC security scanning stays absent. Sprint 40 stays Planned and is not ENGINEERING COMPLETE. Sprint 38, Sprint 39, and Sprint 41 are unchanged. No Shopify call, live research, affiliate activation, or deploy was performed.
