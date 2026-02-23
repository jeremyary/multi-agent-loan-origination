# Architecture: AI Banking Quickstart -- Summit Cap Financial (v1.3)

## 1. System Overview

### 1.1 Design Philosophy

This architecture serves two audiences: Summit demo viewers who need a polished, reliable walkthrough, and Quickstart developers who need a comprehensible, extensible codebase. Every design decision favors **clarity over cleverness** and **explicit over implicit**.

Core principles:

- **Dual-data-path isolation** -- HMDA demographic data and lending decision data travel through architecturally separate paths that share no runtime components.
- **Role-scoped agents** -- Each persona gets an agent with a distinct tool set, system prompt, and data access boundary. No shared "super agent."
- **Append-only auditability** -- Every AI action, data access, and human decision is captured in an immutable audit log that supports backward tracing.
- **Configuration-driven extensibility** -- Agent definitions, tool registrations, model routing rules, and RBAC policies are declared in configuration, not scattered through code. A Quickstart user can add a persona by adding configuration, not by modifying framework code.
- **PoC maturity, production structure** -- Implementation quality is PoC-appropriate (smoke tests, console errors acceptable), but the component boundaries, data model, and integration patterns are designed to support production hardening without rearchitecture.

### 1.2 High-Level Component Diagram

```
                                    +-------------------+
                                    |   Identity        |
                                    |   Provider        |
                                    |   (Keycloak)      |
                                    +--------+----------+
                                             |
                                             | OIDC tokens
                                             |
+---------------------------+       +--------v----------+       +-------------------+
|                           |       |                   |       |                   |
|   Frontend Application    | <---> |   API Gateway     | <---> |   LangFuse        |
|   (React SPA)             |  WS/  |   (FastAPI)       |       |   (Observability) |
|                           | HTTP  |                   |       |                   |
+---------------------------+       +--------+----------+       +-------------------+
                                             |
                        +--------------------+--------------------+
                        |                    |                    |
               +--------v-------+   +--------v-------+   +------v---------+
               |                |   |                |   |                |
               |  Agent Layer   |   |  Domain        |   |  Document      |
               |  (LangGraph)   |   |  Services      |   |  Processing    |
               |                |   |                |   |                |
               +--------+-------+   +--------+-------+   +--------+------+
                        |                    |                    |
                        +--------------------+--------------------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------v-------+      +--------v--------+     +--------v--------+
           |                |      |                  |     |                 |
           |  PostgreSQL    |      |  Object Storage  |     |  LlamaStack /   |
           |  + pgvector    |      |  (Local FS /     |     |  Model Serving  |
           |                |      |   S3-compatible) |     |                 |
           +----------------+      +------------------+     +-----------------+
```

### 1.3 Component Summary

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| Frontend Application | Five persona UIs, chat interfaces, dashboards | React (Vite) |
| API Gateway | Authentication, authorization, request routing, RBAC enforcement | FastAPI |
| Agent Layer | Per-persona AI agents with role-scoped tools | LangGraph |
| Domain Services | Business logic: applications, documents, compliance, audit | Python modules |
| Document Processing | Upload, extraction, quality assessment, demographic filtering | Python + LLM-based extraction |
| PostgreSQL + pgvector | Application state, audit trail, conversation history, vector embeddings | PostgreSQL 16 + pgvector |
| Object Storage | Raw document files (PDFs, images) | Local filesystem (dev) / S3-compatible (prod) |
| Identity Provider | User authentication, role management, session tokens | Keycloak |
| LlamaStack | Model serving abstraction, inference routing | LlamaStack server |
| LangFuse | Agent trace observability, token tracking, latency monitoring | LangFuse (self-hosted) |

## 2. Component Architecture

### 2.1 Frontend Application

**Responsibility:** Render five persona-specific user interfaces. Handle chat interactions with streaming responses. Display dashboards (CEO), pipeline views (LO, Underwriter), document upload (Borrower, LO), and audit trail views (CEO, Underwriter).

