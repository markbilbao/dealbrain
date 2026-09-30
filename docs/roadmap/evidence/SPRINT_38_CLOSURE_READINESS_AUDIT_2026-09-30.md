# Sprint 38 closure-readiness audit — 2026-09-30

**Audit verdict:** SPRINT 38 IN PROGRESS — TRUE SPRINT 38 ENGINEERING BLOCKERS REMAIN

**Sprint closure status:** IN PROGRESS. Not COMPLETE / CLOSED.

**Engineering status:** IN PROGRESS. `SPRINT_38_ENGINEERING_STATUS` is `IN PROGRESS`.

**Correction before merge:** The first draft of this audit, on `7b8b0421daeb2a5ea7869f28ef046459c9727c00`, called engineering complete and set Class B count to 0. That conclusion is withdrawn. The shopper call graph stops at `prepare_confirmed_research` / `prepared_unavailable`. It does not call `LiveStartClaimService` or `ShopifyCatalogExecutionService`. `execute_production_shopify_catalog` still discards the supplied transport and returns `production_execution_not_wired` even when the other block reasons would be empty. Sprint 41 lists "Domain engine changes" as an explicit non-goal, so that missing application and domain composition is Sprint 38 engineering.

**This audit does not close Sprint 38.** It reconciles two requirement eras in the sprint document. The 2026-09-26 PH-only scope, the Sprint 32 and Sprint 37 close records, and the Sprint 41 / 42 / 44 / 45 definitions supersede the original Sprint 38 acceptance template where they conflict on multi-connector chaos, probes, and paging. They do not remove the current contract that confirmed research uses the certified path and that completed research returns a canonical updated Results snapshot. The original template is retained in the sprint document and labeled historical for the superseded sentences only.

**Starting `main`:** `2f69f106b08a4fd343e609519efd6a24b2b0e050`

**Sprint definition:** [`../sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md`](../sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md)

No Shopify call was made. No flag was enabled. No deploy was performed. Sprint 32 validation was not rerun. Sprint 41 and Sprint 42 were not started.

---

## Meanings that stay separate

| Meaning | Current value | What would make it true |
|---------|---------------|-------------------------|
| ENGINEERING COMPLETE | No | Positive shopper composition and validated-outcome-to-canonical-Results plumbing are still missing |
| SPRINT COMPLETE / CLOSED | No | Every current Sprint 38-owned acceptance criterion is satisfied, including the real validation that this audit leaves blocked |
| LIVE OPERATIONAL | No. `LIVE_RESEARCH_EXECUTION_OPERATIONAL` is False | A real certified connector attempt is permitted and has run under the production gates |
| PRODUCTION DEPLOYED | No | Sprint 41 production environment, deploy/rollback evidence, and the production UCP profile |
| LAUNCH READY | No | Sprint 44 claims approval and Sprint 45 exit criteria, including a useful certified PH shopping market |

Fake-transport adapter tests are engineering evidence. They are not live evidence, not a production drill, and not launch approval.

The 2026-09-26 slice used the letters A–G for a different classification. This audit's letters are the closure-readiness classes below. They replace that slice list for closure reading.

| Class | Meaning |
|-------|---------|
| A | Already satisfied by Sprint 38 engineering |
| B | True remaining Sprint 38-owned work that can be completed now without Sprint 41 or Sprint 42 |
| C | Sprint 38 validation blocked on Sprint 41 production or deployment prerequisites |
| D | Sprint 42 operations, probes, or paging work |
| E | Sprint 44 / 45 claims or launch-validation work |
| F | Not applicable to the current one-connector PH beta; preserved as future multi-connector scope |
| G | Historical or superseded wording, retained as history and labeled historical |

**Class B count: 2.** Both items can be engineered behind the existing closed gates. This audit does not implement them.

| Id | Requirement | Why it is Sprint 38 |
|----|-------------|---------------------|
| B1 | Positive production shopper execution composition | A confirmed request must be able to continue from durable preparation to the live-start claim, authorization consumption, and the Shopify adapter when every production gate is true. Today the chain stops earlier. |
| B2 | Successful live outcome → durable evidence reference → canonical updated Results | The adapter stores `normalized_offer_digests` and leaves `evidence_ids` empty. No resolvable evidence record is written, and no canonical updated Results snapshot is produced. The shopper path does not consume a successful outcome. |

