# Technical Debt

Tracked items to address before production or during hardening phases. Items from Phase 1 review deferred list are prefixed with their original ID (D1-D21).

## Pre-Production (address before any non-local deployment)

### (D2) WebSocket chat: no rate limits, no message size limits, no connection limits

`packages/api/src/routes/chat.py` and `borrower_chat.py` accept unbounded messages without rate limiting or connection caps. Add per-user connection limits and message throttling.

### (D7) Unbounded conversation history in WebSocket

`routes/chat.py` accumulates messages in a local list for non-checkpointer fallback. No sliding window or max-messages cap. For long sessions this could exhaust memory. Add a max-messages limit (e.g., 100) with oldest-message eviction.

### (D16) Agent registry stats filesystem on every WebSocket message

`agents/registry.py:23` -- `_load_agent_config()` calls `stat()` on the YAML file for every incoming message to detect hot-reloads. Add a minimum check interval (e.g., 5 seconds) to avoid unnecessary I/O.

### (D17) Fragile `Path(__file__).parents[4]` resolution

`agents/registry.py:20` and `inference/config.py:25` use hardcoded parent traversal depth. Breaks if the package is restructured. Use a project root marker file or env var instead.

### (D18) DB package reads `os.environ` directly vs pydantic-settings

`packages/db/src/db/database.py:16-24` reads env vars directly while `packages/api` uses pydantic-settings. Dual config paths could diverge in non-obvious ways. Unify around pydantic-settings or at minimum document the divergence.

### (D3) `AUTH_DISABLED=true` hardcoded in compose.yml

`compose.yml:91` -- should be `${AUTH_DISABLED:-false}` with a startup guard that warns or blocks if auth is disabled in production-like profiles.

### (D4) No rate limiting on any endpoint

No rate limiting exists project-wide. Add `slowapi` or equivalent middleware. Critical for public endpoints (`/api/public/*`) and auth endpoints.

### (D5) CORS `allow_methods` and `allow_headers` too permissive

