# summit-cap API

FastAPI backend for Summit Cap Financial mortgage loan origination.

> **Setup & Installation**: See the [root README](../../README.md) for installation and quick start instructions.

## Directory Structure

```
src/
  main.py              # FastAPI app, middleware, router registration
  core/config.py       # Pydantic Settings (env-driven config)
  middleware/
    auth.py            # JWT validation, RBAC, UserContext
    pii.py             # PII masking middleware (CEO role)
  routes/
    health.py          # GET /health/
    public.py          # Public endpoints (products, affordability)
    applications.py    # Application CRUD + status + conditions
    decisions.py       # Decision list + detail (read-only)
    documents.py       # Document upload, list, completeness
    chat.py            # Public WebSocket chat (unauthenticated)
    borrower_chat.py   # Borrower WebSocket chat (authenticated) + history
    loan_officer_chat.py  # Loan officer WebSocket chat + history
    underwriter_chat.py   # Underwriter WebSocket chat + history
    admin.py           # Admin endpoints (seed, audit, verification)
    hmda.py            # HMDA demographics collection (isolated schema)
    _chat_handler.py   # Shared WebSocket streaming logic
  schemas/             # Pydantic request/response models
  services/            # Business logic layer
    compliance/        # HMDA, compliance checks, knowledge base
    seed/              # Demo data seeding
  agents/              # LangGraph agent definitions + tool modules
    base.py            # Base agent graph (input/output shields, RBAC, routing)
    registry.py        # Agent config loading from config/agents/*.yaml
    public_tools.py    # Public assistant tools (products, affordability)
    borrower_tools.py  # Borrower tools (intake, docs, disclosures, status)
    loan_officer_tools.py  # LO tools (pipeline, workflow, communication)
    underwriter_tools.py   # UW tools (queue, risk, conditions, application detail)
    decision_tools.py  # Decision tools (propose, confirm, LE/CD, adverse action)
    compliance_check_tool.py  # Compliance check tool (ECOA, ATR/QM, TRID)
  inference/           # LLM client, model routing, safety shields
tests/
  test_*.py            # Unit tests
  functional/          # Persona-based functional tests
  integration/         # DB-backed integration tests
```

## REST API Routes

### Health
- `GET /health/` - Service health check (includes DB, S3, LLM status)

### Public (no authentication)
- `GET /api/public/products` - List mortgage product catalog
- `POST /api/public/calculate-affordability` - Calculate affordability based on income and debts

### Applications (authenticated)
- `GET /api/applications/` - List applications (paginated, role-scoped, sortable by urgency)
- `POST /api/applications/` - Create new application (borrower, admin)
- `GET /api/applications/{id}` - Get single application
- `PATCH /api/applications/{id}` - Update application (loan officer, underwriter, admin)
- `GET /api/applications/{id}/status` - Get aggregated application status summary
- `GET /api/applications/{id}/rate-lock` - Get rate lock status
- `GET /api/applications/{id}/conditions` - List conditions (filterable by `open_only`)
- `POST /api/applications/{id}/conditions/{cid}/respond` - Respond to a condition (borrower)
- `POST /api/applications/{id}/borrowers` - Add borrower to application
- `DELETE /api/applications/{id}/borrowers/{bid}` - Remove borrower from application

### Decisions (authenticated, read-only)
- `GET /api/applications/{id}/decisions` - List all decisions for an application
- `GET /api/applications/{id}/decisions/{did}` - Get single decision detail

### Documents (authenticated)
- `POST /api/applications/{id}/documents` - Upload document (multipart form)
- `GET /api/applications/{id}/documents` - List application documents
- `GET /api/applications/{id}/documents/{did}` - Get document detail (CEO: file_path redacted)
- `GET /api/applications/{id}/documents/{did}/content` - Get document file path (CEO blocked)
- `GET /api/applications/{id}/completeness` - Check document completeness

### HMDA (authenticated)
- `POST /api/hmda/collect` - Collect borrower demographics (isolated compliance schema)

### Admin (admin role only)
- `POST /api/admin/seed` - Seed demo data
- `GET /api/admin/seed/status` - Check seed status
- `GET /api/admin/audit` - Query audit log (filterable by `application_id`, `event_type`)
- `GET /api/admin/audit/application/{id}` - Audit events for a specific application
- `GET /api/admin/audit/verify` - Verify hash chain integrity