---

## Production truth recorded by this audit

| Fact | Value |
|------|-------|
| Provider `ph-shopify-global-catalog` | DISABLED |
| Production routing policies | 0 |
| Public certified shopping markets | 0 |
| Production UCP profile | undeployed. `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` is False |
| `SHOPPING_RESEARCH_EXECUTION_MODE` | `disabled` |
| `SHOPIFY_LIVE_CALL_PERMITTED` | False |
| `LIVE_RESEARCH_EXECUTION_OPERATIONAL` | False |
| `DESTINATION_REEVALUATION_IMPLEMENTED` | False |
| `SPRINT_38_STATUS` | IN PROGRESS |
| `SPRINT_38_ENGINEERING_STATUS` | IN PROGRESS |
| `SPRINT_38_LIVE_EXECUTION_STATUS` | NOT OPERATIONAL |
| Sprint 41 | UNSTARTED |
| Real Shopify calls in the adapter | 0 |
| `SHOPIFY_PERSISTENT_CACHE_ALLOWED` | False |

---

## Requirement matrix

| Requirement | Current evidence | Owner | Class | Current status | Closure effect | Downstream dependency |
|-------------|------------------|-------|-------|----------------|----------------|------------------------|
| Execution identity from the server authorization key; repeated confirmation reuses one execution | `prepare_confirmed_research` and durable `research.authorized_executions`; authorization-handoff and durable-execution tests | Sprint 38 | A | Satisfied | Does not block engineering completion | None for this contract |
| Fail-closed live-mode gate for one exact market, capability, and source | `assess_live_research_mode`; production assessment stays closed | Sprint 38 | A | Satisfied | Does not block engineering completion | Opening the gate is an operational act, not this contract |
| Truthful non-live preparation trace; shopper told execution is unavailable and no source was checked | Preparation projects an empty authoritative trace; confirmation copy stays non-live | Sprint 38, with Sprint 29 presentation | A | Satisfied for the non-live path | Does not block engineering completion | Live disclosure copy is E after a real attempt exists |
| Shopify execution refusal with no HTTP on the production entry | `execute_production_shopify_catalog` deletes the transport and returns block reasons | Sprint 38 | A | Satisfied | Does not block engineering completion | None |
| Scripted timeout, 429, 5xx, credential, retry, and kill-switch behavior | `tests/unit/test_sprint38_live_execution.py` | Sprint 38 | A | Satisfied as non-live scripted evidence | Does not block engineering completion | Scripted tests are not live chaos |
| In-memory scripted breaker | `ScriptedConnector.circuit_breaker` | Sprint 38 | A | Satisfied as chaos-test state only | Does not block engineering completion | Not the production breaker |
| Repository-backed breaker: closed, open, half-open; three breaker-worthy failures open it | `research.provider_reliability`; reliability-state tests | Sprint 38 | A | Satisfied as repository behavior | Does not block engineering completion | Not live-validated and not a deployed row |
| Breaker-worthy categories are timeout, unavailable, and unknown; rate limit, quota, credential, kill switch, circuit-open, and partial do not open it | Reliability policy and adapter failure tests | Sprint 38 | A | Satisfied | Does not block engineering completion | None |
| HALF_OPEN single-probe lease, 30 seconds, one probe per provider and market | `HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED`; live-start and adapter tests | Sprint 38 | A | Satisfied as a lease, not a synthetic production probe | Does not block engineering completion | Do not treat this lease as a Sprint 42 probe |
| Durable live-start claim and compare-and-swap recovery | `DURABLE_LIVE_START_CLAIM_IMPLEMENTED` | Sprint 38 | A | Satisfied | Does not block engineering completion | Current production cannot claim |
| Authorization consumption in the successful claim transaction | `AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM` | Sprint 38 | A | Satisfied | Does not block engineering completion | A failed gate leaves the authorization pending |
| Shopify adapter: 5-second timeout, retry 0, authoritative trace, durable outcome, breaker update, claim release | `app.research.shopify_global_catalog_execution`; adapter tests use a fake transport | Sprint 38 | A | Satisfied for injected transport | Does not block engineering completion | Fake results stay `synthetic` and are not `SourceMode.LIVE` |
| Timeout, HTTP 429, HTTP 5xx, connection unavailable, malformed JSON-RPC, normalization refusal | Adapter classification and `test_failure_traces_and_breaker_policy` | Sprint 38 | A | Satisfied on fake transport | Does not block engineering completion | Not a live Shopify call |
| `outcome_unknown` after an ambiguous post-HTTP crash, without replay and without breaker success or failure | `reconcile_ambiguous` | Sprint 38 | A | Satisfied | Does not block engineering completion | None |
| Kill switch stronger than a closed breaker; disengaging it does not make DISABLED live | `assess_execution_permission` | Sprint 38 | A | Satisfied at code and repository level | Does not block engineering completion | Deployed drill is C |
| Provider DISABLED blocks execution | Production descriptor and adapter pre-transport check | Sprint 38 behavior; Sprint 32 registered the disabled provider | A | Satisfied | Does not block engineering completion | Activation is not Sprint 38. See sequencing |
| No merchant available for the one disabled or failed connector | One-connector aggregate and `NO_MERCHANTS_DISCLOSURE` | Sprint 38 | A | Satisfied | Does not block engineering completion | Not a multi-merchant partial result |
| Prior canonical decision preserved on failure, partial, and `outcome_unknown` | Adapter result forbids replacement today, including on fake success | Sprint 38 | A for the refusal. The positive success path is B2 | Refusal exists. Success integration does not | B2 blocks engineering completion | Real live evidence that fills the success path is C |
| `/ready` independent of merchant availability | Reliability and live-execution readiness tests | Sprint 38, reusing Sprint 22 | A | Satisfied | Does not block engineering completion | None |
| Health facts stay distinct: certified, operationally available, healthy, merchant availability, live | `ResearchProviderHealth` | Sprint 38 | A | Satisfied | Does not block engineering completion | Healthy still requires a recorded successful attempt. Live stays false |
| Fixture and synthetic paths are not labeled live | Adapter rejects `observation_kind == live` and `SourceMode.LIVE` for fake success | Sprint 38 | A | Satisfied | Does not block engineering completion | Sprint 45 release check remains E |
| Query-time Shopify policy: no persistent cache and no persistent product index | `SHOPIFY_PERSISTENT_CACHE_ALLOWED` is False; `admit_shopify_catalog_cache` refuses | Sprint 38, under the Sprint 32 certified policy | A | Satisfied by explicit refusal | Does not block engineering completion | Do not add a cache to satisfy the old stale-cache sentence |
| Fail-closed production composition refusal | `execute_production_shopify_catalog` discards the transport. Empty gate reasons still return `production_execution_not_wired` | Sprint 38 | A for the refusal. The missing positive branch is B1 | Refusal exists. Positive branch does not | B1 blocks engineering completion | Real HTTP execution remains C |
| Real Shopify owner validation | Not run. Real calls stay 0. Sprint 32 harness was not rerun | Sprint 38 validation, blocked | C | Pending | Blocks COMPLETE / CLOSED and LIVE OPERATIONAL. Does not remove the Class B engineering work | Requires routing, operational eligibility, and the Sprint 41 production UCP profile together. Also requires the explicit live switch. None of those are true |
| B1. Positive production shopper execution composition | `ShoppingAssistantService` → `ProposeResearchService` → `prepare_confirmed_research` → `prepared_unavailable`. No call to `LiveStartClaimService` or `ShopifyCatalogExecutionService`. Adapter `execute` requires `BoundedFakeTransportPermit` | Sprint 38 engineering. Sprint 41 supplies environment, profile, and deployment only | B | Not implemented. Not implemented in this audit | Blocks engineering completion. Does not require a Shopify call to build or to test behind closed gates | Real execution of that branch, once the gates are true, is C |
| Deployed operational kill-switch drill | Engineering test exists on the real descriptor in memory and in repository permission checks. No deployed drill | Sprint 41 for the deployed drill. Sprint 38 engineering behavior is A | C | Pending as deployed evidence | Blocks launch operations evidence. Does not block engineering completion | Sprint 41 production deploy. Code tests are not this drill |
| Production UCP profile `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` | Undeployed. Sprint 32 recorded HTTP 404 on 2026-09-23 | Sprint 41 | C | Undeployed | Blocks real Shopify validation. Not missing Sprint 38 engineering | Sprint 41 deploy and owner HTTPS validation |
| Production AWS, DNS, TLS, secrets, deploy, and rollback | Not in this audit | Sprint 41 | C | UNSTARTED | Blocks production deployment | Sprint 41. Predecessor recommendation is Sprint 40 |
| B2. Successful validated outcome → durable evidence reference → canonical updated Results | No shopper-path consumer of a successful outcome. Trace `evidence_ids` stay empty. `normalized_offer_digests` are not evidence ids. No new canonical decision is written. Searched `app/` for an integration from a Shopify execution outcome into a canonical snapshot and did not find one | Sprint 38 engineering. Sprint 29 owns snapshot presentation and does not perform this integration | B | Not implemented. Not implemented in this audit | Blocks engineering completion | Real resolvable live evidence is C. A later fixture test of the plumbing must not be recorded as production live evidence. Fake transport output must not become a shopper-visible canonical live decision |
| Live evidence-backed destination re-evaluation | `DESTINATION_REEVALUATION_IMPLEMENTED` is False. Assessment returns `required_unavailable` and preserves the prior decision | Sprint 37 owns the fail-closed contract. A live shipping executor is not available on the reduced certified set | Dependent / fail-closed. Not Class B | Stays False | Does not join the Class B count. Must not be flipped true in this audit | Shipping is uncertified. Unknown shipping stays unknown. A later live executor still cannot invent destination shipping from the reduced capability set |
| Synthetic production probes, including the old “Probes green” sentence | Not implemented. The HALF_OPEN lease is not a production probe | Sprint 42 | D | Not started | Does not block Sprint 38 engineering or this beta's Sprint 38 closure checklist | Sprint 42 after Sprint 41 |
| Production alerts, paging, and alert-routing evidence | Not implemented. Sprint 38 slices explicitly did not add destinations | Sprint 42 | D | Not started | Does not block Sprint 38 engineering completion | Sprint 42. The template sentence “Alerts routed in 42” is D, not a Sprint 38 hole |
| Incident runbook consolidation, RB-connector, restore, and incident operational evidence | Not in this audit | Sprint 42 | D | Not started | Does not block Sprint 38 engineering completion | Sprint 42 |
| AI-provider monitoring | Not a PH catalog connector behavior | Sprint 42 monitoring. Sprint 13 already owns assistant fallback | D | Not a Sprint 38 connector gap | Does not block this closure reading | Optional EXT-25 quota is Sprint 43 if an AI explanation claim needs it. EXT-25 does not block this beta |
| Public naming of PH as a certified shopping market | Catalog stays empty. Copy remains the preparing-coverage sentence | Sprint 44, then Sprint 45 | E | Not activated | Does not block Sprint 38 engineering completion | Claims approval, then launch |
| Live shopper canonical decision from certified evidence, as a launch claim | Not created | Sprint 45 verifies. Sprint 38 would supply the live execution. Sprint 29 presents the snapshot. Sprint 31 routes | E | Not launch-ready | Blocks launch. Does not block Sprint 38 engineering completion | C, then E |
| CC-01 updated-Results and degradation claims on the frozen candidate | Not re-run here | Sprint 44 rehearsal and Sprint 45 EC-02 / EC-22 | E | Pending | Blocks launch | A frozen candidate after live research exists |
| Fixture-as-live release verification | Engineering guard exists | Sprint 45, with Sprint 18 and Sprint 38 | E | Engineering guard satisfied; launch check pending | Does not block Sprint 38 engineering completion | Sprint 45 |
| Multi-connector live chaos drill | Not run. One certified connector exists. Scripted multi-provider tests are not live connectors | Future, when more than one certified connector exists | F | Not applicable to this beta | Does not block Sprint 38 closure for the PH one-connector beta | A later connector certification. Do not invent a second connector |
| Cross-merchant partial-result orchestration as a live shopper claim | Scripted partial copy says it is not a live multi-merchant result. One connector failing is no-merchants-available | Future multi-connector scope | F | Not applicable to this beta | Does not block this beta | Another certified connector |
| Aggregated health and kill-switch evidence across multiple live connectors | The aggregate formula is tested, including a deterministic two-provider case that is not live evidence | Formula is A. Live multi-connector evidence is F | F for the live claim | Formula satisfied; live multi-connector evidence not applicable | Does not block this beta | Future connectors |
| Production evidence across multiple connectors and markets | One disabled PH provider | Future | F | Not applicable | Does not block this beta | Sprints 33–36 only if the owner expands markets |
| Reliability consistency review signed across all certified connectors | One certified connector. Its reduced set is already certified and disabled | Future when more connectors exist | F | Not a current closure blocker | Does not block this beta | Additional certified connectors |
| Affiliate-provider failure behavior | Affiliate monetization is out of this beta | Not a Sprint 38 closure item | F | Not applicable | Does not block this beta | Later affiliate activation, if any |
| Original acceptance sentences for multi-connector chaos, probes green, and the aggregated-health live drill | Superseded for this one-connector beta | Historical template | G | Labeled historical in the sprint document | Must not be used as the current closure checklist | Reclassified F and D above |
| Original and current contract: confirmed research uses the certified path, provenance-backed execution states, and a canonical updated Results snapshot, while failure or partial research preserves the prior decision | The pieces exist separately. The shopper path does not connect them | Sprint 38 | B, as B1 and B2 | Not satisfied | Blocks engineering completion | Real live evidence remains C. Launch wording remains E |
| Original go/no-go: “Go if multi-connector chaos + aggregated health + kill switch evidenced” | Superseded for this beta | Historical template | G | Labeled historical | Must not be the current go line | Current no-go is the Class B wiring plus the Class C live validation |
| 2026-09-26 slice letters A–G inside the sprint document | Different letter meanings | Historical slice note | G | Superseded for closure reading by this audit | Do not mix those letters with this matrix | None |

