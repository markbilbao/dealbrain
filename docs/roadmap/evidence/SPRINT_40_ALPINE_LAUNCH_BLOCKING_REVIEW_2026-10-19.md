# Alpine launch-blocking Medium review (2026-10-19)

This note classifies the ten findings on the temporary minimized Alpine image `dealbrain:cand-alpine-min`. It does not change the committed `Dockerfile`, load a baseline exception, publish an image, or deploy. The base-image comparison is unchanged.

The Grype 0.120.1 report is `/tmp/cve-candidates/grype-alpine-min.json`. Database schema `v6.1.10`, built `2026-10-18T06:27:17Z`. Counts: Critical 0, High 0, Medium 9, Low 0, Negligible 1. Empty `fix.state` values are normalized to `unknown` before the gate accepts the row. That normalization does not drop the finding or change its severity.

## Parser

`scripts/check_container_vuln_baseline.py` maps Grype's empty fix state to `unknown`. `fixed`, `not-fixed`, `wont-fix`, and explicit `unknown` stay unchanged. Any other value, including `None`, still fails closed. A missing `fix` object still fails closed with `missing fix metadata`. `""` and `"unknown"` share one fingerprint.

## Base64 mitigation

`app/security/base64url.py` is the only production decoder. `app/consumer/decision_owner.py` and `app/analytics/preference.py` call it. HMAC `compare_digest` still runs on the original encoded text before decode.

The helper accepts only the URL-safe alphabet, rejects `+` and `/`, rejects invalid padding, rejects bytes after the first padded block, and decodes with `b64decode(..., validate=True)`. Existing unpadded signed cookies still parse. It does not call `urlsafe_b64decode`.

Locked runtime site-packages still contain other `b64decode` call sites. None of them is a DealBrain request path:

- `pydantic` `Base64UrlBytes` / `Base64UrlStr` call `urlsafe_b64decode`. No application model uses those types.
- `fastapi.security.http` HTTP Basic, `websockets` basic-auth parsing, `starlette` session middleware, `psycopg` XA transaction ids, and `sqlalchemy.ext.serializer` are not referenced by application code. The application has no WebSocket route.

CVE-2025-12781 and CVE-2026-3446 remain real in CPython 3.12.15. They are not applicable to the production application after this mitigation. They are not launch-blocking. No baseline exception is loaded.

## Reachability

Searches covered `app/`, `alembic/`, the `Dockerfile`, Compose, CI workflows, `scripts/`, and the 996 Python files in the minimized image's `/app/.venv` site-packages.

| Question | Result |
|---|---|
| BusyBox wget | `busybox` 1.37.0-r31 owns `/bin/busybox` and lists `wget`. `/usr/bin/wget` points at it. No production file invokes `wget`. The healthcheck is `urllib.request`. |
| busybox-binsh | Package file is the `/bin/sh` symlink only. |
| ssl_client | Package file is `/usr/bin/ssl_client` only. It is not the wget request builder. |
| imaplib | Present in the stdlib. Zero imports in application code, Alembic, or locked runtime site-packages. |
| poplib | Present in the stdlib. Zero imports in application code, Alembic, or locked runtime site-packages. |
| TemporaryDirectory | Not constructed by `app/` or `alembic/`. `anyio` defines a wrapper and nothing in the venv constructs `anyio.TemporaryDirectory`. `uvloop/_testbase.py` and `sqlalchemy/testing` are not imported by the server. `scripts/` and tests use it outside the running container. |
| Morsel.js_output | No call in application code or locked runtime site-packages. Presence of `http.cookies` is not the call. |
| pkgutil.get_data | No call in application code or locked runtime site-packages. |

CVE-2025-60876 is a real wget flaw. It is not a false positive. No unofficial BusyBox patch is applied. Alpine 3.24 and edge still ship 1.37.0-r31, so there is no package upgrade. With no production call path it is real, non-reachable, and not launch-blocking.

## CVE-2026-6019 severity

Grype severity stays Medium. The gate is not overridden.

The PSF CNA record, via OSV, describes `BaseCookie.js_output()` / `Morsel.js_output()` returning an inline script that escapes `"` and does not neutralize `</script>`. The CNA CVSS v4 vector is `CVSS:4.0/AV:N/AC:L/AT:P/PR:H/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N`. That upstream vector is Low relative to Grype's Medium. It is recorded here and is not written into the scanner severity.

## CVE-2026-3479

The PSF CNA record, via OSV, is disputed (`isDisputed: true`). The CNA text says the documentation was incorrect, `pkgutil.get_data()` has the same security model as `open()`, and there is no vulnerability when that model is followed. The CNA CVSS v4 vector is `CVSS:4.0/AV:P/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:N/SI:N/SA:N`, score 0.0. Grype severity stays Negligible. This is the false-positive rationale. The image still joins resource path parts; that behavior matches the CNA's intended model.

## Launch-blocking matrix