`packages/api/src/main.py:37-38` -- currently allows `["*"]` for both methods and headers. Restrict to actual methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`) and headers (`Authorization`, `Content-Type`) used by the frontend.

### (D6) Sync `httpx.get()` for JWKS fetch blocks event loop

`middleware/auth.py:36` -- JWKS keys are fetched synchronously with `httpx.get()`, blocking the async event loop. Use `httpx.AsyncClient` instead.

### (D11) SSN stored as plaintext with `ENC:` prefix

`packages/db/src/db/models.py:46` -- field is named `ssn_encrypted` but value is plaintext with `ENC:` prefix. Either implement real encryption (AES-256) or rename the field and add a disclaimer that this is simulated for MVP.

### (D12) Safety shields fail-open on error

`inference/safety.py:128-149` -- when the safety model endpoint is unreachable or returns an error, the message passes through unfiltered. Documented and acceptable for MVP. For production, consider fail-closed behavior for high-risk content categories.

### (D14) Application service untested

`services/application.py` has no direct test coverage. The RBAC data scope filtering is tested via integration tests against real DB, but the service layer methods themselves lack unit tests.

### (D15) HMDA `collection_method` only stores race method

`services/compliance/hmda.py:55-56` -- originally only stored `race_collected_method`. Per-field methods (race, ethnicity, sex, age) were added in the co-borrower PR but the schema comment may still reference the old behavior.

## Pre-Phase 4 (address before audit trail queries)

### (D10) `audit_events.event_data` is Text, contract says JSONB

`packages/db/src/db/models.py` -- audit event data is stored as Text, not JSONB. DB-level JSON querying (filtering audit events by event_data fields) is not possible. Requires migration to JSONB column type.

## Phase 5 Readiness

**Note:** Phase 5 (Executive/CEO persona) cannot be fully completed until these items are addressed.

### P-1: CEO persona unimplemented

The CEO persona and its associated features (F33-F39 from requirements-chunk-5-executive.md) have not been implemented. Phase 5 requires CEO chat endpoint, executive dashboard aggregations, audit trail query endpoints, and fair lending metrics display.

### P-2: F38 TrustyAI dependency for CEO fair lending panel

Feature F38 (Fair Lending Metrics with TrustyAI) was deferred from Phase 4 and moved to `plans/deferred/f38-trustyai-fairness-metrics.md`. The CEO dashboard's fair lending panel (showing SPD/DIR metrics by protected class) depends on this feature. Without F38, the CEO persona can be implemented but the fairness metrics panel will be non-functional or removed.

### P-3: Seed data expansion needed for demo walkthrough

The `plans/demo-walkthrough.md` script requires diverse applications spanning multiple loan officers, product types, underwriter decisions, and demographic groups to demonstrate pipeline views, fairness metrics, and audit trails. Current seed data (added in Phase 1-4) covers basic CRUD and agent tool flows but lacks the volume and diversity for executive-level aggregations.

### P-4: F23 Container Deployment not started

Feature F23 (Container Deployment) from Phase 1 requirements was never implemented. The Helm chart exists but has not been tested in an OpenShift environment. Phase 5 is the natural time to validate containerized deployment since CEO features require the full stack (compliance KB, HMDA schema, agents, audit trail).

### P-5: LoanType ARM missing (USDA was never planned)

The `LoanType` enum in `packages/db/src/db/models.py` includes `USDA` but not `ARM` (Adjustable Rate Mortgage). USDA loans were never in scope for this quickstart. ARM should be added to support diverse product demonstrations in Phase 5. USDA should be removed or marked as placeholder.

### P-8: No interface contracts for Phases 3-4

Interface contract documents were only created for Phase 1 (`plans/interface-contracts-phase-1.md`). Phases 2-4 added significant API surface (pipeline endpoints, underwriter tools, compliance checks) without corresponding contract docs. Phase 5 planning would benefit from a consolidated interface contracts document covering all implemented APIs.

## Deferred Features (out of MVP scope)

### F26: Agent Adversarial Defenses (4 stories deferred)

S-4-F26-01 through S-4-F26-04. Adds regex-based prompt injection detection (Layer 1), HMDA data leakage output scanning (Layer 4), demographic proxy detection, and security_event audit logging.

**Why deferred:** Existing defenses are stronger than what F26 adds at PoC maturity:
- Llama Guard 3 (ML-based) already handles prompt injection detection -- regex keyword matching is strictly weaker and will produce false positives on legitimate mortgage queries
- HMDA schema isolation (architectural boundary, separate DB schema + session) prevents data leakage -- output text scanning for demographic keywords would flag compliance KB content referencing fair lending laws
- Proxy discrimination detection requires ML-based semantic analysis to distinguish legitimate property assessment (ZIP code for flood zone) from demographic inference; pattern matching at PoC maturity would have unacceptable false positive rates
- Tool RBAC (Layer 3) already prevents unauthorized tool access with audit logging

**Revisit when:** Moving toward production hardening, or if adversarial testing reveals gaps in Llama Guard coverage that keyword patterns could cheaply address.

### F38: TrustyAI Fairness Metrics (4 stories deferred)

S-4-F38-01 through S-4-F38-04. Adds SPD/DIR fairness metrics computed from HMDA demographics vs underwriting decisions, threshold-based alerts, and a CEO/ADMIN dashboard endpoint.

**Why deferred:** Stakeholder decision -- too much scope for the MVP timeline. The TrustyAI library requires JPype + JVM which adds infrastructure complexity. A full implementation plan exists at `plans/deferred/f38-trustyai-fairness-metrics.md` and can be picked up post-MVP.

**Revisit when:** Post-MVP hardening, or when a frontend dashboard for executive metrics is prioritized.

### (D20) Co-borrower management endpoints

POST/DELETE `/applications/{id}/borrowers` -- schema and junction table are ready, endpoints deferred until the UI needs them.

### (D21) Per-borrower financials

`ApplicationFinancials` stays per-application for MVP. Co-borrower-level financial tracking is out of scope.

## Existing Items (from earlier tracking)

### Rate limiting on public endpoints

The public API (`/api/public/products`, `/api/public/calculate-affordability`) requires no authentication. Overlaps with D4 above.

### Dev Postgres port hardcoded to 5433

All connection strings default to port 5433. Scattered across `compose.yml`, `alembic.ini`, `database.py`, `admin.py`, and `config.py`. Should be centralized to `DATABASE_URL` env var.

### Alembic migration hand-written

The first migration (`fe5adcef3769_add_domain_models.py`) was written manually. Future migrations should use `alembic revision --autogenerate`.

### SQLAlchemy deprecated API usage

`packages/db/src/db/database.py` uses `sqlalchemy.ext.declarative.declarative_base()` (deprecated in SQLAlchemy 2.0). Migrate to `sqlalchemy.orm.DeclarativeBase`.

### Pydantic v2 deprecated config style

`packages/api/src/core/config.py` uses class-based `Config` inner class (deprecated in Pydantic v2). Migrate to `model_config = ConfigDict(...)`.

### Admin panel uses separate sync engine

`packages/api/src/admin.py` creates its own `sqlalchemy.create_engine`. SQLAdmin requires a sync engine, but the URL derivation should be centralized.

### JWKS key rotation lacks integration test

Cache-bust-on-kid-mismatch logic in `middleware/auth.py` has no automated test coverage. Add integration test once Keycloak is in CI.

### Data scope query filtering lacks integration tests

`_apply_scope` in `services/application.py` is the core RBAC enforcement on data access. Needs integration tests with real DB.

### Ruff config extends nonexistent shared config

`packages/db/pyproject.toml` has `extend = "../../configs/ruff/pyproject.toml"` but that file doesn't exist.

### Interface contract drift (D13a-d)

- Compose versions: Keycloak 24->26, LangFuse v2->v3, MinIO added
- ID types: contract says UUID, implementation uses int; user_id is str not UUID
- `models.yaml` provider: contract says "llamastack", implementation uses "openai_compatible"
- HealthResponse: implementation returns list of service objects, contract specifies single object

## Resolved

| ID | Finding | Resolution |
|----|---------|------------|
| D1 | SQLAdmin had no authentication | Added `AdminAuth` backend -- login required when `AUTH_DISABLED=false` |
| D8 | `verify_aud` disabled in JWT validation | Fixed in PR #73 -- added `"verify_aud": True` to JWT validation options |
| D9 | HMDA route didn't verify application ownership (IDOR) | Fixed in `collect_demographics()` -- uses `apply_data_scope` |
| D19 | HMDA `/collect` borrower_id not validated against junction table | Fixed in `collect_demographics()` -- validates via `ApplicationBorrower` |