---

## Answers to the ownership questions

### 1. Multi-connector chaos

Multi-connector live chaos is not a Sprint 38 closure requirement for this beta. The current public beta has one certified connector, `ph-shopify-global-catalog`. The 2026-09-26 PH-only scope already preserved multi-connector chaos as future scope. The original acceptance sentence that requires the drill is historical. Scripted multi-provider tests remain allowed and are not live evidence. No second connector is added.

### 2. Probes, alerts, and paging

Production alerts, paging, synthetic production probes, and incident operational evidence belong to Sprint 42. “Probes green” is not a Sprint 38-owned closure blocker. The HALF_OPEN single-probe lease is a concurrency control on the breaker row. It is not a synthetic production probe.

### 3. Production UCP profile

Deployment and owner HTTPS validation of the production profile belong to Sprint 41. This audit does not deploy it. Real Shopify validation that needs that profile is blocked on Sprint 41. It is not missing Sprint 38 engineering.

### 4. Real Shopify call

A real Shopify owner validation is Class C. It stays pending, and this audit does not call Shopify. It cannot run now: routing is 0, the provider is DISABLED, the production profile is undeployed, and live mode is disabled.

That pending validation does not make the missing shopper composition Class C. Sprint 38 engineering is not complete while B1 and B2 remain. The sprint stays IN PROGRESS and is not COMPLETE / CLOSED. Real execution validation remains blocked until Sprint 41. The engineering implementation of the positive branch does not wait for Sprint 41.

