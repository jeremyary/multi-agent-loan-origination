# API Response Patterns

The API uses three distinct response patterns. A frontend client must handle all three — there
is no single universal envelope.

---

## 1. Paginated Envelope

Offset-paginated list endpoints wrap results in a `data` array with a `pagination` object.

```json
{
  "data": [ { ... }, { ... } ],
  "pagination": {
    "total": 42,
    "offset": 0,
    "limit": 20,
    "has_more": true
  }
}
```

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/api/applications/` | Supports `offset`, `limit`, `sort_by`, `filter_stage`, `filter_stalled` |
| `GET` | `/api/applications/{id}/conditions` | Supports `open_only`; pagination always reflects full result set |
| `GET` | `/api/applications/{id}/decisions` | Pagination always reflects full result set |

The `Pagination` model is defined in `src/schemas/__init__.py`.

---

## 2. Custom Envelope

Audit endpoints use domain-specific wrappers with a `count` integer, a named events array, and
one or more context identifiers. No `data` key.

| Method | Path | Response shape |
|--------|------|----------------|
| `GET` | `/api/audit/session` | `{ "session_id": "...", "count": N, "events": [...] }` |
| `GET` | `/api/audit/application/{id}` | `{ "application_id": N, "count": N, "events": [...] }` |
| `GET` | `/api/audit/decision/{id}` | `{ "decision_id": N, "count": N, "events": [...] }` |
| `GET` | `/api/audit/search` | `{ "count": N, "events": [...] }` |
| `GET` | `/api/audit/verify` | `{ "status": "...", "events_checked": N, "first_break_id": N\|null }` |
| `GET` | `/api/audit/decision/{id}/trace` | `{ "decision_id": N, "application_id": N, "decision_type": "...", "events_by_type": {...}, "total_events": N, ... }` |

`GET /api/audit/export` returns a file download (`application/json` or `text/csv`) with a
`Content-Disposition` header — not a JSON envelope.

---

## 3. Raw Response

Object or array returned directly — no `data` wrapper, no `pagination`.

**Single objects:**

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/api/applications/{id}` | `ApplicationResponse` object |
| `GET` | `/api/applications/{id}/status` | `ApplicationStatusResponse` object |
| `GET` | `/api/applications/{id}/rate-lock` | `RateLockResponse` object |
| `POST` | `/api/applications/` | `ApplicationResponse` object (201) |
| `PATCH` | `/api/applications/{id}` | `ApplicationResponse` object |
| `POST` | `/api/applications/{id}/borrowers` | `ApplicationResponse` object (201) |
| `DELETE` | `/api/applications/{id}/borrowers/{bid}` | `ApplicationResponse` object |
| `POST` | `/api/applications/{id}/conditions/{cid}/respond` | `{ "data": ConditionItem }` — single-item data wrapper |
| `GET` | `/api/applications/{id}/decisions/{did}` | `{ "data": DecisionItem }` — single-item data wrapper |
| `GET` | `/api/analytics/pipeline` | `PipelineSummary` object |
| `GET` | `/api/analytics/denial-trends` | `DenialTrends` object |
| `GET` | `/api/analytics/lo-performance` | `LOPerformanceSummary` object |
| `GET` | `/api/ceo/model-monitoring` | `ModelMonitoringSummary` object |
| `GET` | `/api/ceo/model-monitoring/latency` | `LatencyMetrics` object |
| `GET` | `/api/ceo/model-monitoring/tokens` | `TokenUsage` object |
| `GET` | `/api/ceo/model-monitoring/errors` | `ErrorMetrics` object |
| `GET` | `/api/ceo/model-monitoring/routing` | `RoutingDistribution` object |
| `POST` | `/api/admin/seed` | `SeedResponse` object |
| `GET` | `/api/admin/seed/status` | `SeedStatusResponse` object |

**Arrays:**

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/api/health/` | `list[HealthResponse]` |
| `GET` | `/api/public/products` | `list[ProductInfo]` |
| `POST` | `/api/public/calculate-affordability` | `AffordabilityResponse` object |

---

## Summary

| Pattern | Top-level shape | Used for |
|---------|----------------|----------|
| Paginated envelope | `{ "data": [...], "pagination": {...} }` | Offset-paginated collection endpoints |
| Custom envelope | `{ "<context_key>": ..., "count": N, "events": [...] }` | Audit trail query endpoints |
| Raw response | Object or array directly | All other endpoints |

**Known inconsistency (W-43):** `GET .../decisions/{id}` and
`POST .../conditions/{id}/respond` wrap their single item in `{ "data": <item> }` rather than
returning the object bare, unlike all other single-resource endpoints.
