# Sprint 26 — Staging Current-Main Proof & Roadmap Bootstrap

**Status:** Planned
**Primary owner / domain:** Ops / release engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-6; P1-7 (primary)

## Objective

Prove the current launch candidate on staging and bootstrap external dependency applications so Global Public Beta work can proceed on evidence, not assumptions.

## Included requirements

- Deploy current main (or designated launch-candidate digest) to staging via existing deploy-staging architecture
- Smoke: /live, /ready, auth register/login, search→DealScore→recommendation on staging
- Record staging-deploy-evidence for the launch candidate
- Open EXT applications for merchant markets, email provider, domain, support/privacy contacts
- Publish initial entries in EXTERNAL_DEPENDENCY_REGISTER.md with owners and dates
- Confirm fixture/simulated offers cannot be labeled as live in staging responses

## Explicit non-goals

- Production AWS apply
- Real merchant HTTP
- Consumer SPA rewrite
- Legal publication

## External dependencies

- EXT-01…EXT-05 bootstrap
- EXT-08
- EXT-10
- EXT-17
- EXT-18

## Implementation deliverables

- Staging deploy of launch candidate
- Smoke scripts/checklist execution notes
- Register updates

## Documentation deliverables

- Staging evidence artifact references
- Updated external dependency statuses
- Sprint 26 completion note

## Required tests

- Existing CI green on candidate
- Staging smoke checklist

## Required staging evidence

- staging_ok evidence for launch candidate
- /ready READY with sqlalchemy bindings

## Required production evidence

- None required

## Acceptance criteria

- Launch candidate digest is staging_ok
- Smoke journey recorded (pass/fail with links)
- External dependency register shows application dates for critical EXT rows
- No production resources mutated beyond read-only verification
- **P1-7 closed:** current launch-candidate staging promotion discipline is defined and evidenced here; Sprint 45 may only **re-verify** the same gate on the frozen candidate (not a second primary owner)

## Predecessor sprints

25b.3, 25b.5*

## Parallelizable work

Legal counsel scheduling, UI design spike

## Go / no-go gate

Go if staging smoke green; No-go blocks 27+ public-path work that assumes staging truth

## Rollback or contingency

Use existing staging rollback workflow to last known good digest

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