### 5. Routing and provider activation

| Step | Owner | Current state | May Sprint 38 flip it to close? |
|------|-------|---------------|---------------------------------|
| Routing model | Sprint 31 | Implemented | No |
| Production routing policies | Not Sprint 38 | 0 | No. A live route is operational activation after the Sprint 41 profile exists |
| Provider registration and DISABLED status | Sprint 32 | DISABLED | No |
| Provider operational activation to a live-eligible status | After Sprint 41 production environment and production profile | DISABLED | No. Activation is not a Sprint 38 engineering task |
| Public PH shopping-market activation | Sprint 44 claims, then Sprint 45 | 0 certified markets | No |

### 6. Destination re-evaluation

This is not an independent Sprint 38 engineering gap. `assess_destination_reevaluation` already returns `required_unavailable` and preserves the prior decision. `destination_reevaluation_execution_connected()` stays false until the live flag, live mode, and live operational flag are all true. Those flags must stay false. Shipping, tax, and import are not in the reduced certified set, so a later live product/offer/price/availability call still cannot honestly re-evaluate destination shipping. Unknown shipping stays unknown. The flag stays False.

### 7. Canonical updated Results

The current Sprint 38 contract still requires completed research to return a canonical updated Results snapshot. It still requires failed or partial research, and `outcome_unknown`, to leave the prior valid decision in place.

