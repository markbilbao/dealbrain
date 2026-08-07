# Sprint 29 — Production Consumer Web UI & Accessibility

**Status:** Planned
**Primary owner / domain:** Frontend / product
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-6 (public UX)

## Objective

Deliver a production consumer web application covering the core shopping and account journey with accessibility and e2e baselines — not a visual reskin of `demo.html`.

## Included requirements

### Full shopping and account journey UI

- Registration, login, recovery, and email-verification state presentation
- Search → normalized results → DealScore → recommendation → AI explanation with deterministic fallback → merchant redirect
- Affiliate disclosure rendering
- Loading, empty, error, timeout, partial-result, stale-result, and unsupported-market states
- Account settings:
  - account information view
  - sign-out and session-management access
  - privacy and consent settings access
  - email/status presentation where supported
- Account deletion and data-export entry points:
  - UI can initiate the Sprint 28 deletion flow
  - UI can request/download the Sprint 28 export
  - confirmation, pending, success, and failure states
  - UI must not invent backend completion before Sprint 28 contracts exist
- Feedback, support, and bug-report entry points:
  - visible navigation or contextual actions
  - UI contract may initially target Sprint 39 interfaces
  - final integration cannot be considered complete until Sprint 39 services are available

### Market-selection interface (ownership split)

- **Sprint 29 owns** the accessible, responsive market-selection UI shell/component
- **Sprint 37 owns** MarketContext domain rules, supported-market data, persistence semantics, currency behavior, and final integration
- Explicitly distinguish UI-component ownership from domain-policy ownership

### Validation

- Responsive mobile web
- Accessibility baseline (keyboard, labels, contrast, focus)
- Supported-browser validation matrix
- Frontend production build validation in CI
- Unit/component tests
- End-to-end tests using non-live provider contracts where necessary
- Staging E2E after required backend dependencies (26/27/28 hooks) are available

## Explicit non-goals

- Native apps
- Full design-system expansion
- Merchant admin UI redesign
- Certifying live merchant data (32–36)
- Final MarketContext domain behavior (37)
- Completing Sprint 39 analytics/support backends (UI may stub to contract)

## External dependencies

- None critical (UI can progress against API contracts and fixtures labeled non-live)

## Implementation deliverables

- Frontend package + build pipeline
- Wired API client
- Account, privacy, deletion/export, feedback/support entry components
- Market-selection UI shell (domain wiring finalized in 37)
- State components for degradation

## Documentation deliverables

- UI journey map
- A11y baseline checklist
- Browser matrix
- Ownership note: UI shell (29) vs MarketContext policy (37)

## Required tests

- Component/unit as appropriate
- E2E happy path + key failure states (non-live contracts OK)
- Build size budget check
- A11y smoke

## Required staging evidence

- Full UI journey on staging after backend hooks available
- A11y smoke
- Deletion/export UI states exercised against Sprint 28 APIs when present

## Required production evidence

- Static asset hosting decision recorded for 41

## Acceptance criteria

- Staging e2e journey green for registration/login/recovery/verification-state, search→DealScore→recommendation→explanation→redirect, account settings, deletion/export entry points, and feedback/support entry points
- A11y baseline checklist signed; browser matrix recorded; CI validates production frontend build
- Unsupported-market and stale-data states do not present fixtures as live
- Market-selection UI shell present; domain/policy integration explicitly deferred to Sprint 37
- Sprint 29 does **not** certify live merchant data or final MarketContext behavior

### Additive PiqSavi public-brand criteria (primary implementation sprint; not marked complete)

Authority: [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)

- Public consumer application displays PiqSavi
- Tagline displayed where appropriate: Your AI Personal Shopper
- No unintended DealBrain branding in consumer-facing UI
- Title/meta/social/install surfaces use PiqSavi
- Approved PiqSavi logo assets used
- Favicon/PWA/social/email asset slots implemented from approved assets
- Canonical metadata uses `piqsavi.com`
- Staging pages are non-indexable
- Public brand boundary test passes
- Internal DealBrain identifiers remain operational
- DealScore remains DealScore
- No blanket internal rename occurs

Do not implement these items in documentation-only brand-lock tasks.

## Predecessor sprints

27, 28 (API hooks), 26

## Parallelizable work

31 platform design; 39 support API design; 37 MarketContext policy (UI shell can precede)

## Go / no-go gate

Go if staging e2e + a11y baseline pass for the production consumer app surfaces above

## Rollback or contingency

Keep API invite-only; disable public UI route

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
