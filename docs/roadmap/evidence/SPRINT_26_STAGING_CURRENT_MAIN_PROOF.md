# Sprint 26 — Current-Main Staging Proof Evidence

**Document type:** Sanitized technical evidence package  
**Sprint definition:** [`../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)  
**Packaging date (UTC):** 2026-08-06  
**Sprint 26 closure status:** **Open** — technical staging proof verified; external dependency bootstrap remains

---

## 1. Purpose and scope

This document packages verified evidence that the current launch-candidate commit on `main` was successfully deployed to staging, passed host-evidence validation with `final_status=staging_ok`, satisfied zero-mutation readiness/search smokes, and passed authenticated lifecycle smoke with intentional cleanup residue.

**In scope**

- Deploy Staging identity correlation (CI → Build Image → release → deploy → host evidence)
- Staging AWS health observation (read-only)
- Zero-mutation HTTP smoke
- Authenticated register/login/session/logout smoke
- Temporary staging-account residue record
- Deferred non-blocking findings

**Out of scope**

- External dependency applications (see [`SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md))
- Production mutation or production deploy
- Application-code changes
- Claiming Sprint 26 complete

---

## 2. Repository SHA

| Field | Value |
|-------|-------|
| Branch at proof time | `main` |
| Git SHA | `79bd03f9e3df99efe4a978c48bec79eceec46767` |
| Short SHA | `79bd03f9e3df` |
| Evidence packaging branch | `sprint-26-staging-proof-evidence` |

---

## 3. CI and Build Image authority

| Authority | Run ID | Result |
|-----------|--------|--------|
| CI | `31070428452` | Authority for candidate (success path used for deploy) |
| Build Image | `31070741743` | Immutable image publication for candidate |

---

## 4. Release ID and immutable digest

| Field | Value |
|-------|-------|
| Release ID | `rel-20260806T041533Z-79bd03f9e3df` |
| Git SHA | `79bd03f9e3df99efe4a978c48bec79eceec46767` |
| Image digest | `sha256:c8f5610d9538bac17db42b456e96455adb59d5a113494e40fae32408f23d87b8` |
| Manifest SHA-256 | `fc529721c1f3c819da4ce250460520a5b44c366c133cafcb6b1f11a4e037b95b` |

Identity correlation: release ID embeds the short SHA; deploy and host evidence bind the same full SHA, digest, and manifest hash.

---

## 5. Deploy Staging run and job IDs

| Field | Value |
|-------|-------|
| Workflow | Deploy Staging |
| Deploy number | `#16` |
| Run ID | `31072785397` |
| Job ID | `92524021958` |
| Result | `success` |

---

## 6. Host evidence validation

| Field | Value |
|-------|-------|
| Host evidence `final_status` | `staging_ok` |
| GitHub evidence artifact name | `staging-evidence-rel-20260806T041533Z-79bd03f9e3df-31072785397` |
| GitHub artifact digest | `sha256:a292ef95867e501850b99b26feeadfc6a5b8c54efc908a562858611be0498778` |
| S3 host evidence | Downloaded; checksum sidecar matched |
| Official evidence validator | Returned OK |

**GitHub artifact-access limitation (non-blocking):** local GitHub credentials returned `401` when attempting independent download of the GitHub Actions artifact bytes. This does **not** indicate deployment failure. S3 host evidence was independently validated with matching checksum sidecar and official validator OK.

---

## 7. Migration result

| Field | Value |
|-------|-------|
| Migration revision before | `d4e5f6a7b8c9` |
| Migration revision after | `d4e5f6a7b8c9` |
| Interpretation | No migration drift across deploy; before and after revisions identical |

---

## 8. AWS health matrix

| Check | Observed value |
|-------|----------------|
| AWS account | `941035169846` |
| Region | `us-east-1` |
| EC2 | `running` |
| EC2 system status | `ok` |
| EC2 instance status | `ok` |
| SSM | `Online` |
| ALB target | `healthy` |
| RDS | `available` |
| RDS `PubliclyAccessible` | `false` |

Observations were zero-mutation / read-only. No production resources were mutated.

---

## 9. Zero-mutation smoke matrix

| Probe / check | Result |
|---------------|--------|
| `/live` | `200`, `live=true` |
| `/ready` | `200`, `ready=true`, `persistence_level=READY` |
| User-platform bindings | SQLAlchemy selected |
| `/health` | `200`, `environment=staging` |
| `/openapi.json` | `200` |
| DealScore search | `200` |
| Recommendation search | `200` |
| Marketplace search | `200` |
| Affiliate disclosure | `200` |
| Invalid empty queries | `422` with request ID |
| `X-Request-ID` behavior | Present |

