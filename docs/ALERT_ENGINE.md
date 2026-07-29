# Alert Engine (Sprint 19)

**Status:** Sprint 19
**Evaluation engine:** `AlertEvaluationEngine` in `app/alerts/engine/evaluator.py`
**Dedupe helpers:** `app/alerts/engine/dedupe.py`
**Rule CRUD service:** `AlertRuleService` in `app/services/alert_rule_service.py`
**Orchestration service:** `AlertEvaluationService` in `app/services/alert_evaluation_service.py`
**Domain entities:** `app/domain/entities/alerts.py`
**Repository ports:** `app/domain/interfaces/alert_rule_repository.py`
**In-memory store:** `InMemoryAlertRuleRepository` in `app/alerts/memory.py`

## Overview

The Alert Engine is a rule-driven, scheduler-neutral alternative to the
Sprint 10 hard-coded four-condition `AlertService` (`WATCHLISTS_V1.md`).
Users define one or more `AlertRule` records, each with one or more
`AlertCondition`s; evaluating a rule against a fresh observation snapshot
produces an `AlertEvaluation` and, when triggered, a deduplicated
`AlertEvent` that fans out to the [Notification Center](NOTIFICATIONS.md).

The Sprint 10 `Alert`/`AlertType`/`AlertService` surface is **untouched** —
`AlertEvaluationService` additionally creates a Sprint-10-compatible `Alert`
record for every triggered condition (via `_create_legacy_alert`) so existing
`GET /alerts`, acknowledge, and dismiss endpoints keep working against both
evaluation paths.

## Architecture

```
API (/api/v1/alerts/rules, /api/v1/alerts/evaluate, /api/v1/alerts/events)
      │
      ▼
  AlertRuleService                    AlertEvaluationService (implements AlertJobTrigger)
   ├─ create/update/delete_rule()      ├─ trigger_evaluate(user_id | watchlist_id | rule_id)
   ├─ pause/resume_rule()              ├─ evaluate_all() / evaluate_for_user() / evaluate_watchlist()
   ├─ condition/threshold validation   ├─ evaluate_item() / evaluate_rules()
   └─► AlertRuleRepository             └─► _build_observation()  (price history, DealScore, marketplace offer)
                                             │
                                             ▼
                                       AlertEvaluationEngine (pure, no I/O)
                                             │  evaluate_rule() — OR across conditions
                                             ▼
                                       AlertEvaluation {triggered, reason, fingerprint}
                                             │  (if triggered)
                                             ▼
                                       dedupe.build_dedupe_key() ──► AlertEventRepository.find_by_dedupe_key()
                                             │  (new occurrence only)
                                             ▼
                                       AlertEvent  ──► NotificationCenterService.create_from_alert_event()
                                             └──────► legacy Alert (Sprint 10 compatible) + mock notify
```

`AlertEvaluationEngine` never sleeps, starts background work, or performs
I/O — it is a pure function of `(AlertRule, observation dict) -> AlertEvaluation`.
All persistence, price/DealScore/marketplace reads, and notification fan-out
happen in `AlertEvaluationService`.

## Conditions

`AlertConditionType` (`app/domain/entities/alerts.py`) — one enum shared by
rule conditions and the legacy `AlertType`:

| Condition | Trigger rule |
|-----------|--------------|
| `price_drop` | `price < previous_price` |
| `percentage_price_decrease` | `(previous_price - price) / previous_price * 100 >= threshold_percent` |
| `absolute_price_decrease` | `previous_price - price >= threshold_value` |
| `price_increase` | `price > previous_price` |
| `target_price_reached` | `price <= threshold_value` (or `target_price` observation) |
| `historical_low` | `price <= historical_low` |
| `dealscore_improved` | `dealscore - previous_dealscore >= threshold_value` (default `0`) |
| `dealscore_threshold` | `dealscore` compared to `threshold_value` via `comparison` (`gte`/`lte`, default `gte`) |
| `restocked` | availability transitions out-of-stock → in-stock |
| `unavailable` | availability transitions (or starts) in-stock/unknown → out-of-stock |
| `low_inventory` | `inventory <= threshold_value` (default `3`) |
| `better_offer` | a competing `better_offer_price` is present and cheaper than `price` |
| `preferred_seller_available` | current `seller` is in `preferred_sellers` and changed since last observation |
| `preferred_marketplace_available` | current `marketplace` is in `preferred_marketplaces` and changed |
| `stale_data` | `freshness_status == "stale"`, or `age_hours >= threshold_value` |
| `freshness_restored` | `previous_freshness_status == "stale"` and current status is not |

A rule triggers if **any** condition holds (OR semantics); split conditions
across separate rules for AND-style requirements. A condition that raises a
`ConditionEvaluationError` (e.g. a required threshold is missing) is reported
via `AlertEvaluation.partial_failure`/`error` — it never blocks the other
conditions in the same rule.

