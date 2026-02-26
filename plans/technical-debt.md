# Technical Debt

Tracked items to address before production or during hardening phases. Items from Phase 1 review deferred list are prefixed with their original ID (D1-D21).

## Pre-Phase 3 (address before loan officer features)

### (D2) WebSocket chat: no rate limits, no message size limits, no connection limits

`packages/api/src/routes/chat.py` and `borrower_chat.py` accept unbounded messages without rate limiting or connection caps. Add per-user connection limits and message throttling.

### (D7) Unbounded conversation history in WebSocket

`routes/chat.py` accumulates messages in a local list for non-checkpointer fallback. No sliding window or max-messages cap. For long sessions this could exhaust memory. Add a max-messages limit (e.g., 100) with oldest-message eviction.

### (D8) `verify_aud` disabled in JWT validation

`middleware/auth.py:105` -- token from any Keycloak client is accepted. Should validate `aud` claim matches `summit-cap-ui` (or a configured client ID).

### (D16) Agent registry stats filesystem on every WebSocket message

`agents/registry.py:23` -- `_load_agent_config()` calls `stat()` on the YAML file for every incoming message to detect hot-reloads. Add a minimum check interval (e.g., 5 seconds) to avoid unnecessary I/O.

### (D17) Fragile `Path(__file__).parents[4]` resolution

`agents/registry.py:20` and `inference/config.py:25` use hardcoded parent traversal depth. Breaks if the package is restructured. Use a project root marker file or env var instead.

### (D18) DB package reads `os.environ` directly vs pydantic-settings

`packages/db/src/db/database.py:16-24` reads env vars directly while `packages/api` uses pydantic-settings. Dual config paths could diverge in non-obvious ways. Unify around pydantic-settings or at minimum document the divergence.

## Pre-Phase 4 (address before audit trail queries)

### (D10) `audit_events.event_data` is Text, contract says JSONB

`packages/db/src/db/models.py` -- audit event data is stored as Text, not JSONB. DB-level JSON querying (filtering audit events by event_data fields) is not possible. Requires migration to JSONB column type.

## Pre-Production (address before any non-local deployment)

### (D3) `AUTH_DISABLED=true` hardcoded in compose.yml

`compose.yml:89` -- should be `${AUTH_DISABLED:-false}` with a startup guard that warns or blocks if auth is disabled in production-like profiles.

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

## Deferred Features (out of MVP scope)

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
| D9 | HMDA route didn't verify application ownership (IDOR) | Fixed in `collect_demographics()` -- uses `apply_data_scope` |
| D19 | HMDA `/collect` borrower_id not validated against junction table | Fixed in `collect_demographics()` -- validates via `ApplicationBorrower` |