**Honesty note (observed, non-blocking for this proof):** DealScore and Recommendation responses disclose mocked connector data and state that prices are not live marketplace data. Raw marketplace search does not contain an equally explicit fixture/not-live field (see deferred finding B).

---

## 10. Authenticated smoke matrix

**Verdict:** `AUTHENTICATED STAGING SMOKE VERIFIED WITH CLEANUP RESIDUE`

| Field | Value |
|-------|-------|
| UTC window start | `2026-08-06T05:51:38Z` |
| UTC window end | `2026-08-06T05:51:46Z` |

| Step | HTTP / outcome | Result |
|------|----------------|--------|
| Registration | `201` | Pass |
| Duplicate registration | `409` | Pass |
| Failed login | `401` | Pass |
| Successful login | `200` | Pass |
| Authenticated `/me` | `200` | Pass |
| Repeated `/me` (same session) | `200` | Pass |
| Authenticated DealScore search | `200` | Pass |
| Logout | `204` | Pass |
| Post-logout `/me` | `401` | Pass |
| Session revocation | Effective | Pass |
| Secrets handling | Passwords/tokens/cookies not printed; temporary local auth files deleted | Pass |

No password, token, cookie, authorization header, or other secret material is recorded in this package.

---

## 11. Temporary-account residue

| Field | Value |
|-------|-------|
| Test email | `sprint26-smoke-20260806T055138Z-ac13d7b8@example.invalid` |
| Non-secret user ID | `fc90f332-3082-48aa-aaaf-aeff8e5e7c46` |
| Creation timestamp (UTC) | `2026-08-06T05:51:38Z` |
| Reason it remains | No supported account-deletion endpoint exists; user is intentional staging smoke residue |
| Future cleanup owner | Sprint 28 privacy / account-deletion work (when a supported deletion path exists) |
| Prohibition | Do **not** clean up via direct database access, SSM, or any invented out-of-band mechanism |

---

## 12. Evidence limitations

1. GitHub Actions artifact bytes were not independently re-downloaded locally (`401` credential limitation). S3 host evidence + checksum sidecar + official validator OK remain the binding host-evidence authority. This limitation is **non-blocking** and is **not** a deployment failure.
2. Authenticated smoke left intentional `example.invalid` residue pending a supported deletion API.
3. Deployment-evidence schema depth gaps are recorded as deferred finding C (not deployment failure).
4. External dependency applications were **not** performed as part of this packaging task.

---

## 13. Confirmation — no production mutation

- Deploy Staging `#16` targeted staging only.
- AWS probes were read-only against staging account `941035169846` / `us-east-1`.
- No production apply, production deploy, production rollback, production SSM, or production secret mutation occurred during the verified window or this documentation packaging.
- This packaging task is documentation-only.

---

## 14. Deferred non-blocking findings

### A. Auth meta persistence reporting mismatch

- **Observation:** `/api/v1/auth/meta` reports `persistence=memory` while `/ready` identifies the SQLAlchemy user-platform binding.
- **Impact:** Observability / identity-reporting honesty; does not reverse `/ready` SQLAlchemy binding evidence for this staging proof.
- **Suggested owner:** Sprint 27 identity hardening
- **Sprint 26 blocker?** No

### B. Marketplace search fixture/not-live disclosure gap

- **Observation:** Raw marketplace search lacks the same explicit fixture/not-live disclosure present in DealScore and Recommendation responses.
- **Impact:** Product-honesty consistency for mocked connector data on the raw search path.
- **Suggested owner:** Sprint 31 (merchant platform / normalized offer + provenance contracts), with Sprint 37 coordination for coverage/honesty product behavior
- **Sprint 26 blocker?** No (unless future policy elevates it; current Sprint 26 definition does not)

### C. Deployment-evidence schema depth

- **Observation:** Schema does not currently include current/previous pointer before and after, deploy script checksum, or deployment capability/version.
- **Impact:** Evidence-depth improvement opportunity only.
- **Suggested owner:** Future staging-evidence schema hardening (ops / release engineering; not a Sprint 26 close gate)
- **Sprint 26 blocker?** No

---

## 15. Exact technical conclusion

**SPRINT 26 CURRENT-MAIN STAGING PROOF VERIFIED**

This conclusion covers technical current-main staging proof, release-evidence correlation, zero-mutation smoke, authenticated lifecycle smoke, and P1-7 technical promotion-discipline evidence for SHA `79bd03f9e3df99efe4a978c48bec79eceec46767`.

It does **not** close Sprint 26. External dependency bootstrap actions, application dates, register status updates, and final Sprint 26 go/no-go remain pending (see [`SPRINT_26_COMPLETION_DRAFT.md`](SPRINT_26_COMPLETION_DRAFT.md)).