| CVE | Reachable in production | Attacker-controlled path | Existing mitigation | Additional mitigation | Launch-blocking? | Rationale |
|---|---|---|---|---|---|---|
| CVE-2025-60876 busybox | no | no call reaches `busybox wget` or `/usr/bin/wget` | healthcheck uses urllib | none; no Alpine fix package | no | real wget flaw, non-reachable |
| CVE-2025-60876 busybox-binsh | no | package is only `/bin/sh` | no wget invocation | none | no | duplicate CPE, package lacks the request builder |
| CVE-2025-60876 ssl_client | no | package is only `ssl_client` | no wget invocation | none | no | duplicate CPE, not the request builder |
| CVE-2025-12781 | no | signed cookies no longer call `urlsafe_b64decode` | HMAC before decode | strict URL-safe decoder rejects `+` and `/` | no | real in stdlib, not on the production decode path |
| CVE-2026-3446 | no | cookie decode uses `validate=True` | HMAC before decode | reject data after the first padded block | no | real in stdlib, production path fails closed |
| CVE-2025-15366 | no | no `imaplib` import | none required for this app | none | no | real package flaw, no command path |
| CVE-2025-15367 | no | no `poplib` import | none required for this app | none | no | real package flaw, no command path |
| CVE-2026-12345 | no | server does not construct `TemporaryDirectory` | none required for this app | none | no | real package flaw, no cleanup path in the container |
| CVE-2026-6019 | no | no `js_output` call | none required for this app | none | no | real in stdlib, unused API; Grype Medium unchanged |
| CVE-2026-3479 | no | no `pkgutil.get_data` call | CNA says this is not a vulnerability | none | no | false positive; Grype Negligible unchanged |

Real reachable Mediums: none.

Real non-reachable Mediums: CVE-2025-60876 on `busybox` (the applet is real; the production call path is absent), CVE-2025-12781, CVE-2026-3446, CVE-2025-15366, CVE-2025-15367, CVE-2026-12345, and CVE-2026-6019. The `busybox-binsh` and `ssl_client` rows are the same CVE on packages that do not contain the wget request builder.

No launch-blocking Medium remains.

## Proposed exceptions, not loaded

Exact identities are in `docs/roadmap/evidence/sprint40-alpine-proposed-grype-exceptions.json`. The active baseline `tests/security/baselines/grype-image.baseline.json` still has `"exceptions": []`.

| ID | Vulnerability | Package | Rationale |
|---|---|---|---|
| GRYPE-001 | CVE-2025-60876 | busybox 1.37.0-r31 | not_applicable |
| GRYPE-002 | CVE-2025-60876 | busybox-binsh 1.37.0-r31 | not_applicable |
| GRYPE-003 | CVE-2025-60876 | ssl_client 1.37.0-r31 | not_applicable |
| GRYPE-004 | CVE-2025-12781 | python 3.12.15 | not_applicable |
| GRYPE-005 | CVE-2025-15366 | python 3.12.15 | not_applicable |
| GRYPE-006 | CVE-2025-15367 | python 3.12.15 | not_applicable |
| GRYPE-007 | CVE-2026-3446 | python 3.12.15 | not_applicable |
| GRYPE-008 | CVE-2026-12345 | python 3.12.15 | not_applicable |
| GRYPE-009 | CVE-2026-6019 | python 3.12.15 | not_applicable |
| GRYPE-010 | CVE-2026-3479 | python 3.12.15 | false_positive |

`fix_state` for the three BusyBox rows is `unknown` because Grype emitted `""` and the parser normalizes that to `unknown`. `fixed_versions` is `[]`. Python rows keep Grype's `fixed` state and the sorted fixed-version lists from the report. Fingerprints are `Finding.fingerprint()` after that normalization.

Regression tests that keep the non-applicability assumptions true:

- `tests/unit/test_sprint40_runtime_reachability.py` fails if production code calls `urlsafe_b64decode` or an unscoped `b64decode`, imports `imaplib` or `poplib`, calls `js_output`, constructs `TemporaryDirectory`, or if operational entrypoints contain `wget`.
- `tests/unit/test_urlsafe_b64.py` fails if signed cookies stop parsing, if tampered cookies parse, or if `+`, `/`, extra padded data, or bad padding decode.
- `tests/unit/test_sprint40_container_vuln_baseline.py` fails if the proposal objects do not match the gate's exact exception identity, and fails if the active baseline gains exceptions.
- CVE-2026-3479 has no code assumption to freeze. Its rationale is the CNA dispute. A later import of `pkgutil.get_data` would not by itself make the CNA record a vulnerability.

## Alpine recommendation

Recommend adopting the minimized Alpine runtime already measured on `dealbrain:cand-alpine-min`:

- Critical 0, High 0
- no launch-blocking Medium
- the reachable Base64 cookie path is mitigated
- the earlier compatibility run on that image passed: non-root uid 100, Python 3.12.15, imports, Alembic 1.18.5 head `a7b8c9d0e1f2`, migrations on PostgreSQL 16, `/live` 200, `/ready` 503 without the database and 200 after migrate, healthcheck healthy, SIGTERM shutdown, production fail-closed exit 3 naming `APP_SECRET_KEY`

The committed `Dockerfile` stays `python:3.12-slim` until the owner approves that change. This review does not commit the Alpine Dockerfile.

The Debian image gate remains fail-closed. Container vulnerability scanning is not PROVEN. R6 stays PARTIAL. IaC scanning stays absent. Sprint 40 stays Planned.

## Owner decision

The owner approved this Alpine runtime and the exact exception set in `sprint40-alpine-proposed-grype-exceptions.json`. The committed implementation is recorded in `SPRINT_40_ALPINE_RUNTIME_IMPLEMENTATION_2026-10-19.md`. This review's earlier recommendation, written before that approval, is unchanged.
