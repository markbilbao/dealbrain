# Sprint 29 — Production Consumer Web UI & Accessibility

**Status:** Planned
**Primary owner / domain:** Frontend / product
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-6 (public UX)

## Objective

Deliver a production consumer web application covering the core shopping and account journey, including Results-bound Conversational Continuity through Ask PiqSavi, with accessibility and end-to-end baselines — not a visual reskin of `demo.html` and not a second conversation, Results, Recommendation, or PiqScore system.

## Included requirements

### Full shopping and account journey UI

- Registration, login, recovery, and email-verification state presentation
- Search → normalized results → PiqScore → recommendation → AI explanation with deterministic fallback → merchant redirect
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

### Conversational Continuity

- Extend the existing `ConversationRepository` / `ConversationContext` architecture; do not create a second conversation system.
- Treat canonical Results, Recommendation, and PiqScore services as the only scoring and result authority.
- Search creates a server-owned decision context containing the exact evaluated set, canonical PiqScores, Recommendation, Best Piq, alternatives, evidence, provenance, freshness, unknowns, and version.
- Ask PiqSavi remains available on Results, Compare, and Why This Is the Best Piq.
- Each follow-up must resolve to exactly one action:
  - answer from existing evidence
  - refine the session Recommendation over the same evaluated set
  - propose new research because the existing evidence is insufficient
- New research requires explicit user confirmation before execution.
- Loading, partial, stale, completed, failed, cancelled, merchant, price, review, and freshness statements must be derived from actual execution evidence.
- Completed research atomically creates updated canonical Results and retains the active conversation.
- Guest users receive server-bound session continuity across navigation, close/reopen, mobile sheet use, and guest→authenticated transition.
- Session priorities remain separate from persistent account preferences unless the user explicitly saves them.
- Session Recommendation refinement must not modify canonical PiqScore values or semantics.
- Affiliate commission and partner economics remain post-selection and cannot influence answers, refinement, alternatives, research, canonical scores, or organic ordering.
- Implement the approved Product Foundation artwork exactly under its owner-approved manifest; desktop insertion height is 80 px and mobile insertion height is 72 px.

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
- Canonical decision-context API contract using the existing conversation architecture
- Shared guest-capable decision-context persistence adapter
- Ask PiqSavi insertion bar for Results, Compare, and Why This Is the Best Piq
- Reusable desktop conversation overlay and mobile conversation sheet
- Evidence-answer, session-refinement, research-proposal, confirmation, execution-state, and updated-Results UI
- Guest continuity and guest→authenticated transition behavior

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
- Minimum 20 explicit Conversational Continuity behavior tests
- Stable evaluated-set regression coverage across follow-up questions
- Canonical PiqScore immutability during session Recommendation refinement
- Results/Compare/Why context-equivalence tests
- Guest continuity, expiry, cleanup, restart, multi-worker, and auth-transition tests
- Research confirmation, idempotency, truthful status, partial/failure, and updated-Results tests
- Affiliate-neutrality regression coverage across every conversational action
- Desktop/mobile visual regression against the approved Product Foundation manifest
- Mobile keyboard, safe-area, focus, composer, close/reopen, and accessibility coverage

## Required staging evidence

- Full UI journey on staging after backend hooks available
- A11y smoke
- Deletion/export UI states exercised against Sprint 28 APIs when present

## Required production evidence

- Static asset hosting decision recorded for 41

## Acceptance criteria

- Staging e2e journey green for registration/login/recovery/verification-state, search→PiqScore→recommendation→explanation→redirect, account settings, deletion/export entry points, and feedback/support entry points
- A11y baseline checklist signed; browser matrix recorded; CI validates production frontend build
- Unsupported-market and stale-data states do not present fixtures as live
- Market-selection UI shell present; domain/policy integration explicitly deferred to Sprint 37
- Sprint 29 does **not** certify live merchant data or final MarketContext behavior

### Conversational Continuity acceptance criteria — CC-01 primary owner

Authority:

- [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md), EC-02 / EC-22 / CC-01
- [`../evidence/PIQSAVI_CONVERSATIONAL_CONTINUITY_PRODUCT_FOUNDATION_MANIFEST.md`](../evidence/PIQSAVI_CONVERSATIONAL_CONTINUITY_PRODUCT_FOUNDATION_MANIFEST.md)

Acceptance requires all of the following:

1. The existing `ConversationRepository` / `ConversationContext` architecture is extended; no second conversation subsystem is introduced.
2. Canonical Results, Recommendation, and PiqScore services remain the only scoring and result authority.
3. Search creates a server-owned decision context containing the exact evaluated set, canonical PiqScores, Recommendation, Best Piq, alternatives, evidence, provenance, freshness, unknowns, and context version.
4. Guest users can complete:

   Search
   → Results
   → Ask PiqSavi
   → contextual answer from the same evidence
   → second follow-up
   → optional session Recommendation refinement
   → optional research proposal
   → explicit research confirmation
   → truthful research/loading
   → updated Results
   → Ask PiqSavi remains available

5. Equivalent contextual entry, close/reopen, and continuation work from Results, Compare, Why This Is the Best Piq, and the mobile conversation sheet.
6. Questions answerable from captured evidence do not invoke marketplace research or imply new execution.
7. Session Recommendation refinement operates only over the current evaluated set and leaves every canonical PiqScore byte-for-byte unchanged.
8. Session priorities remain scoped to the active decision and are not written to persistent account preferences without explicit user action.
9. Research is proposed only when existing evidence is insufficient and never begins before explicit confirmation.
10. Research confirmation is idempotent and starts exactly one real execution.
11. Loading, partial, stale, completed, failed, cancelled, merchant, offer, price, review, freshness, and coverage statements are backed by actual execution evidence.
12. Completed research atomically returns a new canonical Results snapshot while retaining the conversation and Ask PiqSavi availability.
13. Failed, partial, cancelled, or insufficient-evidence outcomes preserve the last valid decision and do not fabricate an answer or execution.
14. The evaluated product set remains stable across follow-up questions unless the user explicitly requests or approves new research.
15. A locked regression test reproduces the observed defect: the initial comparison contains iPhone 17 Pro Max and Samsung Galaxy S25 Ultra 512GB; after “Which one has better battery?”, Samsung must not be replaced by Google Pixel 9 128GB or any other product unless the user explicitly requests or approves new research.
16. Full bounded user and assistant turn history is retained for the active session.
17. Guest continuity survives navigation and permitted close/reopen behavior; expiry, deletion, logout, shared-device isolation, restart, and multi-worker behavior are proven.
18. Guest→authenticated transition validates both principals, rotates ownership credentials, preserves the active decision, and does not expose it to another user.
19. Affiliate commission, partner priority, and conversion value do not affect candidate inclusion, canonical PiqScores, answers, priorities, alternatives, session refinement, research decisions, or organic ordering.
20. Results, Compare, Why This Is the Best Piq, desktop overlays, mobile sheets, research states, and updated-Results states match the approved Product Foundation manifest without modifying the underlying artwork.
21. Desktop Ask insertion height is exactly 80 px; mobile Ask insertion height is exactly 72 px.
22. Accessibility covers dialog/sheet semantics, keyboard navigation, focus trap and restoration, Escape/close, live announcements, reduced motion, zoom, screen-reader labels, mobile safe areas, and keyboard-open composer visibility.
23. At least 20 explicit Conversational Continuity behavior tests are present, including canonical-authority, context-drift, refinement, research, security, affiliate-neutrality, persistence, mobile, visual, and accessibility coverage.
24. The complete CC-01 staging journey passes on the immutable launch-candidate digest.

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
- Consumer UI uses PiqScore for the score feature
- Internal DealScore technical contracts remain unchanged (`deal_score` fields, `/dealscore` paths, protected DealScore engine)
- No public leakage of DealScore as the consumer feature name except where deliberately exposed as an API/schema machine identifier
- Personalized PiqScore is the preferred display for PersonalDealScore where user-visible
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