The refusal half exists and is Class A. The success half does not, so it is B2. The adapter persists `normalized_offer_digests`. Trace `evidence_ids` stay empty. No resolvable live evidence repository record is written. No canonical updated Results snapshot is produced. The shopper path does not consume a successful live outcome. A search of `app/` found no integration from a Shopify execution outcome into a canonical snapshot. Sprint 29 owns snapshot presentation and does not perform this integration.

Real evidence validation stays downstream and must not be fabricated. A later implementation may use deterministic repository fixtures to test the plumbing. Those tests must not be recorded as production live evidence. Fake Shopify transport output must not become a shopper-visible canonical live decision. Failure, partial, and `outcome_unknown` continue to preserve the prior decision.

### 8. Ask PiqSavi chain

Connected today:

1. Ask PiqSavi creates a proposal.
2. Explicit confirmation creates one server `ResearchAuthorization`.
3. Sprint 31 planning uses that authorization. Browser market, capability, source, and provider values cannot replace the plan.
4. Durable preparation writes `prepared_unavailable` on `research.authorized_executions`.
5. The shopper answer says execution is not available and no source was checked.
6. The authoritative trace stays empty. The authorization stays `authorized_pending_execution`.

Implemented, and not composed into that shopper request:

7. Live-start claim.
8. Authorization consumption, which happens only inside a successful claim.
9. Shopify execution adapter, which runs only with `BoundedFakeTransportPermit` and an injected transport.
10. Authoritative trace and durable outcome on that adapter path.
11. `execute_production_shopify_catalog`, which always refuses and never calls the transport.