**Technology:** React with Vite build tooling. See [ADR-0003: Frontend Framework Selection](#adr-0003-frontend-framework-selection).

**Boundaries:**
- The frontend never enforces access control. All authorization decisions happen server-side. The frontend receives only data the user is authorized to see.
- Chat interactions use WebSocket connections for streaming. Non-chat API calls use standard HTTP.
- The frontend is a single React application with file-based routing via TanStack Router. After authentication, `beforeLoad` hooks on route definitions enforce role-based access -- the route itself declares the required role, checked before rendering. TanStack Query manages server state (polling, caching, background refetch) for the application's many data-fetching use cases (pipeline status, document processing status, CEO dashboard metrics, audit trail queries). The UI component layer uses shadcn/ui (copy-paste components built on Radix primitives for accessibility) on top of Tailwind CSS.
- No server-side rendering -- a simple SPA that connects to the FastAPI backend.

**Key UI surfaces by persona:**

| Persona | Primary UI | Secondary UI |
|---------|-----------|-------------|
| Prospect | Chat widget on public landing page | Product information pages |
| Borrower | Chat interface with application context | Document upload, status tracker |
| Loan Officer | Pipeline dashboard with urgency indicators | Chat interface, document review |
| Underwriter | Review workspace with application detail | Chat interface, audit trail viewer |
| CEO | Executive dashboard with charts and metrics | Chat interface, audit trail viewer |

**Model monitoring overlay (F39):** The CEO dashboard includes a model monitoring panel displaying inference health metrics: latency percentiles, token usage, error rates, and model routing distribution. These metrics are sourced from data already collected by LangFuse callbacks -- no additional monitoring infrastructure is required. The frontend queries LangFuse's API (proxied through the FastAPI backend) to render this overlay.

**CEO document access restriction:** The CEO persona can see document metadata (that a document exists, its type, status, and quality flags) but cannot access document content. This restriction is enforced at the API, service, and query layers (see Section 4.2 for the full enforcement matrix).

**F4 form fallback contingency:** The primary application intake experience is conversational-only (agent-driven). However, a structured form fallback is accepted as a contingency: if conversational-only proves too brittle for specific application sections (e.g., complex financial data entry), those sections may fall back to structured forms while preserving conversational guidance as the primary experience. The frontend architecture accommodates both paths -- the chat interface is the default, with optional form components that can be activated per-section if needed.

**Interface with backend:** HTTP REST for data operations. WebSocket for streaming chat responses. SSE is a production upgrade path if WebSocket proves problematic in certain deployment environments, but the PoC uses WebSocket exclusively.

### 2.2 API Gateway (FastAPI)

**Responsibility:** The single entry point for all client requests. Authenticates requests against the identity provider, enforces RBAC at the API layer, routes requests to the appropriate domain service or agent, and applies PII masking for role-restricted responses.

**Boundaries:**
- Every request (except public/unauthenticated routes for the Prospect persona) must carry a valid OIDC token.
- RBAC enforcement happens here, not in the frontend or in individual services. The gateway resolves the user's role from the token claims and applies data access policies before forwarding the request.
- PII masking for the CEO role (SSN, DOB, account numbers) is applied at this layer before data reaches the response.
- The gateway does NOT contain business logic. It delegates to domain services and the agent layer.

**Key routing patterns:**

| Route Category | Auth Required | Handler |
|----------------|--------------|---------|
| `/api/public/*` | No | Public assistant, product info |
| `/api/chat` | Yes (all roles) | Agent layer via WebSocket |
| `/api/applications/*` | Yes (Borrower, LO, UW, CEO) | Application domain service |
| `/api/documents/*` | Yes (Borrower, LO, UW) | Document processing service |
| `/api/audit/*` | Yes (UW, CEO) | Audit trail service |
| `/api/analytics/*` | Yes (CEO) | Analytics service |
| `/api/admin/*` | Yes (internal) | Demo data seeding, health checks |
| `/api/admin/db/*` | Yes (admin role, dev only) | SQLAdmin database inspection UI. Wired to the `lending_app` connection pool -- cannot see HMDA data. Must be disabled or restricted in production. |

**RBAC middleware pipeline:**

```
Request -> Token validation -> Role extraction -> Route authorization
        -> Data scope injection (e.g., LO sees only own pipeline)
        -> Handler execution
        -> PII masking (role-based field filtering)
        -> Response
```

The "data scope injection" step is critical: when a Loan Officer requests applications, the middleware injects a filter restricting results to applications assigned to that officer. This prevents application-level code from accidentally returning unauthorized data.

### 2.3 Agent Layer (LangGraph)

**Responsibility:** Execute AI agent workflows for each persona. Each agent is a LangGraph graph with a persona-specific system prompt, a curated tool set, and data access boundaries that mirror the RBAC policy.

**Architecture:** Agent-per-persona with shared infrastructure. See [ADR-0005: Agent Security Architecture](#adr-0005-agent-security-architecture).

**Agent definitions are configuration-driven.** Each agent is defined by:

1. **System prompt template** -- persona-specific instructions, guardrails, and behavioral constraints.
2. **Tool registry** -- the set of tools this agent can invoke, declared in configuration.
3. **Data access scope** -- which domain services this agent can call and with what filters.
4. **Model routing rule** -- which model tier to use for different query complexities.

Agent config changes are picked up per-conversation via hot-reload (see Section 9.3) -- no application restart required.

**Agent inventory:**

| Agent | Persona | Key Tools | Data Scope |
|-------|---------|-----------|------------|
| Public Assistant | Prospect | product_info, affordability_calc, prequalification | Public data only. No customer data. |
| Borrower Assistant | Borrower | application_status, document_status, upload_document, application_data | Own application data only |
| LO Assistant | Loan Officer | pipeline_view, application_detail, document_review, draft_communication, submit_to_underwriting, condition_response | Own pipeline only |
| Underwriter Assistant | Underwriter | risk_assessment, compliance_check, kb_search, issue_conditions, render_decision, draft_adverse_action | Full underwriting pipeline + read-only origination |
| CEO Assistant | CEO | analytics_query, pipeline_summary, fair_lending_metrics, audit_search | Aggregate data + masked individual records |

**Security layers (defense in depth):**

1. **Input validation** -- Agent queries are validated for adversarial patterns before processing. Known injection patterns are detected and rejected. Rejected queries are logged to the audit trail.
2. **Tool authorization at execution time** -- Implemented as a LangGraph pre-tool node that executes immediately before each tool invocation. The node reads the user's role from JWT claims in the session context (known staleness window: access token lifetime of 15 minutes). Authorization results are NOT cached across turns -- every tool call triggers a fresh check. On authorization failure: the tool returns an authorization error to the agent, the agent communicates the restriction to the user, and the attempt is recorded in the audit trail.
3. **Output filtering** -- Agent responses are scanned before delivery to ensure no out-of-scope data is included. For the CEO agent, PII fields are verified as masked. For lending agents (LO, Underwriter), HMDA demographic data is verified as absent. The filter includes semantic checks for demographic proxy references (neighborhood-level demographic composition, proxy characteristics that correlate with protected classes). This is pattern-matching at PoC maturity; production would use ML-based semantic detection.

**LangGraph state management:** Each agent conversation maintains state in a LangGraph checkpoint. Checkpoints are persisted to PostgreSQL for cross-session memory (F19). The checkpoint includes conversation history, collected application data (for the borrower agent), and tool call results.

### 2.4 Domain Services

**Responsibility:** Business logic organized by domain concern. Domain services are called by the API gateway (for direct API requests) and by agent tools (for AI-mediated operations).

**Boundaries:** Domain services contain the business rules. They do not contain authentication, authorization (that is the gateway's job), or AI logic (that is the agent layer's job). They operate on validated, authorized requests.

**Service inventory:**

| Service | Responsibility | Key Operations |
|---------|---------------|----------------|
| Application Service | Mortgage application lifecycle | Create, update, get status, transition state, list by pipeline |
| Document Service | Document metadata, completeness checking | Register upload, record extraction results, check completeness, track freshness |
| Underwriting Service | Decision management, conditions tracking | Record decisions, manage conditions lifecycle, generate adverse action data |
| Compliance Service | HMDA data management, fair lending, fairness metrics, compliance knowledge base search | Store HMDA data (isolated path), aggregate HMDA statistics, flag fair lending concerns. Computes fairness metrics (Statistical Parity Difference, Disparate Impact Ratio) using the `trustyai` Python library on aggregate HMDA-correlated lending outcomes. Exposes only pre-aggregated statistics -- no API returns individual HMDA records joined with lending decisions. Aggregation happens inside the service; consumers receive pre-aggregated results. Includes a knowledge base submodule providing vector similarity search with tier precedence and document ingestion for the compliance KB (see Section 2.6). |
| Audit Service | Append-only audit trail | Write audit events, query by application/decision/pattern |
| Analytics Service | Cross-domain metric aggregation for executive reporting | Composes business metrics (pipeline volume, turn times, denial rates, pull-through, LO performance) from lending data, fairness metrics (SPD, DIR) from Compliance Service, and operational metrics (model latency, token usage, error rates) from LangFuse into unified dashboard views. Read-only; owns no primary data. |
| Conversation Service | Cross-session memory management | Store/retrieve conversation checkpoints, enforce user isolation |

**Key design rule:** Domain services accept a `user_context` parameter that includes the authenticated user's ID, role, and data scope. Services use this context to filter data access. Services never trust the caller to have already filtered -- they re-apply data scoping internally as defense in depth.

### 2.5 Document Processing

**Responsibility:** Handle document upload, storage, information extraction, quality assessment, and demographic data filtering.

**Pipeline:**

```
Upload -> Store raw file -> Quality assessment -> Information extraction
       -> Demographic data filter -> Store extracted data -> Update application
       -> Audit log
```

**Demographic data filter (HMDA isolation):** After extraction, a dedicated filter step scans extracted data for demographic content (race, ethnicity, sex). The detection mechanism uses keyword matching combined with semantic similarity against known demographic data patterns. If detected:
1. The demographic data is excluded from the extraction result that enters the lending data path.
2. The exclusion is logged in the audit trail with the reason.
3. The raw document is stored as-is (it may contain demographic data), but access to raw documents is role-controlled (CEO gets metadata only).

**False negative mitigation:** If the demographic filter misses indirect demographic data (e.g., a document that references "applicant from a predominantly Hispanic neighborhood"), the agent output filter (Layer 4 of agent security, see Section 4.3) acts as a secondary defense -- even if demographic data enters the extraction pipeline, it is caught before reaching the user. The adversarial test suite includes test cases with indirect demographic references to validate both layers. This is a PoC-maturity limitation; production would use ML-based detection for higher recall.

**Quality assessment:** LLM-based assessment for common document issues: blurriness, incorrect time period, missing pages, unsigned documents, wrong document type. Quality flags are stored as document metadata.

**Extraction approach:** LLM-based extraction with structured output (Pydantic models). The extraction prompt is document-type-specific. Pre-seeded demo documents are designed to produce consistent, correct extractions.

### 2.6 Knowledge Base (Compliance Service Submodule)

> **Organizational note:** The compliance knowledge base is architecturally part of the Compliance Service (see Section 2.4). It is described in its own section because the RAG pipeline has distinct concerns (embedding, chunking, tier precedence) that warrant dedicated documentation. In the codebase, the knowledge base lives as a submodule within the Compliance Service (`services/compliance/knowledge_base/`).

**Responsibility:** Store, index, and search the three-tier compliance knowledge base for the underwriter and loan officer AI assistants.

**Architecture:** RAG pipeline using pgvector for vector storage. See [ADR-0002: Database Selection](#adr-0002-database-selection) for the pgvector rationale.

**Three-tier document hierarchy:**

| Tier | Content | Precedence | Source |
|------|---------|-----------|--------|
| 1 (Highest) | Federal and state regulations | Overrides all lower tiers | TRID, ECOA/Reg B, HMDA, ATR/QM, FCRA, Colorado state regs |
| 2 | Agency and investor guidelines | Overrides internal overlays | Fictional Fannie Mae, FHA, VA guideline excerpts |
| 3 (Lowest) | Internal Summit Cap Financial overlays | Lowest precedence | Internal policies, risk thresholds, exception procedures |

**Search with tier precedence:** When the agent searches the KB, results are ranked by vector similarity but tier precedence is applied as a boost factor. Federal regulations rank above agency guidelines, which rank above internal overlays. If results from multiple tiers conflict, the higher tier prevails and the conflict is noted in the response.

**Ingestion pipeline:**
1. Source documents (markdown or PDF) are chunked with overlap.
2. Each chunk is tagged with its tier, source document name, and section reference.
3. Chunks are embedded using the configured embedding model (via LlamaStack).
4. Embeddings are stored in pgvector with tier metadata.

**Content curation:** Compliance KB content must be reviewed by a domain-knowledgeable reviewer before coding. Incorrect regulatory statements are the highest credibility risk. All content carries a "simulated for demonstration purposes" tag.

## 3. Data Architecture

### 3.1 Database Selection

PostgreSQL 16 with the pgvector extension. See [ADR-0002: Database Selection](#adr-0002-database-selection).

**Rationale summary:** A single PostgreSQL instance handles relational data (applications, users, conditions, documents), append-only audit events, conversation checkpoints, and vector embeddings for the compliance KB. This avoids the operational complexity of multiple databases while pgvector provides vector search capability that is sufficient for PoC-scale RAG (hundreds of compliance document chunks, not millions).

### 3.2 Schema Overview

SQLAlchemy models for all schemas are defined in `packages/db/` (a separate Python package). The dual connection pool configuration (`lending_app` / `compliance_app` PostgreSQL roles) is configured in `packages/db/src/summit_cap_db/database.py` and imported by the API package. Alembic migrations also live in `packages/db/`. The API package (`packages/api/`) depends on `packages/db/` as a uv workspace path dependency.

The schema is organized into logical domains. This is a high-level overview -- detailed table definitions belong in Technical Design.

**Application domain:**
- `applications` -- Mortgage application state (stage, loan type, property info, financial details)
- `borrowers` -- Borrower identity and contact information (linked to auth user)
- `co_borrowers` -- Co-borrower information linked to applications
- `application_financials` -- Income, debts, assets, DTI calculations
- `rate_locks` -- Rate lock status, dates, terms (first-class data per F27)
- `conditions` -- Underwriting conditions with lifecycle status (issued, responded, cleared, waived)
- `decisions` -- Underwriting decisions with rationale and AI recommendation

**Document domain:**
- `documents` -- Document metadata (type, upload date, status, quality flags, freshness)
- `document_extractions` -- Extracted data points with source provenance
- `document_versions` -- Version history for resubmitted documents

**HMDA domain (isolated -- see Section 3.3):**
- `hmda_demographics` -- Demographic data collected per application, stored in isolated schema
- `hmda_aggregates` -- Pre-computed aggregate statistics for CEO dashboard

**Audit domain:**
- `audit_events` -- Append-only event log (see Section 3.4)

**Conversation domain:**
- `conversation_checkpoints` -- LangGraph state checkpoints keyed by user ID

**Knowledge base domain:**
- `kb_documents` -- Source document metadata (tier, name, section)
- `kb_chunks` -- Document chunks with embeddings (pgvector column)

**Analytics domain:**
- Standard SQL views over the application and decision data for CEO dashboard queries. These are read-only aggregations, not separate tables. At PoC scale, standard views are sufficient. Materialized views are noted as a production optimization for when query volume or data size warrants cached aggregations.

**Demo data domain:**
- `demo_data_manifest` -- Tracks whether demo data is seeded, supports clean teardown. Demo data uses the same tables as live data -- no separate demo tables.

### 3.3 HMDA Data Isolation

See [ADR-0001: HMDA Data Isolation Architecture](#adr-0001-hmda-data-isolation-architecture).

The core architectural challenge: the system must collect demographic data for regulatory reporting (HMDA) while proving that this data cannot influence lending decisions.

**Four-stage isolation:**

| Stage | Mechanism | Verification |
|-------|----------|-------------|
| **Collection** | HMDA data is collected through a dedicated API endpoint that writes only to the `hmda` schema. The collection endpoint does not share a transaction or service path with any lending data operation. | Audit log records collection event on the HMDA path. |
| **Document Extraction** | The document extraction pipeline includes a demographic data filter. If demographic data is detected in an uploaded document, it is excluded from the extraction result, the exclusion is logged, and the excluded data is not written to any lending-path table. | Audit log records exclusion event with document reference. |
| **Storage** | HMDA demographic data is stored in a separate PostgreSQL schema (`hmda`). Access is enforced at the database level through distinct PostgreSQL roles (see role table below). The lending data path services do not have queries that join to the `hmda` schema. The Compliance Service is the only service that reads from `hmda`, and it exposes only aggregate statistics. | Database role verification: `psql -U lending_app -c "SELECT * FROM hmda.demographics"` must return a permission denied error. CI lint check: no code outside `services/compliance/` references the `hmda` schema. |
| **Retrieval** | AI agents for lending personas (LO, Underwriter) are configured with tools that cannot query the HMDA data. The Compliance Service's `get_hmda_aggregates` tool is available only to the CEO agent. Individual HMDA records are never exposed through any tool. | Agent tool registry audit: verify no lending-persona agent has HMDA-querying tools. |

**TrustyAI fairness metrics (F38):** The Compliance Service uses the `trustyai` Python library to compute Statistical Parity Difference (SPD) and Disparate Impact Ratio (DIR) on aggregate HMDA-correlated lending outcomes. These metrics power the CEO dashboard's fair lending analysis (F12). The `trustyai` library runs within the Compliance Service process -- no additional containers or external services. Because TrustyAI operates on aggregate data within the Compliance Service, it follows the same dual-data-path isolation: the Compliance Service remains the sole HMDA accessor, and fairness metrics are pre-computed before exposure to any consumer.

**Data flow diagram:**

```
Borrower provides demographic data
        |
        v
HMDA Collection Endpoint -----> hmda.demographics table
(Isolated service path)              |
                                     | (aggregate only)
                                     v
                              Compliance Service
                              get_hmda_aggregates()
                                     |
                                     v
                              CEO Agent only
                              (aggregate metrics)

Document upload
        |
        v
Extraction Pipeline -----> Demographic Filter -----> EXCLUDED
        |                                            (logged)
        v
Lending data path tables
(No demographic data)
```

**PostgreSQL role separation:**

| Role | Grants | Used By | Connection Pool |
|------|--------|---------|----------------|
| `lending_app` | Full CRUD on lending schema tables, INSERT+SELECT on `audit_events`, no grants on `hmda` schema | API gateway, Agent layer, all domain services except Compliance | Primary connection pool |
| `compliance_app` | SELECT on `hmda` schema, SELECT on lending schema (read-only for aggregate joins), INSERT+SELECT on `audit_events` | Compliance Service only | Dedicated connection pool |

In the monolithic FastAPI process, role separation is enforced through **separate SQLAlchemy connection pools** -- one configured with the `lending_app` credentials and one with `compliance_app` credentials. The Compliance Service module is the only code that uses the `compliance_app` pool. A CI lint check (see Section 8.1) verifies that no code outside `services/compliance/` imports or references the compliance connection pool or the `hmda` schema.

### 3.4 Audit Trail Architecture

See [ADR-0006: Audit Trail Architecture](#adr-0006-audit-trail-architecture).

**Append-only guarantees:**
- The `audit_events` table has no UPDATE or DELETE grants for the application database user. The application connects with a role that has INSERT and SELECT only on audit tables.
- A database trigger rejects any UPDATE or DELETE attempted on `audit_events`, logging the attempt to a separate `audit_violations` table.
- Sequential event IDs (bigserial) provide ordering guarantees.
- A hash chain (each event includes a hash of the previous event's ID + content) provides tamper evidence at PoC level. This is not cryptographically rigorous but detects naive modification.
- **Concurrency strategy:** A PostgreSQL advisory lock is acquired around audit inserts to ensure serial hash chain computation. At PoC scale (small number of concurrent users), advisory lock contention is negligible. The hash chain is a PoC-specific mechanism that would be **replaced** (not incrementally upgraded) for production -- a production system would use a fundamentally different tamper-evidence approach (e.g., database-level cryptographic verification or an external ledger).

**Audit event schema (conceptual):**

```
audit_events:
  id: bigserial (sequential, immutable)
  timestamp: timestamptz (server-generated, immutable)
  prev_hash: text (hash of previous event -- tamper evidence)
  user_id: uuid (who)
  user_role: text (their role at time of event)
  event_type: text (query, tool_call, data_access, decision, override, system)
  application_id: uuid (nullable -- links to application if applicable)
  decision_id: uuid (nullable -- links to decision if applicable)
  event_data: jsonb (full context: query text, tool name, parameters, response, model used)
  source_document_id: uuid (nullable -- data provenance link)
  session_id: uuid (conversation session)
```

**Three query patterns:**

| Pattern | Use Case | Query Approach |
|---------|----------|---------------|
| Application-centric | "Show me everything that happened with application #2024-0847" | Filter on `application_id`, order by timestamp |
| Decision-centric | "Trace backward from this denial to all contributing factors" | Start from `decision_id`, follow `application_id` to find all related events |
| Pattern-centric | "All denials in past 90 days with AI recommendation for each" | Filter on `event_type = 'decision'`, aggregate with decision data |

**PII masking in audit responses:** When the CEO views audit entries, the same PII masking rules apply -- borrower names visible, sensitive fields (SSN, DOB, account numbers) masked in the `event_data` JSON before response.

### 3.5 Conversation Persistence

Cross-session memory (F19) is implemented through LangGraph's checkpoint persistence, backed by PostgreSQL.

**Isolation:** The checkpoint table includes `user_id` as a mandatory column. All checkpoint queries use parameterized queries (`WHERE user_id = :requesting_user_id`) -- never string interpolation for the user ID. There is no query path that retrieves checkpoints across users, including for admin or CEO roles.

**Defense-in-depth:**
- **Post-retrieval verification:** After retrieving a checkpoint, the Conversation Service validates that the checkpoint's `user_id` matches the requesting user's ID. This catches any ORM misconfiguration or query builder error that might bypass the WHERE clause.
- **ORM configuration:** The SQLAlchemy model for checkpoints does not define eager-loading relationships that cross user boundaries. No relationship to other users' checkpoints is modeled. Lazy loading is used for all checkpoint relationships to prevent accidental cross-user data loading.

**Upgrade path:** At PoC maturity, full conversation history is stored. For production, the architecture supports migration to summarized or semantic memory by replacing the checkpoint serializer -- the storage interface remains the same.

## 4. Authentication and Authorization

### 4.1 Identity Provider

Keycloak running as a container alongside the application. See [ADR-0007: Deployment Architecture](#adr-0007-deployment-architecture).

**Rationale:** Keycloak is the stakeholder-suggested identity provider. It provides standards-based OIDC authentication, role management, and user administration. It runs as a container with minimal configuration, supports pre-configured realm import for single-command setup, and is production-grade.

**Pre-configured realm:** The Quickstart ships with a Keycloak realm export (`summit-cap-realm.json`) that pre-configures:
- Five roles: `prospect`, `borrower`, `loan_officer`, `underwriter`, `ceo`
- Demo users mapped to each role (when demo data is seeded)
- Client configuration for the React frontend (public client with PKCE)
- Client configuration for the FastAPI backend (confidential client for token validation)

**Token configuration:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Access token lifetime | 15 minutes | Short-lived to limit exposure window. Bounds the staleness window for role checks (including agent tool authorization). |
| Refresh token lifetime | 8 hours with rotation | Supports a full working session. Rotation ensures that a stolen refresh token is single-use. |
| JWKS cache duration | 5 minutes | The API caches Keycloak's JWKS for 5 minutes. On signature verification failure, the JWKS is re-fetched immediately (cache-busting on failure). |
| IdP unavailability | Fail-closed | If Keycloak cannot be reached for token validation, all authenticated requests are rejected. The system does not fall back to an unvalidated state. |
| WebSocket token validation | Per-message | The token is re-validated on every WebSocket message, not just on the initial connection upgrade. This ensures that token expiration or revocation mid-conversation is enforced. |

**Authentication flow:**
1. Frontend redirects unauthenticated users to Keycloak login page.
2. Keycloak authenticates and returns an OIDC token with role claims.
3. Frontend stores token and includes it in all API requests.
4. FastAPI middleware validates the token against Keycloak's public key (JWKS cached for 5 minutes, re-fetched on verification failure).
5. Role is extracted from token claims and injected into the request context.
6. Prospect routes bypass authentication entirely -- no login required.

### 4.2 RBAC Enforcement

Authorization is enforced at three layers:

**Layer 1: API Gateway (FastAPI middleware)**
- Route-level access: each endpoint declares which roles can access it.
- Data scope injection: for role-scoped data (LO sees own pipeline only), the middleware injects a filter into the request context.
- PII masking: for the CEO role, response middleware masks sensitive fields before the response is sent.

**Layer 2: Domain Services**
- Services receive `user_context` and re-apply data scope filters.
- This is defense in depth -- even if a middleware bug skips scope injection, the service layer blocks unauthorized data access.

**Layer 3: Agent Layer**
- Each agent's tool registry is fixed per role. The agent runtime checks role before executing any tool.
- Output filtering scans agent responses for data that should not be visible to the user's role.

**Data access matrix:**

| Data Type | Prospect | Borrower | Loan Officer | Underwriter | CEO |
|-----------|----------|----------|-------------|-------------|-----|
| Public product info | Read | Read | Read | Read | Read |
| Own application data | -- | Read/Write | -- | -- | -- |
| Pipeline (own) | -- | -- | Read/Write | -- | -- |
| Pipeline (all) | -- | -- | -- | Read (UW queue: R/W) | Read (masked PII) |
| Documents (content) | -- | Own only | Pipeline only | Full pipeline | Metadata only (enforced at API, service, and query layers -- see below) |
| HMDA demographics | -- | -- | -- | -- | Aggregates only |
| Audit trail | -- | -- | -- | Read | Read (masked PII) |
| Conversation history | -- | Own only | Own only | Own only | Own only |
| Analytics/aggregates | -- | -- | -- | -- | Read |

**CEO document access enforcement (multi-layer):**

| Layer | Mechanism |
|-------|-----------|
| API endpoint | `/api/documents/{id}/content` returns 403 for requests with the CEO role. The CEO can access `/api/documents/{id}` (metadata) but not the content sub-resource. |
| Service method | `DocumentService.get_content()` raises an authorization exception if the caller's `user_context.role` is `ceo`. Defense-in-depth against gateway bypass. |
| Query layer | Queries executed on behalf of the CEO role exclude content columns (`file_path`, `raw_content`) from the SELECT projection. |
| Audit trail | When audit events reference a document (via `source_document_id`), the CEO sees the document reference (that a document was involved) but the audit response does not inline document content. The CEO can see that "W-2 for borrower was reviewed" but not the W-2 content. |

### 4.3 Agent Security

See [ADR-0005: Agent Security Architecture](#adr-0005-agent-security-architecture).

The agent security architecture addresses three threat vectors:

1. **Prompt injection** -- Adversarial user input that attempts to manipulate the agent into bypassing guardrails, accessing unauthorized data, or producing harmful output.
2. **Tool misuse** -- Attempts to invoke tools outside the user's authorized scope, either through prompt manipulation or through direct API exploitation.
3. **Data leakage** -- Agent responses that inadvertently include data the user should not see (HMDA data in lending responses, other users' data, unmasked PII for CEO).

**Defense layers:**

| Layer | Threat | Mechanism |
|-------|--------|-----------|
| Input validation | Prompt injection | Pattern detection on user input before agent processing. Known adversarial patterns (role-play attacks, instruction override attempts, system prompt extraction) are detected and rejected. Rejected inputs are logged. |
| System prompt hardening | Prompt injection | Agent system prompts include explicit refusal instructions for out-of-scope requests. For lending agents: "You do not have access to demographic data. If asked, refuse and explain that HMDA data is isolated." |
| Tool authorization | Tool misuse | A LangGraph pre-tool node checks `user_role in tool.allowed_roles` immediately before each invocation. Role is read from JWT claims (staleness bounded by 15-minute access token lifetime). Auth results are not cached across turns. On failure: tool returns authorization error, agent communicates restriction, audit trail records attempt. |
| Output filtering | Data leakage | A post-processing step scans the agent response for patterns matching sensitive data (SSN format, HMDA data references) and semantic checks for demographic proxy references (neighborhood-level demographic composition, proxy characteristics). Matches trigger response redaction and audit logging. PoC uses pattern matching; production would use ML-based semantic detection. |
| Fair lending guardrails | Bias/discrimination | Lending agents actively refuse to consider protected characteristics. Proxy discrimination awareness flags queries involving factors that correlate with protected classes (ZIP codes, neighborhood names). |

## 5. Knowledge Base Architecture

### 5.1 Three-Tier Compliance Knowledge Base

The compliance knowledge base is a RAG pipeline that serves the Underwriter and Loan Officer agents with regulatory, guideline, and policy information.

**Architecture:**

```
Source Documents (Markdown/PDF)
        |
        v
Ingestion Pipeline
  - Chunk with overlap (512 tokens, 64 token overlap)
  - Tag with tier, source doc, section ref
  - Generate embedding (via LlamaStack embedding endpoint)
  - Store in pgvector
        |
        v
kb_chunks table (pgvector)
  - chunk_text: text
  - embedding: vector(dim)
  - tier: int (1=federal, 2=agency, 3=internal)
  - source_document: text
  - section_ref: text
        |
        v
Search (at query time)
  - Embed user query
  - Vector similarity search
  - Apply tier precedence boost
  - Return top-k results with citations
```

**Tier precedence in search:** Results from all three tiers are retrieved by vector similarity. A tier boost factor is applied to the similarity score (tier 1 gets the highest boost), so that regulatory citations outrank guideline citations of similar semantic relevance. If a query returns conflicting information from different tiers, the response notes the conflict and defers to the higher tier.

**Content management:** Source documents live in a dedicated directory (`data/compliance-kb/`) organized by tier. A CLI command rebuilds the vector index from source documents. This is a batch operation, not a real-time pipeline -- appropriate for PoC where compliance content changes infrequently.

### 5.2 OpenShift AI Integration Point

In an OpenShift AI deployment, the KB ingestion pipeline can run as a data science pipeline (Kubeflow/Tekton-based), providing a managed environment for document processing, embedding generation, and index building. This is a production deployment pattern -- local development uses the CLI command.

## 6. Model Serving and Routing

### 6.1 LlamaStack Abstraction

See [ADR-0004: LlamaStack Abstraction Layer](#adr-0004-llamastack-abstraction-layer).

LlamaStack serves as the model serving abstraction layer, providing a consistent inference interface regardless of the underlying model provider. The application code interacts with LlamaStack's Python client SDK; the LlamaStack server handles provider-specific routing.

**Architecture:**

```
Agent Layer (LangGraph)
        |
        | LlamaStack Python SDK
        v
LlamaStack Server (container)
        |
        | Provider-specific protocol
        v
Model Endpoint (vLLM, Ollama, OpenShift AI, OpenAI-compatible)
```

**Why LlamaStack, not direct OpenAI SDK:**
- Stakeholder mandate.
- Provides a single integration point for model serving that abstracts provider differences.
- Supports both local development (Ollama, vLLM) and production (OpenShift AI model serving) without code changes -- only configuration changes.
- Exposes OpenAI-compatible endpoints at `/v1`, so tools and libraries that expect OpenAI endpoints work without modification.

**Isolation principle:** Business logic and agent code import only from a thin application-level inference interface. This interface wraps the LlamaStack client SDK. If LlamaStack is replaced in the future, only the wrapper changes -- no business logic or agent code is modified.

### 6.2 Model Routing (F21)

Model routing selects different models based on query complexity. The router is a LangGraph node that runs before the main agent graph.

**Routing strategy:**

| Query Complexity | Characteristics | Model Tier | Examples |
|-----------------|----------------|------------|---------|
| Simple | Factual lookup, status check, simple calculation | Fast/Small | "What is my application status?", "When does my rate lock expire?" |
| Complex | Multi-step reasoning, tool orchestration, compliance analysis, document extraction | Capable/Large | "Give me a risk assessment", "Draft conditions for this application", "Are there disparate impact concerns?" |

**Implementation:** The router is a lightweight classifier (could be rule-based at PoC, LLM-based for production) that examines the user query and conversation context, then sets the model parameter for the downstream agent invocation.

**Configuration:** Model endpoints and routing rules are defined in configuration (`config/models.yaml`). Each model entry specifies the LlamaStack provider, model name, and routing criteria. This makes the routing transparent in the observability dashboard (F18) and configurable by Quickstart users. Changes to `config/models.yaml` are hot-reloaded per-conversation without restart (see Section 9.3).

### 6.3 Model Health Monitoring (F39)

Model health metrics -- latency percentiles, token usage, error rates, and model routing distribution -- are collected via LangFuse callbacks that are already attached to every agent invocation (see Section 8.4). These metrics are surfaced in a lightweight monitoring overlay on the CEO dashboard. No additional monitoring infrastructure, agents, or containers are required. The data flow is: LangFuse callback captures per-call metrics -> LangFuse stores in ClickHouse -> FastAPI proxies LangFuse API queries -> frontend renders the monitoring panel.

### 6.4 OpenShift AI Model Serving

In an OpenShift AI deployment, model serving is provided by the platform (KServe with vLLM or Caikit-TGIS serving runtimes). LlamaStack is configured to point to OpenShift AI model serving endpoints instead of local endpoints. No application code changes are required -- only the LlamaStack server configuration (`run.yaml`) changes.

**Natural integration:** Different model sizes (fast/small for simple queries, capable/large for complex reasoning) can be served from separate OpenShift AI InferenceService instances, naturally supporting the model routing architecture.

## 7. Deployment Architecture

### 7.1 Deployment Modes

See [ADR-0007: Deployment Architecture](#adr-0007-deployment-architecture).

The application supports two deployment modes that share the same application code:

| Aspect | Local Development | OpenShift AI Production |
|--------|------------------|------------------------|
| Orchestration | Compose (podman-compose / docker compose) | Helm charts |
| Model serving | LlamaStack + Ollama/vLLM (local) or remote endpoint | LlamaStack + OpenShift AI InferenceService |
| Database | PostgreSQL container | Managed PostgreSQL or OpenShift-deployed |
| Object storage | Local filesystem mount | S3-compatible (OpenShift Data Foundation / MinIO) |
| Identity provider | Keycloak container | Keycloak Operator or existing enterprise IdP |
| Observability | LangFuse container | LangFuse container + OpenShift AI model monitoring |
| Networking | localhost ports | Kubernetes Services + Routes/Ingress |

### 7.2 Container Inventory (Compose)

The local development stack uses `compose.yml` (Compose Spec format). The default runtime is `podman-compose` (Red Hat alignment); `docker compose` is a compatible alternative. The Makefile uses a configurable variable (`COMPOSE ?= podman-compose`).

```yaml
services:
  ui:              # React app (nginx)
  api:             # FastAPI application
  keycloak:        # Identity provider          [profile: auth]
  postgres:        # PostgreSQL + pgvector
  llamastack:      # LlamaStack server          [profile: ai]
  langfuse-web:    # LangFuse web UI            [profile: observability]
  langfuse-worker: # LangFuse event worker      [profile: observability]
  redis:           # LangFuse cache             [profile: observability]
  clickhouse:      # LangFuse analytics storage [profile: observability]
```

**Compose profiles:** The full 9-service stack is heavy (minimum 8 GB RAM). Profiles allow developers to start with a lighter stack and add services as needed:

| Profile | Services | Use Case |
|---------|----------|----------|
| Default (no profile) | postgres, api, ui | Minimal for non-AI development |
| `--profile ai` | + llamastack | Adds AI agent capability |
| `--profile auth` | + keycloak | Adds authentication |
| `--profile observability` | + langfuse-web, langfuse-worker, redis, clickhouse | Adds observability |
| `--profile full` | All services | Full stack |

**Keycloak database:** Keycloak uses its embedded H2 database for PoC (not the application PostgreSQL). The pre-configured realm import file (`summit-cap-realm.json`) is loaded on Keycloak startup, making Keycloak's state fully reproducible without persistent storage. This avoids coupling Keycloak to the application database and simplifies the startup sequence.

**Startup order:** PostgreSQL -> Redis -> ClickHouse -> Keycloak (independent, uses embedded H2) -> LangFuse -> LlamaStack -> API -> UI. Compose health checks enforce ordering.

**Single-command setup (F22):** `make run` (or equivalent) executes: (1) pull/build containers, (2) start services in order, (3) wait for health checks, (4) run database migrations, (5) optionally seed demo data based on configuration flag, (6) print access URLs. Target: under 10 minutes with images pre-pulled, excluding model download time.

**Model download note:** Local inference requires downloading model weights. This is a one-time cost that cannot be included in the 10-minute setup target. The setup documentation clearly separates "first-time setup with model download" from "subsequent startup" times. Remote inference mode (pointing to an external endpoint) avoids this entirely.

**Graceful degradation:**

| Service | Required? | Behavior When Absent |
|---------|-----------|---------------------|
| PostgreSQL | Required | Application cannot start. All data storage depends on it. |
| Keycloak | Required | Authentication fails. No user can log in. API rejects all authenticated requests (fail-closed). |
| API | Required | No backend functionality. UI shows connection error. |
| UI | Required | No user interface. API is still accessible for development/testing via curl. |
| LlamaStack | Conditional | Required for AI agent functionality. If unavailable, chat endpoints return "AI service unavailable" errors. Non-chat API operations (document upload, application status) continue to function. Required unless using remote inference endpoint directly. |
| LangFuse (web, worker) | Optional | Agent execution continues without observability tracing. The LangFuse callback handler degrades to a no-op with a warning log. No traces, token counts, or latency metrics are captured. |
| Redis | Optional | Required only by LangFuse. If absent, LangFuse fails to start but the application is unaffected. |
| ClickHouse | Optional | Required only by LangFuse. Same degradation as Redis. |

### 7.3 Resource Requirements

| Configuration | RAM | CPU | GPU | Disk |
|--------------|-----|-----|-----|------|
| Remote inference (API + services only) | 8 GB | 4 cores | None | 10 GB |
| Local inference (small model, e.g., 7B) | 16 GB | 8 cores | Optional (CPU inference) | 30 GB |
| Local inference (capable model, e.g., 70B) | 32+ GB | 8+ cores | Recommended (GPU) | 60+ GB |

### 7.4 OpenShift AI Natural Integration Points

Per stakeholder preference ("use where possible, showcase different aspects where it makes sense"), these OpenShift AI capabilities are leveraged:

| Capability | Application Integration | Notes |
|-----------|------------------------|-------|
| Model serving (KServe) | LlamaStack points to OpenShift AI InferenceService endpoints | Primary integration. Showcases production model serving. |
| S3-compatible storage (ODF/MinIO) | Document storage backend | Replaces local filesystem in production. |
| Data science pipelines | Compliance KB ingestion and embedding pipeline | Showcases ML pipeline capabilities for knowledge management. |
| Model monitoring (infra) | Complement LangFuse with infrastructure-level metrics | Additive -- GPU utilization, inference latency, serving health. |
| Model monitoring overlay (F39) | Lightweight dashboard panel using LangFuse-collected metrics for inference health visibility | Demonstrates operational observability without requiring a dedicated monitoring platform. |
| TrustyAI fairness metrics | `trustyai` Python library used by Compliance Service for SPD/DIR computation | Demonstrates OpenShift AI ecosystem integration at the algorithmic level. Used as a library dependency, not as a platform operator. |
| Namespace isolation | HMDA data path can run in a separate namespace | Defense-in-depth for HMDA isolation. Production enhancement. |

## 8. Integration Patterns

### 8.1 Synchronous Communication

**HTTP/REST** is used for all non-streaming interactions between the frontend and the API gateway. Standard request-response pattern with JSON payloads and Pydantic validation.

**Internal service calls** within the API process are direct Python function calls (not HTTP). The API gateway, agent layer, and domain services all run in the same FastAPI process. This avoids microservice overhead that is inappropriate for PoC maturity. The service boundaries are enforced by module structure and interface contracts, not by network boundaries.

**Monorepo build system:** Turborepo + pnpm orchestrate build, test, and lint tasks across the `packages/` workspace (ui, api, db, configs). The Makefile wraps turbo commands (e.g., `make test` calls `turbo run test`). Turborepo provides task caching and parallel execution across packages. Python packages (`packages/api/`, `packages/db/`) use uv + hatchling as the build tooling; TypeScript packages (`packages/ui/`, `packages/configs/`) use pnpm.

**Module boundary enforcement caveat:** Python module boundaries are convention, not runtime enforcement -- any module can import any other. For the HMDA isolation boundary (the most critical), two mitigations apply:

1. **Database-level enforcement:** The `lending_app` PostgreSQL role has no grants on the `hmda` schema, so even if code outside the Compliance Service attempts an HMDA query through the primary connection pool, the database rejects it.
2. **CI lint check:** A CI step verifies that no code outside `services/compliance/` references the `hmda` schema or imports the compliance connection pool. This is implemented as a `grep -r` check in the CI pipeline that fails the build on violation.

### 8.2 Streaming Communication

**WebSocket** is used for chat interactions. The flow:
1. Frontend opens a WebSocket connection to `/api/chat`.
2. The gateway authenticates the WebSocket upgrade request.
3. User messages are sent through the WebSocket.
4. The agent processes the message and streams tokens back through the WebSocket.
5. Tool call results, status updates, and final responses are sent as structured messages.

**Message protocol (WebSocket):**
```
Client -> Server: { "type": "message", "content": "..." }
Server -> Client: { "type": "token", "content": "..." }           # streaming token
Server -> Client: { "type": "tool_call", "name": "...", "args": {...} }  # tool invocation
Server -> Client: { "type": "tool_result", "name": "...", "result": {...} }
Server -> Client: { "type": "done" }                               # completion signal
Server -> Client: { "type": "error", "message": "..." }            # error
```

**Reconnection strategy:** The frontend reconnects automatically on WebSocket disconnection using exponential backoff. Conversation state is recoverable from the LangGraph checkpoint, so a dropped connection does not lose conversation context. On reconnection, the client sends the last known event ID to avoid duplicate messages. SSE is not used at PoC maturity; it is noted as a production upgrade path if WebSocket proves problematic in certain deployment environments (e.g., restrictive corporate proxies).

### 8.3 Document Upload

Document upload uses multipart form POST to `/api/documents/upload`. The API gateway:
1. Authenticates and authorizes the request.
2. Stores the raw file to object storage.
3. Creates a document metadata record in PostgreSQL.
4. Queues the document for async processing (extraction + quality assessment).
5. Returns immediately with the document ID and "processing" status.
6. Processing status is available via a polling endpoint (`GET /api/documents/{id}/status`). The frontend polls this endpoint to track document processing progress. Additionally, the Borrower agent has access to document status through the `document_status` tool, so processing results are surfaced naturally when the user next interacts with the chat.

At PoC maturity, "async processing" is a simple background task within the FastAPI process (using `asyncio`), not a full message queue. The interface supports upgrading to a proper queue (Redis/Celery) for production.

### 8.4 Observability Integration

LangFuse integration uses the LangChain/LangGraph callback handler (`langfuse.callback.CallbackHandler`). The handler is injected into every agent invocation, capturing:
- Agent execution traces (each node in the LangGraph)
- Tool calls with parameters and results
- LLM calls with prompts, completions, token counts, and latency
- Model selection (which model handled each call)

LangFuse traces are linked to application audit events through a shared `session_id`, allowing correlation between the developer-facing observability view and the compliance-facing audit trail.

## 9. Cross-Cutting Concerns

### 9.1 Observability

**Three observability surfaces:**

| Surface | Audience | Tool | Content |
|---------|----------|------|---------|
| LangFuse dashboard | Developers/operators | LangFuse (self-hosted) | Agent traces, LLM calls, token usage, latency |
| In-app audit trail | CEO, Underwriter | Application UI | Decision traceability, compliance events, override tracking |
| Application logs | Developers/operators | Structured JSON logging | Request lifecycle, errors, system events |

**Structured logging:** All application logs use structured JSON format with standard fields (timestamp, level, request_id, user_id, service, message). Log correlation uses a request ID that propagates through the API gateway, domain services, and agent layer.

### 9.2 Error Handling

**PoC-level error handling strategy:**
- Domain service errors return structured error responses with error codes and human-readable messages.
- Agent errors (LLM failures, tool failures) are caught and surfaced to the user as "I encountered an issue" messages through the chat interface, with full details logged.
- LlamaStack/model serving errors trigger fallback messaging: "The AI service is temporarily unavailable."
- Database errors are logged and return generic server errors. No database error details are exposed to users.
- Document processing errors are recorded as document metadata (quality flags) and communicated to the user through the chat interface.

### 9.3 Configuration Management

Configuration is organized in layers:

| Layer | Content | Format | Examples |
|-------|---------|--------|---------|
| Infrastructure | Database URLs, Keycloak URLs, LlamaStack endpoints | Environment variables | `DATABASE_URL`, `KEYCLOAK_URL`, `LLAMASTACK_URL` |
| Application | Feature flags, demo data toggle, PII masking rules | YAML config file | `config/app.yaml` |
| Agent | System prompts, tool registries, model routing rules | YAML config files | `config/agents/*.yaml` |
| Compliance KB | Source documents, tier definitions | Files + YAML manifest | `data/compliance-kb/manifest.yaml` |

**Environment variable precedence:** Environment variables override YAML config values. This supports container deployment where environment-specific values are injected at runtime.

**Configuration hot-reload (live demo support):** Agent configuration files (`config/agents/*.yaml`) and the model routing configuration (`config/models.yaml`) support hot-reload: changes to these files take effect on the next new conversation without an application restart. This enables live extensibility demos where a presenter modifies agent behavior on stage.

The reload uses a per-conversation staleness check, not filesystem watchers. At conversation start, the application compares each config file's `os.stat().st_mtime` against the mtime recorded when the config was last successfully loaded. If any file has a newer mtime, the application re-reads and re-validates the changed file(s). The `ModelRouter` and agent registry are reconstructed from the new config. Existing in-progress conversations continue using the config snapshot they started with -- only new conversations pick up changes.

If a reloaded config file contains a YAML syntax error or fails validation, the reload is rejected: the application logs a warning with the file path and error detail, retains the last successfully loaded config, and serves new conversations with that config. The mtime is not updated on failure, so the next conversation re-attempts the reload. This ensures a typo during a live demo degrades to "change not applied" rather than "application broken."

Infrastructure configuration (environment variables, database URLs, Keycloak endpoints), application configuration (`config/app.yaml`), and compliance KB content are NOT hot-reloadable. Infrastructure and application config change between environments, not during demos. Compliance KB requires re-embedding, which is a batch operation.

### 9.4 Demo Data Strategy

Demo data (F20) populates the same tables as live data. There is no separate "demo mode."

**Seeded volume:** 5-10 active borrowers with in-progress applications across pipeline stages, plus 15-25 historical completed loans providing 6+ months of trend data for CEO analytics and fair lending metrics.

**Seeding mechanism:** A CLI command (`python -m summit_cap.seed`) or API endpoint (`POST /api/admin/seed`) runs the seeding script. The script:
1. Checks if data already exists (idempotent -- does not re-seed if data is present).
2. Creates demo users in Keycloak via the admin API.
3. Inserts application, borrower, document, condition, decision, rate lock, and HMDA data.
4. Inserts historical loan data for CEO analytics (6+ months of trends).
5. Inserts sample conversation histories.
6. Records the seeding in `demo_data_manifest`.

**Empty state handling:** All UI views and AI agents handle empty data gracefully. The pipeline dashboard shows "No applications yet." The CEO dashboard shows empty charts with zero values. The AI assistant says "There are no applications in the system yet."

## 10. Project Structure

```
summit-cap-financial/
  compose.yml                        # Local development (podman-compose / docker compose)
  Makefile                           # make setup, dev, test, lint, deploy (wraps turbo)
  turbo.json                         # Turborepo pipeline config
  package.json                       # pnpm workspace root
  pnpm-workspace.yaml
  commitlint.config.js
  README.md
  config/
    app.yaml                         # Application configuration
    agents/                          # Per-agent configuration (prompts, tools, routing)
      public-assistant.yaml
      borrower-assistant.yaml
      lo-assistant.yaml
      underwriter-assistant.yaml
      ceo-assistant.yaml
    models.yaml                      # Model routing configuration
    keycloak/
      summit-cap-realm.json          # Pre-configured Keycloak realm
  data/
    compliance-kb/                   # Compliance knowledge base source documents
      tier1-federal/
      tier2-agency/
      tier3-internal/
      manifest.yaml
    demo/                            # Demo data seed files
      seed.json
  packages/
    ui/                              # React 19, Vite, TanStack Router/Query, shadcn/ui
      src/
        components/                  # Atomic design: atoms/, molecules/, organisms/
        routes/                      # TanStack Router file-based routes
        hooks/                       # TanStack Query wrappers
        services/                    # API client functions
        schemas/                     # Zod validation schemas
        styles/                      # Global CSS, Tailwind config
      .storybook/
      vitest.config.ts
    api/                             # FastAPI application
      src/summit_cap/
        main.py                      # FastAPI app entry point
        core/                        # Config, settings
        middleware/                   # Auth, RBAC, PII masking
        routes/                      # API route handlers
        agents/                      # LangGraph agent definitions
        services/                    # Domain services
          application/
          document/
          underwriting/
          compliance/
            knowledge_base/          # KB submodule (RAG pipeline)
          audit/
          analytics/
          conversation/
        inference/                   # LlamaStack wrapper
        schemas/                     # Pydantic request/response models
        admin.py                     # SQLAdmin configuration
      tests/
    db/                              # Database models and migrations (separate Python package)
      src/summit_cap_db/
        models/                      # SQLAlchemy models (all schemas)
        database.py                  # Engine, session, dual connection pools
      alembic/                       # Alembic migrations
      pyproject.toml
    configs/                         # Shared ESLint, Prettier, Ruff configs
  deploy/
    helm/                            # Helm charts for OpenShift deployment
      summit-cap-financial/
        Chart.yaml
        values.yaml
        templates/                   # api, ui, db, migration, keycloak, etc.
  tests/                             # Cross-package tests
    integration/
    e2e/
```

**Notable Python dependencies (beyond standard web stack):**

| Dependency | Used By | Purpose |
|-----------|---------|---------|
| `langgraph` | Agent layer | Agent orchestration, state management, checkpointing |
| `langchain-openai` | Agent layer | ChatOpenAI pointed at LlamaStack's `/v1` endpoint |
| `langfuse` | Observability | Callback handler for agent tracing, token tracking |
| `pgvector` | Compliance Service (knowledge base submodule) | Vector similarity search for compliance KB |
| `trustyai` | Compliance Service | SPD and DIR fairness metric computation on HMDA aggregate data |

## 11. Architecture Decision Records

Full ADRs are maintained in `plans/adr/`. Summaries and cross-references follow.

### ADR-0001: HMDA Data Isolation Architecture

**Decision:** Dual-data-path architecture with four-stage isolation (collection, extraction, storage, retrieval). HMDA data stored in a separate PostgreSQL schema. Compliance Service is the sole accessor, exposing only aggregates. Lending-path agents have no HMDA-querying tools.

**Reference:** `plans/adr/0001-hmda-data-isolation.md`

### ADR-0002: Database Selection

**Decision:** PostgreSQL 16 with pgvector extension as the single database. Handles relational data, append-only audit events, conversation checkpoints, and vector embeddings.

**Reference:** `plans/adr/0002-database-selection.md`

### ADR-0003: Frontend Framework Selection

**Decision:** React with Vite. Single SPA with role-based routing. No SSR. Amended to adopt TanStack Router, TanStack Query, shadcn/ui + Radix, and Vitest from the ai-quickstart-template.

**Reference:** `plans/adr/0003-frontend-framework.md`

### ADR-0004: LlamaStack Abstraction Layer

**Decision:** LlamaStack as the model serving abstraction, wrapped behind an application-level inference interface to prevent LlamaStack API leakage into business logic.

**Reference:** `plans/adr/0004-llamastack-abstraction.md`

### ADR-0005: Agent Security Architecture

**Decision:** Four-layer defense: input validation, system prompt hardening, tool authorization at execution time, and output filtering. Each layer is independently testable.

**Reference:** `plans/adr/0005-agent-security.md`

### ADR-0006: Audit Trail Architecture

**Decision:** Append-only PostgreSQL table with INSERT+SELECT-only grants, database trigger rejection of UPDATE/DELETE, sequential IDs, and hash chain tamper evidence.

**Reference:** `plans/adr/0006-audit-trail.md`

### ADR-0007: Deployment Architecture

**Decision:** Compose (podman-compose / docker compose) for local development, Helm charts for OpenShift AI production. Compose profiles for service subsets. Same application code, different infrastructure configuration. Amended from Kustomize to Helm for cross-quickstart consistency with the ai-quickstart-template.

**Reference:** `plans/adr/0007-deployment.md`

## 12. Open Questions

| ID | Question | Impact | Owner | Stakeholder Input |
|----|----------|--------|-------|-------------------|
| OQ-A1 | Embedding model selection for compliance KB -- which embedding model to use with LlamaStack for the RAG pipeline? Affects vector dimensions and search quality. | Medium -- affects KB search quality | Tech Lead | Prefer a Granite model appropriate for embedding. |
| OQ-A2 | LangGraph checkpoint storage adapter -- does LangGraph's PostgreSQL checkpointer meet the cross-session memory requirements, or do we need a custom adapter? | Low -- verify during Phase 1 implementation | Tech Lead | Tech Lead's judgment. |
| OQ-A3 | Document extraction model -- should document extraction use the same LLM as agent conversations, or a specialized model? Affects model routing configuration. | Medium -- affects extraction quality and latency | Tech Lead | Use whatever model is best for the purpose; a different specialized model is fine. |
| OQ-A4 | CEO dashboard charting library -- which React charting library for the executive dashboard? Affects bundle size and chart types available. | Low -- implementation detail for Phase 4a | Tech Lead | Tech Lead's recommendation. |

### OQ-A5: Compliance Knowledge Base Content Review Timeline

**Question:** When does the domain expert review of compliance KB content begin?

**Dependency:** Compliance KB content must be reviewed by a domain expert before Phase 4a coding begins. Phase 4a includes UW, Compliance, and CEO persona features (F9, F10, F11, F16, F17, F26, F38, F39) -- all of which depend on KB content. Phase 4b (container platform deployment, F23) is independent of KB content. Content with incorrect regulatory statements is the highest credibility risk for the Summit demo.

**Suggested timeline:**

| Milestone | Timing |
|-----------|--------|
| Content drafting (AI-drafted, parallel workstream) | During Phase 2 |
| Domain expert review session (60-90 min) | During Phase 3 |
| Content revisions applied | End of Phase 3 |
| Content loaded and tested | Phase 4a |

**Action needed from stakeholder:** Identify or begin sourcing a domain expert during Phase 1/2 so the review session can be scheduled during Phase 3.

## 13. Product Plan Consistency Notes

During architecture design, I verified the product plan against the architecture and found no inconsistencies. Specific verification points:

- **F14 RBAC enforcement at API layer** -- Architecture enforces RBAC at three layers (gateway, service, agent), satisfying the product plan requirement that RBAC is "not just frontend."
- **F25 HMDA four-stage isolation** -- Architecture implements all four stages (collection, extraction, storage, retrieval) as specified.
- **F15 append-only audit trail** -- Architecture uses database-level enforcement (role grants + triggers), satisfying the immutability requirement.
- **F19 memory isolation** -- Architecture uses `user_id` as a mandatory filter on all checkpoint queries.
- **F22 single-command setup** -- Architecture supports a Compose one-command startup with health check ordering.
- **F4 conversational-only with form fallback contingency** -- Architecture uses conversational intake as the primary path. A structured form fallback is an accepted contingency for sections where conversational-only proves too brittle. The frontend accommodates both paths.
- **F5 demographic data filtering in extraction** -- Architecture includes a dedicated filter step in the document processing pipeline.
- **CEO document access (F14)** -- Architecture restricts CEO to document metadata only; raw document content is not accessible.
- **Knowledge Base Service folded into Compliance Service** -- The Knowledge Base Service has been merged into the Compliance Service as a submodule (`services/compliance/knowledge_base/`). Rationale: the KB's sole consumers are compliance-adjacent agents (underwriter, loan officer for regulatory questions), and the previous "Knowledge Base Service" / "Document Service" naming caused confusion since they serve entirely different purposes (compliance KB search vs. borrower document management). All KB functionality (RAG pipeline, tier precedence, vector search, ingestion) is preserved; only the organizational relationship changed. The domain service count is now seven (Application, Document, Underwriting, Compliance, Audit, Analytics, Conversation).
- **Template alignment (v1.3)** -- Project structure, build tooling, deployment manifests, and frontend libraries align with the `rh-ai-quickstart/ai-quickstart-template` standard. ADR-0003 amended to adopt TanStack Router, TanStack Query, shadcn/ui, Vitest, and Storybook. ADR-0007 amended to adopt Helm charts over Kustomize and podman-compose as the default local runtime. Project layout adopts `packages/ui/` (not `packages/frontend/`), `packages/db/` (separate Python package), and `packages/configs/` (shared lint configs). Build system uses Turborepo + pnpm for monorepo orchestration, uv + hatchling for Python packages. Compose profiles allow running subsets of the 9-service stack. SQLAdmin adopted for dev-time database inspection.
