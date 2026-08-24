# Sprint 45 — Controlled Global Public Beta Launch

**Status:** Planned
**Primary owner / domain:** Launch director + on-call
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Program launch

## Objective

Execute controlled public launch **no later than September 30, 2026** by performing **final go/no-go verification** against all Global Public Beta exit criteria (EC-01…EC-30). Sprint 45 does not re-own implementation for criteria primarily owned by earlier sprints, except launch-control items EC-20, EC-22, and EC-30.

September 30, 2026 is the owner target launch date. It is not permission to bypass security, privacy/legal, truthfulness, evidence, rehearsal, or production-readiness gates. Reduce optional market/provider/feature scope rather than weaken those gates.

## Included requirements

- Attach public DNS if not already
- Limited rollout percentages
- Launch monitoring window + handoff package for Sprint 46
- Publish legal URLs if not live
- Publish coverage matrix
- Enforce exit criteria EC-01…EC-30 from master roadmap §9 (verify owners’ evidence; do not substitute documentation for runtime proof)
- Market subset rule applied if EXT failures (remove markets rather than fake readiness)
- Do not mark launch ready if any non-waivable blocker remains
- Where an optional market is not certified: remove that market from launch claims
- Where an optional non-core feature is not ready: demote/remove the claim or feature rather than fake readiness
- Public launch must provide a genuinely useful PiqSavi shopping experience in the supported scope
- At least one genuinely useful certified market must exist for public shopping launch

### SEO public cutover

- Only approved public pages may become indexable
- Do not promise ranking position
- Sprint 45 proves: pages are technically indexable where intended; private routes are not; sitemap/robots/canonicals are correct; Search Console is connected; structured data is valid where used
- SEO ranking is an acquisition outcome, not an acceptance guarantee
- Incident war-room staffing; rollback authority assignment (EC-20)
- Signed final launch checklist (EC-22)
- Confirm Sprint 26 promotion discipline still holds for the frozen launch candidate (final verification of P1-7 — not duplicate primary ownership)
- Re-run and verify CC-01 as a required child gate of EC-02.
- Attach signed CC-01 evidence and its immutable candidate digest to the EC-22 final launch checklist.
- Reject CC-01 evidence produced from a different digest, stale environment, mock-only live-research path, or incomplete surface/device matrix.

## Explicit non-goals

- 100% traffic without soak
- New feature launches
- Implementing deferred Sprint 27–44 work under a Sprint 45 label
- Using Sprint 46 to absorb unresolved launch blockers

## External dependencies

- Remaining blocking EXT must be provisioned

## Implementation deliverables

- Rollout controls
- Launch communications
- Monitoring handoff package for Sprint 46

## Documentation deliverables

- Signed final launch checklist
- Launch report
- Live coverage matrix
- Per-criterion go/no-go record referencing EC-01…EC-22

## Required tests

- Post-deploy smoke prod
- Fixture-as-live guard

## Required staging evidence

- Candidate unchanged from 44; still satisfies Sprint 26 promotion gate

## Required production evidence

- Production proven under controlled rollout

## Acceptance criteria

- All applicable EC-01…EC-30 true (or market/feature removed where the criterion allows)
- Owner target date: no later than September 30, 2026
- No non-waivable blocker remains
- Only certified markets named
- EC-09 capability-policy invariant verified for every named shopping market (declared, evidence-backed, fail-closed enforced; unknown permissions do not enable production features); remove/disable markets or providers that fail rather than weakening the gate
- Rollback authority on-call
- Checklist signed
- Monitoring handoff to Sprint 46 recorded
- No documentation-only evidence accepted for runtime criteria
- EC-02 cannot pass unless CC-01 passes on the frozen launch candidate.
- EC-22 cannot be signed unless the exact CC-01 evidence package is attached.
- Public launch is no-go if Ask PiqSavi loses context, changes the evaluated set without approved research, mutates canonical PiqScores, fabricates execution, violates affiliate neutrality, or fails Results/Compare/Why/mobile continuity.

### Additive PiqSavi launch gate (not marked complete)

Authority: [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)

- PiqSavi is the only master brand presented to consumers
- `piqsavi.com` canonical hostname verified
- `www` redirect verified
- Live metadata uses PiqSavi
- Public email identity uses PiqSavi
- Public legal/support contacts use PiqSavi
- No fixture/demo DealBrain hostname leaks publicly
- No accidental DealBrain branding appears in consumer UI/API documentation
- Internal DealBrain infrastructure continues operating unchanged

Sprint 45 remains controlled Global Public Beta launch.

## Predecessor sprints

44

## Parallelizable work

None

## Go / no-go gate

Launch go

## Rollback or contingency

Execute prod rollback; status communication

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