Not connected:

12. Evidence-repository records for a validated observation.
13. A new canonical Results snapshot.
14. Destination re-evaluation against a live executor.
15. Production UCP profile, routing, provider operational eligibility, public market activation, and the live switch.

When every production gate is genuinely true, a confirmed Ask PiqSavi research request must be able to continue:

proposal → explicit confirmation → authorization → trusted Sprint 31 plan → durable preparation → live-start claim → authorization consumption → Shopify execution adapter → durable trace and outcome.

Today that chain stops after durable preparation. The missing continuation from step 6 to steps 7–10 is B1. The missing continuation from a validated successful outcome to a durable evidence reference and a canonical updated Results snapshot is B2. Destination re-evaluation stays fail-closed. The production profile, routing, provider activation, public market, and live switch stay Class C or E.

Adapter implemented is not production composition wired.

### 9. Production composition

The ownership is split. Executable production composition is not wholly Class C.

Sprint 38 engineering implements the positive application and domain composition behind the existing gates. It connects the shopper path to the live-start claim and the Shopify adapter only when those gates pass. That branch is fully testable without live HTTP. It does not enable the provider, routing, or live mode, and it does not deploy or call Shopify. `execute_production_shopify_catalog` currently discards the supplied transport and returns `production_execution_not_wired` even when the other block-reason list would be empty. Closing that positive branch is B1. This audit does not implement it.

Sprint 41 provides the real production environment, deploys the production UCP profile, and makes production validation possible. Sprint 41 lists "Domain engine changes" as a non-goal, so Sprint 41 cannot own this composition.

Real execution validation remains Class C and stays blocked until Sprint 41. Engineering implementation does not need to wait for Sprint 41.

### 10. Kill switch

| Layer | Status | Evidence |
|-------|--------|----------|
| Code-level behavior | Satisfied | Kill switch blocks before the breaker. Browser input cannot disengage it |
| Repository-backed permission | Satisfied | A claim consults the persisted breaker together with provider status and the kill switch. This is not a deployed drill |
| Deployed operational drill | Not done | Sprint 41, after a production deploy. Sprint 32's “Sprint 38/41” wording is reconciled to this split |

### 11. One-connector degradation cases

These engineering cases exist for the one PH connector: timeout, 429, 5xx, connection unavailable, malformed response, normalization refusal, breaker open threshold, HALF_OPEN success and failure, kill switch, provider disabled, no merchant available, prior-decision preservation, truthful trace on an injected attempt, `outcome_unknown`, and application readiness independent of merchant availability. They are class A. They are not live operational evidence.

### 12. Stale cache, fallback, and refresh

