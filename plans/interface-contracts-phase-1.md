# Interface Contracts: Phase 1

This document defines the **boundary-level agreements** for Phase 1. It covers only the shapes that cross component boundaries -- what goes in and out at integration points. It does not prescribe internal implementation details.

Engineers own how they build their piece. This document owns the seams between pieces.

---

## 1. API Routes

These are the HTTP endpoints the frontend calls and the backend exposes. Both sides must agree on method, path, auth requirement, and request/response shape.

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| GET | `/health` | No | Any | -- | `HealthResponse` |
| GET | `/api/public/products` | No | Any | -- | `ProductInfo[]` |
| POST | `/api/public/calculate-affordability` | No | Any | `AffordabilityRequest` | `AffordabilityResponse` |
| POST | `/api/hmda/collect` | Yes | borrower | `HmdaCollectionRequest` | `HmdaCollectionResponse` |
| POST | `/api/admin/seed` | Yes | admin (dev only) | -- | `{ status, summary }` |
| GET | `/api/admin/seed/status` | Yes | admin (dev only) | -- | `{ seeded: bool, seeded_at }` |

Error responses use `ErrorResponse` for all 4xx/5xx.

---

## 2. Shared Data Models

### Python (Pydantic) -- `packages/api/src/summit_cap/schemas/`

These models are the contract. If you consume or produce data that crosses a boundary, use these exact shapes.

```python
# common.py

class UserRole(StrEnum):
    ADMIN = "admin"
    PROSPECT = "prospect"
    BORROWER = "borrower"
    LOAN_OFFICER = "loan_officer"
    UNDERWRITER = "underwriter"
    CEO = "ceo"

class DataScope(BaseModel):
    assigned_to: str | None = None
    pii_mask: bool = False
    own_data_only: bool = False
    user_id: str | None = None
    full_pipeline: bool = False

class UserContext(BaseModel):
    """Injected by RBAC middleware into every authenticated request.
    Frozen -- middleware returns new instances via model_copy()."""
    model_config = ConfigDict(frozen=True)
    user_id: str  # Keycloak sub claim
    role: UserRole
    email: str
    name: str
    data_scope: DataScope = Field(default_factory=DataScope)

class HealthResponse(BaseModel):
    name: str
    status: str
    message: str
    version: str
    start_time: str | None = None

class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str | None = None
```

```python
# calculator.py

class AffordabilityRequest(BaseModel):
    gross_annual_income: float = Field(gt=0)
    monthly_debts: float = Field(ge=0)
    down_payment: float = Field(ge=0)
    interest_rate: float = Field(default=6.5, ge=0, le=15)
    loan_term_years: int = Field(default=30, ge=10, le=40)

class AffordabilityResponse(BaseModel):
    max_loan_amount: float
    estimated_monthly_payment: float
    estimated_purchase_price: float
    dti_ratio: float
    dti_warning: str | None = None
    pmi_warning: str | None = None
```

```python
# hmda.py

class HmdaCollectionRequest(BaseModel):
    application_id: int
    race: str | None = None
    ethnicity: str | None = None
    sex: str | None = None
    race_collected_method: str = "self_reported"
    ethnicity_collected_method: str = "self_reported"
    sex_collected_method: str = "self_reported"
    age_collected_method: str = "self_reported"

class HmdaCollectionResponse(BaseModel):
    id: int
    application_id: int
    collected_at: datetime
    status: str = "collected"
```

```python
# auth.py

class TokenPayload(BaseModel):
    sub: str
    email: str
    preferred_username: str
    name: str
    realm_access: dict  # {"roles": ["borrower", ...]}
```

### TypeScript -- `packages/ui/src/services/types.ts`

Frontend equivalents of the Python models above. Must stay in sync.

```typescript
type UserRole = "admin" | "prospect" | "borrower" | "loan_officer" | "underwriter" | "ceo";

interface AuthUser {
    id: string;
    email: string;
    name: string;
    role: UserRole;
}

interface HealthResponse {
    name: string;
    status: string;
    message: string;
    version: string;
    start_time: string | null;
}

interface ErrorResponse {
    error: string;
    detail?: string;
    request_id?: string;
}

interface ProductInfo {
    id: string;
    name: string;
    description: string;
    min_down_payment_pct: number;
    typical_rate: number;
}

interface AffordabilityRequest {
    gross_annual_income: number;
    monthly_debts: number;
    down_payment: number;
    interest_rate?: number;
    loan_term_years?: number;
}

interface AffordabilityResponse {
    max_loan_amount: number;
    estimated_monthly_payment: number;
    estimated_purchase_price: number;
    dti_ratio: number;
    dti_warning: string | null;
    pmi_warning: string | null;
}
```

---

## 3. Database Schema

### Tables (public schema -- `lending_app` role)

