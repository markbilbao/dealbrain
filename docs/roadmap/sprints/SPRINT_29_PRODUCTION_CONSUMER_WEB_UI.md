# Sprint 29 — Production Consumer Decision Experience & Conversational Continuity

**Filename retained** for link stability: `SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md`

**Status:** In progress — 29.0–29.4B, Product Foundation, economics, UUID presentation, and schema 1.2 are **merged**. Phase 29.4C is **implemented on branch** (proposal only; no live research). Sprint 29 is **not closed**.
**Primary owner / domain:** Frontend / product / conversational continuity
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-6 (public UX); CC-01; persistent Ask; SEO technical foundation
**Engineering baseline recorded:** `ab23d29e5f303bd5ecdfed60f7e7defe598d84d0` (2819 passed / 0 failed / 0 skipped / 168 warnings). This is not the final launch candidate and does not prove live merchant research.

## Objective

Deliver the production consumer **decision experience** and Results-bound Conversational Continuity through Ask PiqSavi, including accessibility, SEO technical foundation, and the conversational contract for proposal → confirmation → authorized research request — not a visual reskin of `demo.html` and not a second conversation, Results, Recommendation, or PiqScore system.

Frontend/accessibility responsibility is preserved. The sprint purpose is no longer only “Production Consumer Web UI & Accessibility.”

## Included requirements

### Current implementation record (truthful; not a close)

| Work | Status | Notes |
|------|--------|-------|
| 29.0 CC-01 contract freeze | merged | PR #83 |
| 29.1 Conversation domain | merged | PR #84 |
| 29.2 Conversation persistence | merged | PR #85 |
| 29.3 Canonical decision snapshots | merged | PR #86 — immutable snapshots, owner binding, evaluated-set authority, Recommendation authority, canonical PiqScores, evidence/provenance, unknowns, integrity verification, affiliate-neutrality preservation |
| Product Foundation | merged | PR #87 — Results, Compare, Why This Is the Best Piq for You, persistent Ask PiqSavi, desktop/mobile behavior, truthful price-state presentation, delivery/location UX, unknown/not-captured states, qualification presentation, truthful source/evidence behavior, no fixture claims in production UUID mode |
| 29.4A `answer_from_evidence` | merged | PR #88 — Ask can answer post-Recommendation questions using bounded existing evidence. It cannot research, add products, or modify Recommendation / PiqScore |
| Canonical offer economics | merged | PR #89 — listing price, verified discounts, verified vouchers where captured, shipping, taxes/duties, import costs, dominant price state, dominant amount, location context, structured unknowns, evidence/provenance, freshness where known; schema 1.0 compatibility preserved |
| Canonical UUID consumer presentation | merged | PR #90 — one canonical owner-bound UUID drives Results → Compare → Why → Ask PiqSavi with no fixture fallback for real UUID decisions |
| Canonical decision presentation contract | merged | PR #91 / schema 1.2 — Recommendation qualification, shopper decision context, product identity metadata, category-flexible product fit, Recommendation reasons, Best For, alternative trade-offs, outbound offer reference, integrity protection, Ask evidence support |
| 29.4B `refine_session_recommendation` | merged | Shopper may clarify preferences after Recommendation. Session Best Piq may change using already-evaluated products/evidence. PiqScore does not change. Canonical snapshot does not mutate. Original Recommendation remains historical. Evaluated set cannot expand. No new research. No affiliate influence. |
| 29.4C `propose_research` | implemented on branch | Detect when the shopper asks for evidence/product outside currently evaluated evidence. PiqSavi may propose additional research. Research does **not** automatically execute. User confirmation remains required. Execution remains Sprints 31–38. |

**Truthfulness rules already locked for presentation:**

- no brand/model inference from display name
- no universal headphone fit fallback
- qualification absent ≠ explicit unqualified
- do not claim live merchant research

**Intent sufficiency (locked):** Ask only when missing information could materially change the Recommendation. Otherwise, research first. Do not introduce long onboarding/questionnaire friction.

**Ask PiqSavi lock:** remains available after Recommendation on Results, Compare, and Why This Is the Best Piq for You. Recommendation is not the end of the shopping conversation.

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

### Research confirmation / handoff (Sprint 29 owns the conversational contract only)

Remaining Sprint 29 acceptance includes:

proposal
→ user confirmation
→ authorized research request

Actual **LIVE** research execution belongs to Sprints 31–38. Sprint 29 must not pretend merchant research exists before those dependencies are satisfied. `propose_research` does not imply research automatically executes.

### SEO technical foundation (Sprint 29)

- semantic HTML
- descriptive page metadata infrastructure
- canonical URL support
- index/noindex controls
- robots architecture
- sitemap architecture
- structured-data / JSON-LD infrastructure where truthful
- crawl-safe public URL architecture
- internal linking support for public pages

**Critical privacy rule:** Personalized decision/session pages such as canonical UUID Results/Compare/Why must remain private/non-indexable unless a separately designed public representation exists.

Private/personalized examples (`/results/{uuid}`, `/compare/{uuid}`, `/why-best-piq/{uuid}`) may contain shopper location, budget, priorities, personalized Recommendation, and session state. They must not become general search-index pages.

Public SEO surfaces, if later approved, may include `/product/...`, `/compare/...-vs-...`, `/best/...`, and category/budget buying guides. Publish/index only when content is supported by sufficiently trustworthy public evidence. No mass thin AI page generation.

Do **not** create a separate large pre-launch SEO sprint. Measurement is Sprint 39. Rehearsal is Sprint 44. Cutover is Sprint 45. Observation is Sprint 46.

### Frontend architecture (reconcile stale wording)

Production consumer frontend remains:

- FastAPI-served semantic HTML
- shared CSS
- native vanilla-JavaScript ES modules

Mandatory React, Next.js, Vite, TypeScript production build, SPA architecture, and Node production build are **not** required unless independently approved later.

### Search / Save / Watch and guest continuity

- Search / Ask = research/decision action
- Save = preserve a buying decision/context for later
- Watch = explicitly subscribe to future monitoring where that capability genuinely exists
- Do not silently turn Save into Watch
- Do not promise notifications before monitoring is operational
- Guest→account continuity must retain current decision context and Saved intent/state where safely possible
- Do not silently lose the decision because signup occurred

### Live decision creation (shared launch requirement)

Sprint 29 owns capture/presentation of the canonical snapshot and UUID consumer Results. Sprint 31 owns routing/eligibility. Sprint 38 owns live execution. Fixture-created UUIDs are not sufficient for Sprint 45.

### Market-selection interface (ownership split)

- **Sprint 29 owns** the accessible, responsive market-selection UI shell/component
- **Sprint 37 owns** MarketContext domain rules, supported-market data, persistence semantics, currency behavior, and final integration
- Explicitly distinguish UI-component ownership from domain-policy ownership

### Validation

- Responsive mobile web
- Accessibility baseline (keyboard, labels, contrast, focus)
- Supported-browser validation matrix
- Document-route / static-asset validation in CI (not a Node/React production build unless later approved)
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

- FastAPI document routes + semantic HTML + shared CSS + vanilla-JS ES modules
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
- Asset/size budget check appropriate to the FastAPI static consumer
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
- A11y baseline checklist signed; browser matrix recorded; CI validates the FastAPI HTML/CSS/vanilla-JS consumer
- UUID Results/Compare/Why are non-indexable; no fixture fallback for real UUID decisions
- Live merchant research is not claimed
- `propose_research` never executes research before explicit confirmation
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