### Conversation History (authenticated)
- `GET /api/borrower/conversations/history` - Borrower conversation history
- `GET /api/loan-officer/conversations/history` - Loan officer conversation history
- `GET /api/underwriter/conversations/history` - Underwriter conversation history

## WebSocket Protocol

### Endpoints

**Public Chat (unauthenticated):**
```
ws://host/api/chat
```
No authentication required. Session ID is ephemeral (UUID). Conversations do not persist.

**Borrower Chat (authenticated):**
```
ws://host/api/borrower/chat?token=<jwt>
```

**Loan Officer Chat (authenticated):**
```
ws://host/api/loan-officer/chat?token=<jwt>
```

**Underwriter Chat (authenticated):**
```
ws://host/api/underwriter/chat?token=<jwt>
```

JWT passed via query parameter for all authenticated endpoints. Thread ID is deterministic (`user:{userId}:agent:{agent-name}`). Conversations persist via PostgreSQL checkpoint.

When `AUTH_DISABLED=true`, returns a development user.

### Message Protocol

**Client sends:**
```json
{"type": "message", "content": "user text here"}
```

**Server sends (streaming):**
```json
{"type": "token", "content": "partial"}
{"type": "tool_start", "content": "tool_name"}
{"type": "tool_end", "content": "tool result summary"}
{"type": "safety_override", "content": "reason for safety intervention"}
{"type": "done"}
{"type": "error", "content": "error message"}
```

Tokens stream incrementally as the LLM generates responses. `done` signals end of response. `safety_override` indicates the safety shield triggered and overrode the LLM output. `tool_start`/`tool_end` bracket agent tool invocations.

## Agents

Four LangGraph agents, each with role-scoped tools and YAML config (`config/agents/`):

| Agent | Role | Tools |
|-------|------|-------|
| `public-assistant` | (none) | Products, affordability calculator |
| `borrower-assistant` | borrower | Application intake, doc upload, status, disclosures |
| `loan-officer-assistant` | loan_officer | Pipeline, workflow actions, communication drafting |
| `underwriter-assistant` | underwriter | Queue, risk assessment, conditions, decisions, compliance checks |

All agents share a common base graph (`agents/base.py`) with input/output safety shields, rule-based model routing (fast/capable tiers), and tool-level RBAC enforcement.

## Authentication & RBAC

Authentication via Keycloak JWT. Five roles supported:
- `admin` - Full system access
- `borrower` - Own application access
- `loan_officer` - Assigned applications access
- `underwriter` - Applications in review
- `ceo` - Read-only access with PII masking

Set `AUTH_DISABLED=true` for local development to bypass authentication.

## Error Format

Errors follow RFC 7807 Problem Details:
```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Application not found",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Pagination

List endpoints return paginated responses:
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "offset": 0,
    "limit": 20,
    "has_more": true
  }
}
```

## Configuration

Environment variables loaded via Pydantic Settings (`src/core/config.py`):
- `DATABASE_URL` - PostgreSQL connection string (host port 5433 for local dev)
- `COMPLIANCE_DATABASE_URL` - Separate connection for HMDA isolated schema
- `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` - Keycloak OIDC configuration
- `AUTH_DISABLED` - Bypass authentication for local dev
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` - MinIO/S3 object storage
- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL_FAST`, `LLM_MODEL_CAPABLE` - LLM provider
- `SAFETY_MODEL`, `SAFETY_ENDPOINT` - Llama Guard safety shields (optional)
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` - LangFuse observability (optional)
- `SQLADMIN_USER`, `SQLADMIN_PASSWORD`, `SQLADMIN_SECRET_KEY` - Admin panel credentials
- `ALLOWED_HOSTS` - CORS allowed origins

## Running Locally

```bash
# Start dev server
uv run uvicorn src.main:app --reload

# Run tests
AUTH_DISABLED=true uv run pytest -v

# Run tests with coverage
AUTH_DISABLED=true uv run pytest --cov=src

# Linting and formatting
uv run ruff check src/
uv run ruff format src/
```

Database is available at `localhost:5433` when using `podman-compose` (maps host 5433 to container 5432).

For database setup and migrations, see the [DB package README](../db/README.md).