| Table | Key Columns | Used By |
|-------|-------------|---------|
| `applications` | id, stage (ApplicationStage enum), loan_type, property_address, loan_amount, property_value, assigned_to | Most services |
| `borrowers` | id, keycloak_user_id, first_name, last_name, email, ssn_encrypted, dob | Auth, application services |
| `application_borrowers` | id, application_id, borrower_id, is_primary | Junction table linking applications to borrowers (supports co-borrowers) |
| `application_financials` | id, application_id, borrower_id, gross_monthly_income, monthly_debts, total_assets, credit_score, dti_ratio | Underwriting, LO pipeline |
| `rate_locks` | id, application_id, locked_rate, lock_date, expiration_date, is_active | LO pipeline |
| `conditions` | id, application_id, description, severity, status, issued_by, cleared_by | Underwriting |
| `decisions` | id, application_id, decision_type, rationale, ai_recommendation, decided_by | Underwriting, audit |
| `documents` | id, application_id, doc_type, file_path, status, quality_flags, uploaded_by | Document services |
| `document_extractions` | id, document_id, field_name, field_value, confidence, source_page | Extraction pipeline |
| `audit_events` | id, timestamp, prev_hash, user_id, user_role, event_type, application_id, decision_id, event_data, session_id | All (append-only, INSERT+SELECT only) |
| `conversation_checkpoints` | id, user_id, thread_id, checkpoint_data, created_at | Agent layer |
| `demo_data_manifest` | id, seeded_at, config_hash, summary | Seeding |

### Tables (hmda schema -- `compliance_app` role only)

| Table | Key Columns |
|-------|-------------|
| `hmda.demographics` | id, application_id, borrower_id, race, ethnicity, sex, age, race_method, ethnicity_method, sex_method, age_method, collected_at |

### Access Rules

| Role | public schema | hmda schema | audit_events |
|------|--------------|-------------|-------------|
| `lending_app` | Full CRUD | **No access** | INSERT + SELECT only |
| `compliance_app` | SELECT only | Full CRUD | INSERT + SELECT |

This is enforced at the PostgreSQL level. Two connection pools in the application map to these roles. The `compliance_app` pool is used exclusively by the Compliance Service (`services/compliance/`).

---

## 4. Auth Contract (Keycloak)

### Realm: `summit-cap`

**Clients:**
- `summit-cap-ui` -- public client, PKCE (S256), redirect to `http://localhost:3000/*`
- `summit-cap-api` -- bearer-only (validates tokens, no login flow)

**Roles:** prospect, borrower, loan_officer, underwriter, ceo, admin

**Demo users:**
| Username | Role |
|----------|------|
| sarah.mitchell | borrower |
| james.torres | loan_officer |
| maria.chen | underwriter |
| david.park | ceo |
| admin | admin |

**Token shape:** JWTs with `realm_access.roles` containing the user's role(s). Access token: 15 min. Refresh token: 8 hours with rotation.

**Contract for backend:** Validate JWT signature against JWKS (cached 5 min, cache-bust on failure). Extract role from `realm_access.roles`. Fail-closed: Keycloak unreachable = 503 for all authenticated requests.

**Contract for frontend:** Use `keycloak-js` adapter. Proactive refresh when < 1 min remaining. Store tokens in sessionStorage (tab-scoped). 401 from API triggers refresh attempt.

---

## 5. RBAC Middleware Contract

This is the pipeline that sits between auth and route handlers. Anyone building routes or services needs to know what it produces.

**What the middleware provides to handlers:**

`UserContext` (see Section 2) is injected as a FastAPI dependency. It contains the authenticated user's identity and data scope filters.

**Data scope rules:**

| Role | Scope Behavior |
|------|---------------|
| borrower | `own_data_only = True`, `user_id` set |
| loan_officer | `assigned_to = <user_id>` (sees only their pipeline) |
| underwriter | No filter (sees all applications in underwriting+) |
| ceo | `pii_mask = True` (sees all data, PII masked) |

**PII masking (CEO role):** Applied as response middleware. SSN -> `***-**-1234`, DOB -> `YYYY-**-**`, account numbers -> `****5678`. Masking failure = 500 (never send unmasked).

**Tool authorization:** LangGraph pre-tool node checks `user_role in tool.allowed_roles` before each tool call. Tool registries are in agent config YAML (`config/agents/*.yaml`).

---

## 6. Configuration Schemas

### config/models.yaml

```yaml
routing:
  default_tier: capable_large
  classification:
    strategy: rule_based
    rules:
      simple:
        max_query_words: 10
        patterns: ["status", "when", "what is", "show me", "how much",
                   "my application", "hello", "hi", "thanks", "thank you"]
      complex:
        default: true
        keywords: ["compliance", "regulation", "dti", "calculate",
                   "affordability", "document", "underwriting", ...]

models:
  fast_small:
    provider: openai_compatible
    model_name: "${LLM_MODEL_FAST:-gpt-4o-mini}"
    description: "Fast model for simple factual queries"
    endpoint: "${LLM_BASE_URL:-https://api.openai.com/v1}"
  capable_large:
    provider: openai_compatible
    model_name: "${LLM_MODEL_CAPABLE:-gpt-4o-mini}"
    description: "Capable model for complex reasoning and tool use"
    endpoint: "${LLM_BASE_URL:-https://api.openai.com/v1}"
```

