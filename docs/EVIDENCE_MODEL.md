# Community Evidence Model

**Status:** Sprint 14  
**Entity:** `CommunityEvidence`

## Common normalized fields

| Field | Description |
|-------|-------------|
| `source` | Connector id (`reddit`, `youtube`, …) |
| `product` | Product display name |
| `product_id` | Stable product identifier |
| `evidence_id` | Globally unique evidence id |
| `url` / `permalink` | Link when available |
| `title` / `body` | Discussion text |
| `topic` | Extracted topic (configurable vocabulary) |
| `sentiment` | `{label, score}` |
| `confidence` | 0–1 structural confidence |
| `engagement` | Normalized upvotes/likes/views/etc. |
| `timestamp` | UTC timestamp |
| `author` | When available |
| `thread_id` | Parent discussion id when applicable |
| `data_status` | `mock` / `imported` / `live` |

## Evidence Explorer

Insights (topics / AI statements) must cite `evidence_ids`.

Example:

```
Battery Excellent
Supported by:
  - reddit:r_tuf_battery_1
  - reddit:r_tuf_battery_1_c1
  - amazon_qa:amz_q_15
  - youtube:yt_tuf_review_8
Confidence High
```

## Deduplication

`DuplicateDetector` fingerprints topic + normalized title/body and keeps the strongest engagement/confidence copy so repeated claims are not over-counted.

## Validation

`EvidenceValidator` rejects blank ids, unsupported sources, empty title+body, and out-of-range confidence.

## Shopping Assistant mapping

Community evidence is projected to shopping evidence as:

- `type = "community"`
- `source_id = "community_intelligence"`
- description includes topic + title/body snippet + sentiment label

The assistant must not depend on connector-specific parsing.