The old acceptance sentence is satisfied by the explicit no-cache / query-time policy. Shopify Anonymous catalog mode forbids persistent cache admission and a persistent product index. There is no stale cache to refresh. Re-query is the freshness rule. Adding a cache would weaken the certified policy. This is class A, not a gap, and not class B.

---

## Class B review

Class B count is 2. This audit does not implement either item.

| Id | Remaining Sprint 38 engineering | Why it can be finished without Sprint 41 |
|----|---------------------------------|------------------------------------------|
| B1 | Positive production shopper execution composition | The claim service and the adapter already exist. The shopper path stops at `prepare_confirmed_research`. Connecting them behind the closed gates does not require a live HTTP call |
| B2 | Successful validated outcome → durable evidence reference → canonical updated Results | The adapter stores digests and leaves `evidence_ids` empty. Writing a resolvable evidence reference and a canonical updated snapshot, and preserving the prior decision on failure, partial, and `outcome_unknown`, is application work. Real evidence is not fabricated here |

These candidates stay outside Class B:

| Candidate | Classification |
|-----------|----------------|
| Real Shopify owner validation | C. Blocked until the Sprint 41 production profile, routing, and operational eligibility exist together |
| A real call through `UrllibJsonTransport` | C. The positive composition may accept an injected transport behind the gates. A real HTTP call stays Class C |
| Production UCP profile and the deployed kill-switch drill | C. Sprint 41 |
| Flip `DESTINATION_REEVALUATION_IMPLEMENTED` | Dependent and fail-closed. Shipping is uncertified. Unknown shipping stays unknown |
| Production probes, alerts, paging, and incident operations | D. Sprint 42 |
| Public PH market activation, launch claims, and launch rehearsal | E. Sprint 44 / 45 |
| Multi-connector live chaos and cross-merchant live aggregation | F for this one-connector PH beta |
| A new durable `cancelled` execution state | Pre-start cancellation already cancels the authorization and does not start research. Not a Class B item in this audit |

A later B1 or B2 implementation may use deterministic repository fixtures. Those tests are not production live evidence. Fake transport output must not become a shopper-visible canonical live decision.

---

## Sequencing after this audit

Do not treat Sprint 38 engineering as complete. Do not move on by claiming that it is already done.

Next primary Sprint 38 task: one final bounded engineering slice.

Scope:

1. Positive Ask PiqSavi → claim → adapter composition behind closed gates.
2. Successful validated outcome → durable evidence reference → canonical updated Results integration.
3. Failure, partial, and `outcome_unknown` preserve the prior decision.
4. No real Shopify call.
5. Production flags remain closed.

After that slice, repeat the Sprint 38 closure-readiness audit.

| Sprint | Dependency that matters here | Recommendation |
|--------|------------------------------|----------------|
| 38 | B1 and B2 remain. Real Shopify validation still needs Sprint 41 | Do the bounded slice above, then repeat this audit. Leave the sprint IN PROGRESS until that later audit says otherwise |
| 39 | Predecessors are Sprint 28 and Sprint 29. Parallel with Sprint 40 | Sprint 39 may still run in parallel. Do not justify it by calling Sprint 38 engineering complete. It must not become a disguised Sprint 38 implementation |
| 40 | Predecessors are Sprint 27, Sprint 28, and Sprint 29. Parallel with Sprint 39 | May run in parallel, as already documented |
| 41 | Predecessor recommendation is Sprint 40. Non-goal: domain engine changes | Supplies the production environment, the production UCP profile, deployment, and the conditions for production validation. Does not own B1 or B2. Do not start Sprint 41 implementation in this audit |
| 42 | Predecessor is Sprint 41 | Stays later. Owns probes, alerts, paging, and incident operations |
| 44 / 45 | Launch claims and the public PH market | Public certified shopping markets stay 0 until those gates |

Do not enable routing, provider status, or the public PH market in order to manufacture a Sprint 38 close.

---

## Explicit non-claims

- This audit does not mark Sprint 38 COMPLETE / CLOSED.
- This audit does not call Sprint 38 engineering complete.
- This audit does not implement B1 or B2.
- This audit does not make live research operational.
- This audit does not deploy production or the production UCP profile.
- This audit does not start Sprint 41 or Sprint 42.
- This audit does not enable public PH shopping coverage.
- This audit does not record a real Shopify call.
- This audit does not treat fake transport output as live certified evidence.
