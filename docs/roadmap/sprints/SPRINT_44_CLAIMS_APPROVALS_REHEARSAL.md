# Sprint 44 — Claims Control, Approvals & Production Rehearsal

**Status:** Planned
**Primary owner / domain:** Launch director + legal + security + ops
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes

## Objective

Freeze claims to evidence, obtain approvals, and rehearse production launch/rollback.

## Included requirements

- Public coverage matrix finalized
- Named markets/merchants only if gates passed
- Disclosures: freshness, shipping/tax, affiliate, sponsored, AI, privacy/legal, support, status/incident
- Marketing/social/launch description review
- Final legal/security/ops approvals
- Go/no-go meeting recorded
- Rollback decision authority assigned
- Production launch rehearsal success
- Launch checklist prepared for sign-off
- Integrity certification (DealScore/neutrality monitoring on)
- Verify (do not implement) Sprint 37 shipping-honesty and unsupported-market public wording (P1-2 / P1-1B claims check)
- Verify (do not implement) that every market/merchant named in the coverage matrix has Sprint 32–36 capability-policy evidence: declared, evidence-backed, fail-closed enforced; omit/disable markets or providers lacking it rather than weakening the gate
- Verify, but do not implement, CC-01 Conversational Continuity on the frozen staging candidate.
- Verify that every conversational answer and research/loading claim maps to captured evidence or an actual execution record.
- Verify that session Recommendation refinement leaves canonical PiqScores unchanged.
- Verify affiliate neutrality across answers, refinement, alternatives, research, and updated Results.
- Verify the Product Foundation manifest and artwork checksums against the implemented Results, Compare, Why, overlay, mobile-sheet, research, and updated-Results states.

## Explicit non-goals

- Adding new markets during freeze
- Feature expansion

## External dependencies

- EXT-19
- EXT-20
- EXT-21

## Implementation deliverables

- Launch freeze flag
- Checklist automation updates if needed

## Documentation deliverables

- Signed approvals
- Approved claim sheet
- Rehearsal evidence
- Coverage matrix v1

## Required tests

- Release verification script: no fixture-as-live

## Required staging evidence

- Final staging candidate freeze

## Required production evidence

- Launch rehearsal on production window

## Acceptance criteria

- Legal/security/ops approvals recorded
- Claim matrix approved
- Named markets/merchants have capability-policy certification evidence (declared + evidence-backed + fail-closed enforcement); ungated providers omitted
- Rehearsal succeeds
- Rollback authority named
- CC-01 rehearsal succeeds on the frozen candidate with claims, integrity, neutrality, provenance, and visual-manifest evidence attached.
- No mock-only evidence is accepted for a state presented as live research.
- Any canonical PiqScore mutation, evaluated-set drift, affiliate influence, fabricated execution claim, or artwork checksum mismatch is a launch no-go.

### Additive PiqSavi public-brand / claims criteria (not marked complete)

Authority: [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)

- Public claims use PiqSavi
- No unintended public DealBrain product-brand leakage
- SEO metadata uses PiqSavi
- Open Graph/social metadata uses PiqSavi
- Structured-data organization/application name uses PiqSavi
- Approved logo/assets present
- DealScore terminology unchanged unless separately approved
- Legacy `x-dealbrain-*` compatibility decision finalized
- Public documentation brand reviewed
- Legal/marketing approval covers PiqSavi wording

## Predecessor sprints

27–43 as applicable, 32–36 for any market to be named

## Parallelizable work

None

## Go / no-go gate

Formal go/no-go

## Rollback or contingency

No-go delays Sprint 45

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