## Cooldowns, one-time rules, and idempotent evaluation

- **`cooldown_seconds`** (default `0`) — a rule cannot fire again until this
  many seconds have elapsed since `last_triggered_at`. `cooldown_seconds<=0`
  disables the cooldown entirely.
- **`repeat_policy`** — `recurring` (default) or `one_time`. A `one_time`
  rule that has already fired (`one_time_fired=True`) never fires again,
  regardless of cooldown.
- **`AlertEvaluationEngine.can_fire()`** gates on administrative `enabled`/
  `status`, one-time exhaustion, and cooldown — independent of whether the
  rule's conditions currently hold.
- Re-evaluating the *same* rule against an *unchanged* observation is safe
  and idempotent: the engine reports `triggered=True` again (its conditions
  still hold), but `AlertEvaluationService` computes the same
  `observation_fingerprint` and **dedupe key**, finds the existing
  `AlertEvent` via `AlertEventRepository.find_by_dedupe_key()`, and skips
  creating a duplicate event/notification — it only persists the rule's
  updated cooldown/one-time state.

## Deduplication

`app/alerts/engine/dedupe.py`:

- `observation_fingerprint(observation, condition_type)` — a stable SHA-256
  hash over a curated set of observation fields (`price`, `previous_price`,
  `inventory`, `availability`, `seller`, `marketplace`, `freshness_status`,
  `dealscore`) plus the condition type. Deterministic regardless of dict
  ordering or float formatting.
- `build_dedupe_key(user_id, condition_type, rule_id, watchlist_id, item_id, fingerprint)`
  — combines scope + condition + fingerprint into one string key, used as
  the uniqueness constraint for `AlertEvent` records.

## Scheduler-neutral job interface

`AlertJobTrigger` (`app/domain/entities/alerts.py`) is an abstract
`trigger_evaluate(*, user_id=None, watchlist_id=None, rule_id=None, now=None)`
method that `AlertEvaluationService` implements. **No scheduler, cron,
Celery/RQ worker, or APScheduler job exists anywhere in this codebase.**
Evaluation only ever happens when a caller (an API request, a test, or —
in a future sprint — real infrastructure) explicitly invokes
`trigger_evaluate()` or one of `evaluate_all()` / `evaluate_for_user()` /
`evaluate_watchlist()` / `evaluate_item()` / `evaluate_rules()`. This mirrors
the `SyncJobTrigger` pattern used by Marketplace Data
(see [`SYNC_ENGINE.md`](SYNC_ENGINE.md)).

## API

Route ordering matters: `rules_router` (`/alerts/rules`) and
`evaluate_router` (`/alerts/evaluate`, `/alerts/events`) are registered
**before** the Sprint 10 `/alerts/{alert_id}` routes so FastAPI does not
match `rules`/`evaluate` against the `{alert_id}` path parameter.

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| `GET` | `/alerts/rules` | Bearer* | scoped to caller; filters `watchlist_id`, `item_id`, `enabled` |
| `POST` | `/alerts/rules` | Bearer* | `201 Created` |
| `GET` | `/alerts/rules/{rule_id}` | Bearer* | |
| `PUT` | `/alerts/rules/{rule_id}` | Bearer* | |
| `DELETE` | `/alerts/rules/{rule_id}` | Bearer* | `204 No Content` |
| `POST` | `/alerts/evaluate` | Bearer (required) | scope: `rule_id` \| `watchlist_id` \| user-wide |
| `GET` | `/alerts/events` | Bearer (required) | `limit` 1–200 |

\* Falls back to a body-supplied `user_id` only when `WATCHLISTS_REQUIRE_AUTH=false`.

Every evaluation response includes a disclaimer that notifications remain
mock/simulated.

## Limitations

- **In-app functional**; **email is simulated** — see
  [`EMAIL_PROVIDER_ARCHITECTURE.md`](EMAIL_PROVIDER_ARCHITECTURE.md).
- **No SMS. No push.**
- **No external scheduler** — see above; evaluation is always explicit.
- **In-memory persistence only** — rules, evaluations, and events live in
  `InMemoryAlertRuleRepository` for the life of the process.
- **No affiliate links, ads, sponsored placements, merchant integrations, or
  billing** anywhere in this feature.
- Previous-observation tracking for delta-based conditions (`restocked`,
  `preferred_seller_available`, etc.) is a process-local cache inside
  `AlertEvaluationService`, not a persisted observation-history table — a
  process restart loses the "previous" side of the next comparison (the
  first post-restart evaluation for a delta condition will not trigger until
  a second observation is taken).
- `AlertJobTrigger.trigger_evaluate` is declared synchronous on the ABC but
  implemented `async` (it must await price/DealScore reads); Python does not
  enforce sync/async parity on ABC overrides, so callers must `await` it.