**Routing strategy:** Rule-based classification with confidence escalation. The classify node (no LLM call) checks complex keywords first, then word count, then simple patterns. Default fallback is the capable tier. The fast model has NO tools bound; if its response indicates low confidence (via logprobs or hedging phrases), the graph escalates to the capable model.

Required fields per model: `provider`, `model_name`, `endpoint`. Config is validated at startup (missing = fail to start) and hot-reloaded per-conversation via mtime check.

### config/agents/*.yaml

```yaml
agent:
  name: <agent_name>        # required
  persona: <role>            # required
  description: "..."

system_prompt: |
  ...

tools:
  - name: <tool_name>
    description: "..."
    allowed_roles: [<role>, ...]

data_access:
  scope: public_only | own_data | assigned | full | compliance
  tables: [<table>, ...]
```

Required fields: `agent.name`, `agent.persona`, `system_prompt`. Hot-reloaded same as models.yaml.

---

## 7. Infrastructure Contract (Compose)

### Services and Ports

| Service | Image | Port | Health Check | Profile |
|---------|-------|------|-------------|---------|
| postgres | pgvector/pgvector:pg16 | 5432 | `pg_isready` | (always) |
| keycloak | quay.io/keycloak/keycloak:26.0 | 8080 | `/health/live` | auth, full |
| redis | redis:7-alpine | 6379 | `redis-cli ping` | observability, full |
| clickhouse | clickhouse/clickhouse-server:24 | 8123 | `SELECT 1` | observability, full |
| minio | minio/minio:latest | 9000/9001 | `/minio/health/live` | (always) |
| langfuse-web | langfuse/langfuse:3 | 3001 | `/api/public/health` | observability, full |
| langfuse-worker | langfuse/langfuse-worker:3 | -- | -- | observability, full |
| llamastack | llamastack/distribution-starter:latest | 8321 | `/v1/models` | ai, full |
| api | (built from packages/api/Dockerfile) | 8000 | `/health` | (always) |
| ui | (built from packages/ui/Dockerfile) | 3000 | -- | (always) |

### Profiles

| Profile | What starts |
|---------|-------------|
| (none) | postgres, minio, api, ui |
| auth | + keycloak |
| ai | + llamastack |
| observability | + redis, clickhouse, langfuse-web, langfuse-worker |
| full | everything |

### Startup Order

postgres -> (keycloak, redis, clickhouse in parallel) -> langfuse -> llamastack -> api (after postgres + keycloak healthy) -> ui (after api healthy)

### Volume Mounts

- `./config:/app/config:ro` on api (enables hot-reload of agent/model configs)
- `./data:/app/data:ro` on api (compliance KB, demo data)

---

## 8. Cross-Boundary Dependencies

This shows which stories connect to other engineers' work at integration points. If you're working on one side of a boundary, coordinate with the person on the other side about the contract.

| Boundary | Producer | Consumer | Contract to Agree On |
|----------|----------|----------|---------------------|
| API <-> Frontend | Backend (routes) | Frontend (api-client.ts) | Section 1 (routes) + Section 2 (models) |
| Auth <-> RBAC | Keycloak auth (WU-2) | RBAC middleware (WU-4) | Section 4 (token shape, UserContext) |
| RBAC <-> Routes | RBAC middleware (WU-4) | All route handlers | Section 5 (UserContext, DataScope) |
| DB <-> Services | Schema/migrations (WU-1) | All backend services | Section 3 (table shapes, access rules) |
| HMDA isolation | Schema (WU-1) + endpoint (WU-3) | Compliance service, CI lint | Section 3 (dual roles, dual pools) |
| Config <-> Router | models.yaml schema (WU-5) | Model router, agent loader | Section 6 (YAML schemas) |
| Compose <-> Everything | Docker Compose (WU-9) | All services | Section 7 (ports, health checks, profiles) |

---

## 9. Parallel Work Streams

After bootstrap (WU-0), four streams can run in parallel. Each stream's internal work is sequential, but streams are independent until convergence points.

```
Stream A (Data):     WU-1 -> WU-3, WU-6 (parallel after WU-1)
Stream B (Auth):     WU-2
Stream C (Infra):    WU-5
Stream D (Frontend): WU-8a -> WU-8b
```

**Convergence:** WU-4 (RBAC) needs both WU-1 and WU-2. WU-7 (integration tests) needs WU-4 and WU-3. WU-9 needs everything.

Engineers on parallel streams can stub/mock the contracts from this document at the boundaries. For example, the frontend engineer can mock the API responses using the shapes in Section 2 while the backend is being built.

---

## Contract Change Protocol

If you discover that an agreed contract doesn't work:

1. **Propose** the change (describe what and why) before implementing around it
2. **Check** who else depends on the contract (use Section 8)
3. **Update** this document once agreed
4. **Notify** affected engineers

Do not implement workarounds for a broken contract. Fix the contract.
