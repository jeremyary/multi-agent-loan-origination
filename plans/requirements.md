# Requirements: AI Banking Quickstart -- Summit Cap Financial

## How to Use This Document

This is the **master requirements document** (hub). It provides a complete index of all user stories, cross-cutting concerns, and dependencies, but **does not contain detailed acceptance criteria**. Full Given/When/Then acceptance criteria are in the chunk files.

**Document organization:**
- This file (the hub): Story map, state machine, cross-cutting concerns, dependencies, coverage validation
- Chunk files (the spokes): 15-30 stories each with full acceptance criteria

**Chunk files:**
- `plans/requirements-chunk-1-foundation.md` -- Phase 1 foundation features
- `plans/requirements-chunk-2-borrower.md` -- Phase 2 borrower persona features
- `plans/requirements-chunk-3-loan-officer.md` -- Phase 3 loan officer persona features
- `plans/requirements-chunk-4-underwriting.md` -- Phase 4a underwriting persona features
- `plans/requirements-chunk-5-executive.md` -- Phase 4a executive + Phase 4b deployment features

**Reading sequence:**
1. Read this hub document to understand the full scope, state model, and cross-cutting concerns
2. Read the chunk file for the feature area you're working on
3. Cross-reference story IDs when dependencies span chunks

## Story Map Table

All stories are listed here with their chunk file reference. Story ID format: `S-{phase}-{feature}-{number}`.

| Story ID | Title | Priority | Phase | Feature | Chunk File |
|----------|-------|----------|-------|---------|------------|
| S-1-F1-01 | Prospect accesses product information without login | P0 | 1 | F1 | chunk-1-foundation |
| S-1-F1-02 | Prospect uses affordability calculator | P0 | 1 | F1 | chunk-1-foundation |
| S-1-F1-03 | Prospect initiates prequalification chat | P0 | 1 | F1 | chunk-1-foundation |
| S-1-F2-01 | Authentication via Keycloak OIDC | P0 | 1 | F2 | chunk-1-foundation |
| S-1-F2-02 | Role-based access to persona UIs | P0 | 1 | F2 | chunk-1-foundation |
| S-1-F2-03 | Token refresh and session management | P0 | 1 | F2 | chunk-1-foundation |
| S-1-F14-01 | API-level RBAC enforcement | P0 | 1 | F14 | chunk-1-foundation |
| S-1-F14-02 | Data scope injection for LO pipeline | P0 | 1 | F14 | chunk-1-foundation |
| S-1-F14-03 | CEO PII masking enforcement | P0 | 1 | F14 | chunk-1-foundation |
| S-1-F14-04 | CEO document access restriction (metadata only) | P0 | 1 | F14 | chunk-1-foundation |
| S-1-F14-05 | Agent tool authorization at execution time | P0 | 1 | F14 | chunk-1-foundation |
| S-1-F18-01 | LangFuse callback integration | P0 | 1 | F18 | chunk-1-foundation |
| S-1-F18-02 | LangFuse dashboard displays agent traces | P0 | 1 | F18 | chunk-1-foundation |
| S-1-F18-03 | Trace-to-audit event correlation via session ID | P0 | 1 | F18 | chunk-1-foundation |
| S-1-F20-01 | Demo data seeding command | P0 | 1 | F20 | chunk-1-foundation |
| S-1-F20-02 | Demo data includes 5-10 active applications | P0 | 1 | F20 | chunk-1-foundation |
| S-1-F20-03 | Demo data includes 15-25 historical loans | P0 | 1 | F20 | chunk-1-foundation |
| S-1-F20-04 | Idempotent seeding (no duplicate data on re-run) | P0 | 1 | F20 | chunk-1-foundation |
| S-1-F20-05 | Empty state handling in all UIs | P0 | 1 | F20 | chunk-1-foundation |
| S-1-F21-01 | Model routing classifies query complexity | P0 | 1 | F21 | chunk-1-foundation |
| S-1-F21-02 | Simple queries route to fast/small model | P0 | 1 | F21 | chunk-1-foundation |
| S-1-F21-03 | Complex queries route to capable/large model | P0 | 1 | F21 | chunk-1-foundation |
| S-1-F21-04 | Model routing configuration in config/models.yaml | P0 | 1 | F21 | chunk-1-foundation |
| S-1-F22-01 | Single command starts full stack | P0 | 1 | F22 | chunk-1-foundation |
| S-1-F22-02 | Health checks enforce service startup order | P0 | 1 | F22 | chunk-1-foundation |
| S-1-F22-03 | Setup completes in under 10 minutes (images pre-pulled) | P0 | 1 | F22 | chunk-1-foundation |
| S-1-F22-04 | Compose profiles support subset stack configurations | P0 | 1 | F22 | chunk-1-foundation |
| S-1-F25-01 | HMDA collection endpoint writes to isolated schema | P0 | 1 | F25 | chunk-1-foundation |
| S-1-F25-02 | PostgreSQL role separation (lending_app / compliance_app) | P0 | 1 | F25 | chunk-1-foundation |
| S-1-F25-03 | Demographic data filter in document extraction pipeline | P0 | 1 | F25 | chunk-1-foundation |
| S-1-F25-04 | Compliance Service is sole HMDA accessor | P0 | 1 | F25 | chunk-1-foundation |
| S-1-F25-05 | CI lint check prevents HMDA schema access outside Compliance Service | P0 | 1 | F25 | chunk-1-foundation |
| S-2-F3-01 | Borrower initiates new application via chat | P0 | 2 | F3 | chunk-2-borrower |
| S-2-F3-02 | Borrower provides application data conversationally | P0 | 2 | F3 | chunk-2-borrower |
| S-2-F3-03 | Agent validates data format and completeness | P0 | 2 | F3 | chunk-2-borrower |
| S-2-F3-04 | Borrower can review and correct collected data | P0 | 2 | F3 | chunk-2-borrower |
| S-2-F3-05 | Form fallback for complex financial data entry (contingency) | P0 | 2 | F3 | chunk-2-borrower |
| S-2-F4-01 | Borrower uploads documents through chat | P0 | 2 | F4 | chunk-2-borrower |
| S-2-F4-02 | Document upload stores raw file to object storage | P0 | 2 | F4 | chunk-2-borrower |
| S-2-F4-03 | Document processing status visible to borrower | P0 | 2 | F4 | chunk-2-borrower |
| S-2-F4-04 | Agent notifies borrower when document processing completes | P0 | 2 | F4 | chunk-2-borrower |
| S-2-F5-01 | Document extraction produces structured data | P0 | 2 | F5 | chunk-2-borrower |
| S-2-F5-02 | Quality assessment flags blurry/incomplete/incorrect documents | P0 | 2 | F5 | chunk-2-borrower |
| S-2-F5-03 | Demographic data filter excludes HMDA data from lending path | P0 | 2 | F5 | chunk-2-borrower |
| S-2-F5-04 | Exclusion events logged to audit trail | P0 | 2 | F5 | chunk-2-borrower |
| S-2-F6-01 | Agent identifies missing documents | P0 | 2 | F6 | chunk-2-borrower |
| S-2-F6-02 | Agent proactively requests missing documents | P0 | 2 | F6 | chunk-2-borrower |
| S-2-F6-03 | Agent flags outdated documents (freshness check) | P0 | 2 | F6 | chunk-2-borrower |
| S-2-F15-01 | Audit event written for every AI action | P0 | 2 | F15 | chunk-2-borrower |
| S-2-F15-02 | Audit events are append-only (no UPDATE/DELETE grants) | P0 | 2 | F15 | chunk-2-borrower |
| S-2-F15-03 | Database trigger rejects UPDATE/DELETE on audit_events | P0 | 2 | F15 | chunk-2-borrower |
| S-2-F15-04 | Hash chain provides tamper evidence | P0 | 2 | F15 | chunk-2-borrower |
| S-2-F15-05 | Advisory lock ensures serial hash chain computation | P0 | 2 | F15 | chunk-2-borrower |
| S-2-F19-01 | Borrower conversation persists across sessions | P0 | 2 | F19 | chunk-2-borrower |
| S-2-F19-02 | Conversation checkpoints filtered by user_id | P0 | 2 | F19 | chunk-2-borrower |
| S-2-F19-03 | Post-retrieval verification of checkpoint user_id | P0 | 2 | F19 | chunk-2-borrower |
| S-2-F19-04 | No cross-user checkpoint access (including CEO/admin) | P0 | 2 | F19 | chunk-2-borrower |
| S-2-F27-01 | Borrower views current rate lock status | P0 | 2 | F27 | chunk-2-borrower |
| S-2-F27-02 | Rate lock data stored as first-class application data | P0 | 2 | F27 | chunk-2-borrower |
| S-2-F27-03 | Agent alerts borrower when rate lock nears expiration | P0 | 2 | F27 | chunk-2-borrower |
| S-2-F28-01 | Borrower responds to underwriting conditions via chat | P0 | 2 | F28 | chunk-2-borrower |
| S-2-F28-02 | Borrower uploads documents to satisfy conditions | P0 | 2 | F28 | chunk-2-borrower |
| S-2-F28-03 | Agent confirms condition satisfaction or requests clarification | P0 | 2 | F28 | chunk-2-borrower |
| S-3-F7-01 | LO views pipeline with urgency indicators | P0 | 3 | F7 | chunk-3-loan-officer |
| S-3-F7-02 | Pipeline filtered to LO's own assigned applications | P0 | 3 | F7 | chunk-3-loan-officer |
| S-3-F7-03 | Urgency based on rate lock expiration and stage timing | P0 | 3 | F7 | chunk-3-loan-officer |
| S-3-F7-04 | LO clicks application to view detail | P0 | 3 | F7 | chunk-3-loan-officer |
| S-3-F8-01 | LO reviews application detail in chat interface | P0 | 3 | F8 | chunk-3-loan-officer |
| S-3-F8-02 | LO reviews document quality flags and extraction results | P0 | 3 | F8 | chunk-3-loan-officer |
| S-3-F8-03 | LO submits application to underwriting via agent tool | P0 | 3 | F8 | chunk-3-loan-officer |
| S-3-F8-04 | Submission triggers application state transition | P0 | 3 | F8 | chunk-3-loan-officer |
| S-3-F24-01 | LO drafts borrower communication via agent | P0 | 3 | F24 | chunk-3-loan-officer |
| S-3-F24-02 | Agent incorporates application context into draft | P0 | 3 | F24 | chunk-3-loan-officer |
| S-3-F24-03 | LO reviews and edits before sending | P0 | 3 | F24 | chunk-3-loan-officer |
| S-4-F9-01 | Underwriter views full underwriting queue | P0 | 4a | F9 | chunk-4-underwriting |
| S-4-F9-02 | Underwriter selects application for review | P0 | 4a | F9 | chunk-4-underwriting |
| S-4-F9-03 | Agent performs risk assessment via tool call | P0 | 4a | F9 | chunk-4-underwriting |
| S-4-F9-04 | Risk assessment includes DTI, LTV, credit factors | P0 | 4a | F9 | chunk-4-underwriting |
| S-4-F9-05 | Agent provides preliminary recommendation | P0 | 4a | F9 | chunk-4-underwriting |
| S-4-F10-01 | Agent searches compliance KB for regulatory guidance | P0 | 4a | F10 | chunk-4-underwriting |
| S-4-F10-02 | Search results include tier precedence (federal > agency > internal) | P0 | 4a | F10 | chunk-4-underwriting |
| S-4-F10-03 | Search results include source citations (document, section) | P0 | 4a | F10 | chunk-4-underwriting |
| S-4-F10-04 | Conflicting results across tiers are flagged | P0 | 4a | F10 | chunk-4-underwriting |
| S-4-F11-01 | Agent checks ECOA compliance (no demographic use in decision) | P0 | 4a | F11 | chunk-4-underwriting |
| S-4-F11-02 | Agent checks ATR/QM compliance (ability-to-repay) | P0 | 4a | F11 | chunk-4-underwriting |
| S-4-F11-03 | Agent checks TRID disclosure requirements | P0 | 4a | F11 | chunk-4-underwriting |
| S-4-F11-04 | Compliance check results include pass/fail per regulation | P0 | 4a | F11 | chunk-4-underwriting |
| S-4-F11-05 | Agent refuses to proceed if Critical compliance failure | P0 | 4a | F11 | chunk-4-underwriting |
| S-4-F16-01 | Underwriter issues conditions via agent | P0 | 4a | F16 | chunk-4-underwriting |
| S-4-F16-02 | Conditions include description, severity, and required response | P0 | 4a | F16 | chunk-4-underwriting |
| S-4-F16-03 | Conditions transition through lifecycle states (issued > responded > cleared) | P0 | 4a | F16 | chunk-4-underwriting |
| S-4-F16-04 | Underwriter clears or escalates condition responses | P0 | 4a | F16 | chunk-4-underwriting |
| S-4-F17-01 | Underwriter renders approval decision | P0 | 4a | F17 | chunk-4-underwriting |
| S-4-F17-02 | Underwriter renders denial decision | P0 | 4a | F17 | chunk-4-underwriting |
| S-4-F17-03 | Denial triggers adverse action data capture | P0 | 4a | F17 | chunk-4-underwriting |
| S-4-F17-04 | Agent drafts adverse action notice | P0 | 4a | F17 | chunk-4-underwriting |
| S-4-F17-05 | Decision includes rationale and AI recommendation comparison | P0 | 4a | F17 | chunk-4-underwriting |
| S-4-F26-01 | Agent detects prompt injection patterns and rejects | P0 | 4a | F26 | chunk-4-underwriting |
| S-4-F26-02 | Agent output filter scans for HMDA data leakage | P0 | 4a | F26 | chunk-4-underwriting |
| S-4-F26-03 | Agent output filter scans for demographic proxy references | P0 | 4a | F26 | chunk-4-underwriting |
| S-4-F26-04 | Security events logged to audit trail | P0 | 4a | F26 | chunk-4-underwriting |
| S-4-F38-01 | Compliance Service computes SPD metric on HMDA aggregate data | P0 | 4a | F38 | chunk-4-underwriting |
| S-4-F38-02 | Compliance Service computes DIR metric on HMDA aggregate data | P0 | 4a | F38 | chunk-4-underwriting |
| S-4-F38-03 | Fairness metrics use trustyai Python library | P0 | 4a | F38 | chunk-4-underwriting |
| S-4-F38-04 | Metrics exposed only as pre-aggregated statistics | P0 | 4a | F38 | chunk-4-underwriting |
| S-5-F12-01 | CEO views pipeline summary (volume, stages, turn times) | P0 | 4a | F12 | chunk-5-executive |
| S-5-F12-02 | CEO views denial rate trends over time | P0 | 4a | F12 | chunk-5-executive |
| S-5-F12-03 | CEO views fair lending metrics (SPD, DIR) | P0 | 4a | F12 | chunk-5-executive |
| S-5-F12-04 | CEO views LO performance metrics | P0 | 4a | F12 | chunk-5-executive |
| S-5-F12-05 | All metrics use masked PII (names visible, SSN/DOB hidden) | P0 | 4a | F12 | chunk-5-executive |
| S-5-F13-01 | CEO queries audit trail by application ID | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-02 | CEO queries audit trail by decision ID | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-03 | CEO queries audit trail by time range and event type | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-04 | Audit responses include masked PII | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-05 | Audit trail supports backward tracing from decision | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-06 | CEO asks pipeline and performance questions | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-07 | CEO asks comparative questions | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-08 | CEO asks about specific LO or application by name | P0 | 4a | F13 | chunk-5-executive |
| S-5-F13-09 | CEO asks fair lending questions | P0 | 4a | F13 | chunk-5-executive |
| S-2-F6-04 | Borrower asks application status | P0 | 2 | F6 | chunk-2-borrower |
| S-2-F6-05 | Agent notes approaching regulatory deadlines | P0 | 2 | F6 | chunk-2-borrower |
| S-2-F15-06 | Borrower acknowledges disclosures during application | P0 | 2 | F15 | chunk-2-borrower |
| S-5-F15-07 | Authorized user exports audit trail data | P0 | 4a | F15 | chunk-5-executive |
| S-4-F17-06 | Loan Estimate document generation | P0 | 4a | F17 | chunk-4-underwriting |
| S-4-F17-07 | Closing Disclosure document generation | P0 | 4a | F17 | chunk-4-underwriting |
| S-5-F23-01 | Helm chart deploys API, UI, DB, Keycloak, LlamaStack, LangFuse | P0 | 4b | F23 | chunk-5-executive |
| S-5-F23-02 | Helm values.yaml supports environment-specific overrides | P0 | 4b | F23 | chunk-5-executive |
| S-5-F23-03 | DB migration runs as init container | P0 | 4b | F23 | chunk-5-executive |
| S-5-F23-04 | LlamaStack configured to use OpenShift AI InferenceService endpoints | P0 | 4b | F23 | chunk-5-executive |
| S-5-F23-05 | Object storage configured to use S3-compatible backend (ODF/MinIO) | P0 | 4b | F23 | chunk-5-executive |
| S-5-F39-01 | CEO dashboard displays model latency percentiles | P0 | 4a | F39 | chunk-5-executive |
| S-5-F39-02 | CEO dashboard displays token usage | P0 | 4a | F39 | chunk-5-executive |
| S-5-F39-03 | CEO dashboard displays error rates | P0 | 4a | F39 | chunk-5-executive |
| S-5-F39-04 | CEO dashboard displays model routing distribution | P0 | 4a | F39 | chunk-5-executive |
| S-5-F39-05 | Metrics sourced from LangFuse via API proxy | P0 | 4a | F39 | chunk-5-executive |

**Story count per chunk:**
- Chunk 1 (Foundation): 32 stories
- Chunk 2 (Borrower): 34 stories
- Chunk 3 (Loan Officer): 11 stories
- Chunk 4 (Underwriting): 33 stories
- Chunk 5 (Executive): 25 stories
- **Total: 135 stories**

## Application State Machine

Mortgage applications transition through a defined lifecycle. Each state represents a distinct stage of processing.

**States:**

| State | Description | Allowed Transitions |
|-------|-------------|-------------------|
| `prospect` | Initial inquiry, no formal application yet | → `application` |
| `application` | Formal application initiated, data collection in progress | → `underwriting`, → `withdrawn` |
| `underwriting` | Application submitted to underwriting review | → `conditional_approval`, → `denied`, → `application` (returned for corrections) |
| `conditional_approval` | Approved with conditions issued | → `final_approval`, → `denied` (if conditions not satisfied) |
| `final_approval` | All conditions cleared, approved for closing | → `closing` |
| `closing` | Loan in closing process | → `closed`, → `withdrawn` |
| `closed` | Loan funded and closed | (terminal state) |
| `denied` | Application denied | (terminal state) |
| `withdrawn` | Borrower withdrew application | (terminal state) |

**Role permissions per transition:**

| Transition | Permitted Roles | Notes |
|------------|----------------|-------|
| `prospect` → `application` | Borrower, LO | Borrower initiates via chat, LO can create on behalf of borrower |
| `application` → `underwriting` | LO | LO reviews completeness and submits |
| `underwriting` → `conditional_approval` | Underwriter | Underwriter renders preliminary approval with conditions |
| `underwriting` → `denied` | Underwriter | Underwriter renders denial |
| `underwriting` → `application` | Underwriter | Returned for corrections/additional docs |
| `conditional_approval` → `final_approval` | Underwriter | All conditions cleared |
| `conditional_approval` → `denied` | Underwriter | Conditions not satisfied or new risk discovered |
| `final_approval` → `closing` | LO | Loan packaged for closing |
| `closing` → `closed` | LO | Closing completed |
| `*` → `withdrawn` | Borrower, LO | Borrower can withdraw at any time; LO on borrower's behalf |

**State transition audit:** Every state transition is logged to the audit trail with the user who initiated the transition, the reason (if applicable), and a timestamp.

## Cross-Cutting Concerns

These requirements apply to **all stories** across all chunks.

### RBAC Enforcement

**REQ-CC-01: Three-layer RBAC enforcement**

Authorization is enforced at API, service, and agent layers. Failures at any layer are logged and result in 403 responses.

- **API layer:** Route-level access checks, data scope injection (LO sees own pipeline only)
- **Service layer:** Services re-apply data scope filters on `user_context`, defense-in-depth against middleware bypass
- **Agent layer:** Tool authorization checked immediately before execution (pre-tool node), role read from JWT claims

**REQ-CC-02: CEO PII masking**

When any response is generated for the CEO role, the following fields are masked before the response is sent:
- SSN (replaced with `***-**-XXXX` showing last 4 digits)
- DOB (replaced with age or `YYYY-**-**`)
- Account numbers (replaced with `****XXXX` showing last 4 digits)

Masking occurs at the API response middleware layer and is verified by output filters in agent responses.

**REQ-CC-03: CEO document access restriction**

The CEO role can access document metadata (type, upload date, status, quality flags) but not document content.

Enforcement layers:
- **API endpoint:** `/api/documents/{id}/content` returns 403 for CEO role
- **Service method:** `DocumentService.get_content()` raises exception if `user_context.role == 'ceo'`
- **Query layer:** Queries for CEO role exclude content columns from SELECT projection
- **Audit trail:** Document references in audit events do not inline content for CEO

**REQ-CC-04: Agent tool authorization staleness**

Agent tool authorization checks read the user's role from JWT claims in session context. The staleness window is bounded by access token lifetime (15 minutes). Authorization results are **not cached** across conversation turns -- every tool call triggers a fresh check.

### HMDA Data Isolation

**REQ-CC-05: Four-stage isolation**

HMDA demographic data is isolated at four stages:

1. **Collection:** HMDA data is collected through a dedicated API endpoint (`POST /api/hmda/collect`) that writes only to the `hmda` schema. This endpoint does not share a transaction with any lending data operation.

2. **Document Extraction:** The document extraction pipeline includes a demographic data filter. If demographic data is detected (keyword matching + semantic similarity), it is excluded from the extraction result that enters the lending data path. The exclusion is logged to the audit trail.

3. **Storage:** HMDA data is stored in a separate PostgreSQL schema (`hmda`). Two PostgreSQL roles enforce access:
   - `lending_app`: Full CRUD on lending schema, INSERT+SELECT on `audit_events`, **no grants on `hmda` schema**
   - `compliance_app`: SELECT on `hmda` schema, SELECT on lending schema (read-only for aggregate joins), INSERT+SELECT on `audit_events`

   The FastAPI application uses two connection pools, one for each role. The Compliance Service is the only module that uses the `compliance_app` pool.

4. **Retrieval:** Lending persona agents (LO, Underwriter) have no tools that query the `hmda` schema. The CEO agent has access to the Compliance Service's `get_hmda_aggregates` tool, which returns only pre-aggregated statistics. Individual HMDA records are never exposed through any tool.

**REQ-CC-06: CI lint check for HMDA isolation**

A CI step verifies that no code outside `packages/api/src/summit_cap/services/compliance/` references the `hmda` schema or imports the `compliance_app` connection pool. This check uses `grep -r` and fails the build on violation.

**REQ-CC-07: Database-level HMDA access verification**

The architecture includes a database-level verification test: `psql -U lending_app -c "SELECT * FROM hmda.demographics"` must return a permission denied error. This test is part of the integration test suite.

### Audit Trail Completeness

**REQ-CC-08: Audit every AI action**

The following events must be logged to the audit trail:
- Every user query to an AI agent
- Every tool call (tool name, parameters, result)
- Every data access operation (read/write, table, record ID)
- Every decision (approval, denial, condition issuance)
- Every state transition
- Every security event (rejected prompt injection, output filter redaction, authorization failure)
- Every HMDA data exclusion during document extraction

**REQ-CC-09: Audit event immutability**

The `audit_events` table enforces append-only semantics:
- Application database role has INSERT+SELECT grants only, no UPDATE or DELETE
- Database trigger rejects any UPDATE or DELETE attempt on `audit_events`, logging the attempt to `audit_violations`
- Sequential event IDs (bigserial) provide ordering
- Hash chain: each event includes `prev_hash` (hash of previous event's ID + content), computed under PostgreSQL advisory lock

**REQ-CC-10: Audit event schema**

All audit events include:
- `id` (bigserial, sequential)
- `timestamp` (timestamptz, server-generated)
- `prev_hash` (text, tamper evidence)
- `user_id` (uuid, who)
- `user_role` (text, their role at time of event)
- `event_type` (text: query, tool_call, data_access, decision, override, system, state_transition, security_event, hmda_collection, hmda_exclusion, compliance_check, communication_sent)
- `application_id` (uuid, nullable)
- `decision_id` (uuid, nullable)
- `event_data` (jsonb, full context)
- `source_document_id` (uuid, nullable, data provenance)
- `session_id` (uuid, conversation session)

**REQ-CC-11: Three audit query patterns**

The audit trail supports three query patterns:
1. **Application-centric:** Filter on `application_id`, order by timestamp
2. **Decision-centric:** Start from `decision_id`, follow `application_id` to find all related events
3. **Pattern-centric:** Filter on `event_type` and time range, aggregate with decision data

### Agent Security

**REQ-CC-12: Four-layer agent security**

Every AI agent implements four defense layers:

1. **Input validation:** User input is scanned for adversarial patterns (role-play attacks, instruction override attempts, system prompt extraction). Detected patterns are rejected before agent processing. Rejected inputs are logged.

2. **System prompt hardening:** Agent system prompts include explicit refusal instructions for out-of-scope requests. For lending agents: "You do not have access to demographic data. If asked, refuse and explain that HMDA data is isolated."

3. **Tool authorization:** A LangGraph pre-tool node checks `user_role in tool.allowed_roles` immediately before each invocation. On failure: tool returns authorization error, agent communicates restriction to user, audit trail records attempt.

4. **Output filtering:** Agent responses are scanned for sensitive data patterns (SSN format, HMDA data references) and semantic checks for demographic proxy references (neighborhood-level demographic composition, proxy characteristics). PoC uses pattern matching; production would use ML-based semantic detection.

**REQ-CC-13: Fair lending guardrails**

Lending agents (LO, Underwriter) actively refuse to consider protected characteristics. Queries involving factors that correlate with protected classes (ZIP codes without business justification, neighborhood names, school district references) trigger proxy discrimination awareness warnings.

**REQ-CC-14: HMDA data refusal**

If a lending persona agent (LO, Underwriter) is asked a question involving demographic data, the agent must refuse and explain: "I do not have access to demographic data. HMDA demographic information is collected for regulatory reporting and is isolated from lending decisions."

### AI Compliance Marking

**REQ-CC-15: Source file marking**

All code files produced or substantially modified with AI assistance include a comment near the top:
- **JS/TS:** `// This project was developed with assistance from AI tools.`
- **Python:** `# This project was developed with assistance from AI tools.`

**REQ-CC-16: Commit trailers**

Commits with AI-generated or AI-assisted code include a trailer:
- `Assisted-by: Claude Code` (human-driven design, AI assistance)
- `Generated-by: Claude Code` (substantially AI-generated)

**REQ-CC-17: Regulatory disclaimer**

All compliance-related content (knowledge base documents, compliance check results, regulatory guidance) carries a disclaimer: "This content is simulated for demonstration purposes and does not constitute legal or regulatory advice."

### Observability

**REQ-CC-18: LangFuse callback integration**

Every agent invocation attaches the LangFuse callback handler, capturing:
- Agent execution traces (each LangGraph node)
- Tool calls with parameters and results
- LLM calls with prompts, completions, token counts, and latency
- Model selection (which model handled each call)

**REQ-CC-19: Trace-to-audit correlation**

LangFuse traces and audit events share a `session_id`, allowing correlation between developer-facing observability and compliance-facing audit trail.

**REQ-CC-20: Structured logging**

All application logs use structured JSON format with standard fields:
- `timestamp` (ISO 8601)
- `level` (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `request_id` (propagates through gateway, services, agents)
- `user_id` (if authenticated)
- `service` (which module logged)
- `message` (human-readable)

### Configuration-Driven Extensibility

**REQ-CC-21: Agent configuration**

Each agent is defined in a YAML configuration file (`config/agents/{persona}-assistant.yaml`) containing:
- System prompt template
- Tool registry (list of tool names this agent can invoke)
- Data access scope
- Model routing rule

Adding a new persona requires adding a configuration file and registering it, not modifying framework code.

**REQ-CC-22: Model routing configuration**

Model routing rules are defined in `config/models.yaml`. Model entries specify provider, model name, and endpoint. Routing rules (complex keywords, simple patterns, word count threshold) are in a separate `routing:` section -- not per-model.

## Inter-Feature Dependency Map

Dependencies where one feature cannot function without another.

| Feature | Depends On | Type | Reason |
|---------|-----------|--------|
| F3 (Borrower application intake) | F2 (Authentication), F14 (RBAC) | behavioral | Borrower must be authenticated to initiate application |
| F4 (Document upload) | F3 (Application intake) | data | Documents are uploaded in context of an application |
| F5 (Document extraction) | F4 (Document upload), F25 (HMDA isolation) | behavioral | Extraction pipeline includes demographic filter |
| F6 (Document completeness) | F5 (Extraction) | data | Completeness checking requires extraction results |
| F7 (LO pipeline) | F3 (Applications exist), F14 (RBAC) | data | Pipeline view filtered to LO's scope |
| F8 (LO review) | F7 (Pipeline), F5 (Extraction results), F6 (Completeness) | data | LO reviews application with extraction results |
| F9 (Underwriter risk assessment) | F8 (LO submission), F5 (Extraction) | data | Risk assessment requires application data and documents |
| F10 (Compliance KB search) | None (KB is pre-seeded) | data | KB content exists independently |
| F11 (Compliance checks) | F9 (Risk assessment), F10 (KB) | behavioral | Compliance checks reference KB content and application data |
| F12 (CEO dashboard) | F9 (Decisions exist), F17 (Decisions), F25 (HMDA aggregates), F38 (Fairness metrics) | data | Dashboard aggregates decision data and HMDA statistics |
| F13 (CEO audit trail) | F15 (Audit events), F17 (Decisions) | data | Audit trail queries reference decisions and applications |
| F15 (Audit trail) | F2 (Authentication) | data | Audit events include user_id from authentication |
| F16 (Conditions management) | F9 (Underwriting) | behavioral | Conditions are issued during underwriting |
| F17 (Decisions) | F9 (Risk assessment), F11 (Compliance checks) | behavioral | Decisions reference risk and compliance results |
| F19 (Conversation memory) | F2 (Authentication) | data | Checkpoints are user-scoped |
| F20 (Demo data) | F1, F2, F3, F5, F9, F17, F25 | data | Demo data seeds all domain entities |
| F21 (Model routing) | F18 (Observability for routing visibility) | behavioral | Routing results are traced |
| F22 (Single-command setup) | All infrastructure features | infra | Orchestrates full stack startup |
| F23 (OpenShift deployment) | F22 (Compose-based architecture) | infra | Helm charts translate Compose services to Kubernetes |
| F24 (LO communication draft) | F7 (Pipeline), F8 (Application detail) | data | Drafts reference application context |
| F25 (HMDA isolation) | F2 (Authentication), F14 (RBAC), F5 (Document extraction filter) | behavioral | HMDA isolation spans collection, storage, and retrieval |
| F26 (Agent adversarial defense) | F14 (RBAC), F15 (Audit) | behavioral | Security events are logged |
| F27 (Rate lock tracking) | F3 (Applications), F7 (LO pipeline) | data | Rate locks are application attributes |
| F28 (Borrower condition response) | F16 (Conditions issued) | behavioral | Borrower responds to issued conditions |
| F38 (TrustyAI fairness metrics) | F25 (HMDA data), F17 (Decisions) | data | Metrics computed on HMDA-correlated outcomes |
| F39 (Model monitoring overlay) | F18 (LangFuse metrics) | data | Monitoring panel sources data from LangFuse |

## Phase Breakdown with Story Counts

| Phase | Label | Features | Story Count | Chunk Files |
|-------|-------|----------|-------------|-------------|
| 1 | Foundation | F1, F2, F14, F18, F20, F21, F22, F25 | 32 | chunk-1-foundation |
| 2 | Borrower | F3, F4, F5, F6, F15, F19, F27, F28 | 34 | chunk-2-borrower |
| 3 | Loan Officer | F7, F8, F24 | 11 | chunk-3-loan-officer |
| 4a | Underwriting | F9, F10, F11, F16, F17, F26, F38 | 33 | chunk-4-underwriting |
| 4a | Executive | F12, F13, F15 (export), F39 | 20 | chunk-5-executive |
| 4b | Deployment | F23 | 5 | chunk-5-executive |

**Total P0 stories: 134**

## Chunk Routing

| Chunk File | Features | Description |
|------------|----------|-------------|
| `requirements-chunk-1-foundation.md` | F1, F2, F14, F18, F20, F21, F22, F25 | Phase 1 foundation: authentication, RBAC, HMDA isolation, demo data, model routing, observability, single-command setup |
| `requirements-chunk-2-borrower.md` | F3, F4, F5, F6, F15, F19, F27, F28 | Phase 2 borrower persona: application intake, document upload, extraction, completeness, audit trail, conversation memory, rate lock, condition response |
| `requirements-chunk-3-loan-officer.md` | F7, F8, F24 | Phase 3 loan officer persona: pipeline view, application review, communication drafting |
| `requirements-chunk-4-underwriting.md` | F9, F10, F11, F16, F17, F26, F38 | Phase 4a underwriting persona: risk assessment, compliance KB search, compliance checks, conditions, decisions, agent security, fairness metrics |
| `requirements-chunk-5-executive.md` | F12, F13, F23, F39 | Phase 4a executive persona + Phase 4b deployment: CEO dashboard, audit trail, OpenShift deployment, model monitoring |

## Open Questions and Assumptions

### Open Questions

| ID | Question | Impact | Blocker For | Notes |
|----|----------|--------|-------------|-------|
| REQ-OQ-01 | What is the exact definition of "simple" vs "complex" queries for model routing (F21)? | Medium | Chunk 1 (F21 acceptance criteria) | Resolved: rule-based classification uses complex keywords (first priority) > word count > simple patterns > default to complex. Keywords and patterns are in `config/models.yaml`. |
| REQ-OQ-02 | What is the threshold for rate lock "nearing expiration" (F27)? | Low | Chunk 2 (F27 acceptance criteria) | Suggested: alert when < 7 days remaining, escalate when < 3 days. Defer to stakeholder or use suggested default. |
| REQ-OQ-03 | What fields constitute "application context" for LO communication drafts (F24)? | Low | Chunk 3 (F24 acceptance criteria) | Suggested: borrower name, application ID, loan type, property address, current stage. Defer to stakeholder or use suggested default. |
| REQ-OQ-04 | What are the severity levels for underwriting conditions (F16)? | Medium | Chunk 4 (F16 acceptance criteria) | Suggested: Critical (blocks approval), Standard (must clear), Optional (nice-to-have). Defer to stakeholder or use suggested default. |
| REQ-OQ-05 | What thresholds define fair lending concerns for SPD/DIR metrics (F38)? | High | Chunk 4 (F38 acceptance criteria) | Industry standard: DIR < 0.8 or SPD > 0.1 flags concern. Requires stakeholder confirmation or domain expert input. |
| REQ-OQ-06 | What is the demo data demographic distribution for fairness metrics testing (F38)? | Medium | Chunk 1 (F20 demo data seeding) | Demo data must include sufficient demographic diversity to compute meaningful SPD/DIR. Suggested: 30% protected class representation in historical data. |
| REQ-OQ-07 | What is the compliance KB content review timeline? | High | Chunk 4 (F10 KB search) | Duplicates Architecture OQ-A5. KB content must be reviewed by a domain expert before Phase 4a. Suggested timeline: draft during Phase 2, review during Phase 3, load during Phase 4a. |
| REQ-OQ-08 | What is the regulatory disclaimer text for compliance content? | Low | All chunks (REQ-CC-17) | Suggested: "This content is simulated for demonstration purposes and does not constitute legal or regulatory advice." Confirm with stakeholder. |

### Assumptions

| ID | Assumption | Risk If Wrong | Mitigation |
|----|-----------|--------------|------------|
| REQ-A-01 | The 15-minute access token lifetime is acceptable for agent tool authorization staleness | Low -- this is a Keycloak default | Token lifetime is configurable; can be shortened if stakeholder prefers |
| REQ-A-02 | The demographic data filter (F5, F25) pattern-matching approach is sufficient for PoC | Medium -- false negatives could leak HMDA data | Agent output filter provides secondary defense; adversarial test cases validate both layers |
| REQ-A-03 | The hash chain tamper evidence is sufficient for PoC audit trail integrity | Low -- explicitly called out as PoC-level in architecture | Production would replace with cryptographic verification or external ledger |
| REQ-A-04 | Pre-seeded demo documents are designed to produce consistent extraction results | Medium -- extraction brittleness could break demos | Test extraction pipeline with all demo documents; iterate documents until stable |
| REQ-A-05 | The Compliance KB contains 100-500 document chunks (PoC scale) | Low -- pgvector handles this easily | If actual KB is larger, verify pgvector performance and consider index optimization |
| REQ-A-06 | Form fallback for application intake (F3, F4) will not be required for MVP | Medium -- if conversational-only proves too brittle, form fallback adds scope | Form fallback is an accepted contingency per architecture; frontend accommodates both paths |
| REQ-A-07 | CEO role can see borrower names in audit trail and dashboard | Low -- architecture explicitly states names are visible, sensitive fields masked | If stakeholder prefers full anonymization, update PII masking rules |
| REQ-A-08 | The LlamaStack server is available at a known endpoint (local or remote) | High -- AI functionality depends on this | Architecture supports both local and remote inference; configuration-driven |
| REQ-A-09 | Keycloak realm import succeeds on first startup | Medium -- realm import failure blocks authentication | Test realm import in CI; provide manual import instructions as fallback |
| REQ-A-10 | The 10-minute setup target (F22) excludes model download time | Low -- explicitly called out in architecture | Documentation separates first-time setup (with model download) from subsequent startup |

## Coverage Validation Table

Every P0 feature from the product plan is mapped to at least one story ID.

| Feature ID | Feature Title | Story IDs | Covered? |
|------------|--------------|-----------|----------|
| F1 | Public product information and prequalification assistant | S-1-F1-01, S-1-F1-02, S-1-F1-03 | ✓ |
| F2 | Authentication and authorization | S-1-F2-01, S-1-F2-02, S-1-F2-03 | ✓ |
| F3 | Borrower application intake (conversational) | S-2-F3-01, S-2-F3-02, S-2-F3-03, S-2-F3-04, S-2-F3-05 | ✓ |
| F4 | Borrower document upload | S-2-F4-01, S-2-F4-02, S-2-F4-03, S-2-F4-04 | ✓ |
| F5 | Document extraction and quality assessment | S-2-F5-01, S-2-F5-02, S-2-F5-03, S-2-F5-04 | ✓ |
| F6 | Document completeness and proactive requests | S-2-F6-01, S-2-F6-02, S-2-F6-03, S-2-F6-04, S-2-F6-05 | ✓ |
| F7 | Loan officer pipeline view with urgency | S-3-F7-01, S-3-F7-02, S-3-F7-03, S-3-F7-04 | ✓ |
| F8 | Loan officer application review and submission | S-3-F8-01, S-3-F8-02, S-3-F8-03, S-3-F8-04 | ✓ |
| F9 | Underwriter risk assessment | S-4-F9-01, S-4-F9-02, S-4-F9-03, S-4-F9-04, S-4-F9-05 | ✓ |
| F10 | Compliance knowledge base search | S-4-F10-01, S-4-F10-02, S-4-F10-03, S-4-F10-04 | ✓ |
| F11 | Compliance checks (ECOA, ATR/QM, TRID) | S-4-F11-01, S-4-F11-02, S-4-F11-03, S-4-F11-04, S-4-F11-05 | ✓ |
| F12 | CEO executive dashboard | S-5-F12-01, S-5-F12-02, S-5-F12-03, S-5-F12-04, S-5-F12-05 | ✓ |
| F13 | CEO audit trail access and business analytics | S-5-F13-01, S-5-F13-02, S-5-F13-03, S-5-F13-04, S-5-F13-05, S-5-F13-06, S-5-F13-07, S-5-F13-08, S-5-F13-09 | ✓ |
| F14 | Role-based access control (multi-layer) | S-1-F14-01, S-1-F14-02, S-1-F14-03, S-1-F14-04, S-1-F14-05 | ✓ |
| F15 | Append-only audit trail | S-2-F15-01, S-2-F15-02, S-2-F15-03, S-2-F15-04, S-2-F15-05, S-2-F15-06, S-5-F15-07 | ✓ |
| F16 | Underwriting conditions management | S-4-F16-01, S-4-F16-02, S-4-F16-03, S-4-F16-04 | ✓ |
| F17 | Underwriting decisions and TRID disclosures | S-4-F17-01, S-4-F17-02, S-4-F17-03, S-4-F17-04, S-4-F17-05, S-4-F17-06, S-4-F17-07 | ✓ |
| F18 | LangFuse observability integration | S-1-F18-01, S-1-F18-02, S-1-F18-03 | ✓ |
| F19 | Cross-session conversation memory | S-2-F19-01, S-2-F19-02, S-2-F19-03, S-2-F19-04 | ✓ |
| F20 | Demo data seeding | S-1-F20-01, S-1-F20-02, S-1-F20-03, S-1-F20-04, S-1-F20-05 | ✓ |
| F21 | Model routing (complexity-based) | S-1-F21-01, S-1-F21-02, S-1-F21-03, S-1-F21-04 | ✓ |
| F22 | Single-command local setup | S-1-F22-01, S-1-F22-02, S-1-F22-03, S-1-F22-04 | ✓ |
| F23 | OpenShift deployment (Helm) | S-5-F23-01, S-5-F23-02, S-5-F23-03, S-5-F23-04, S-5-F23-05 | ✓ |
| F24 | Loan officer communication drafting | S-3-F24-01, S-3-F24-02, S-3-F24-03 | ✓ |
| F25 | HMDA data isolation (four-stage) | S-1-F25-01, S-1-F25-02, S-1-F25-03, S-1-F25-04, S-1-F25-05 | ✓ |
| F26 | Agent adversarial defenses | S-4-F26-01, S-4-F26-02, S-4-F26-03, S-4-F26-04 | ✓ |
| F27 | Rate lock tracking | S-2-F27-01, S-2-F27-02, S-2-F27-03 | ✓ |
| F28 | Borrower condition response | S-2-F28-01, S-2-F28-02, S-2-F28-03 | ✓ |
| F38 | TrustyAI fairness metrics | S-4-F38-01, S-4-F38-02, S-4-F38-03, S-4-F38-04 | ✓ |
| F39 | Model monitoring overlay | S-5-F39-01, S-5-F39-02, S-5-F39-03, S-5-F39-04, S-5-F39-05 | ✓ |

**All 30 P0 features are covered.**

## Product Plan Feature Mapping

| Product Plan Feature | Product Plan Name | Requirements Feature(s) | Story IDs |
|---------------------|-------------------|------------------------|-----------|
| F1 | Public Virtual Assistant with Guardrails | F1 (Public Assistant) | S-1-F1-01 to S-1-F1-03 |
| F2 | Prospect Affordability and Pre-Qualification | F1 (merged into Public Assistant) | S-1-F1-02, S-1-F1-03 |
| F3 | Borrower Authentication and Personal Assistant | F2 (Auth) + F3 (Intake) | S-1-F2-01 to S-1-F2-03, S-2-F3-01 to S-2-F3-05 |
| F4 | Mortgage Application Workflow | F3 (Conversational Intake) + F4 (Document Upload) | S-2-F3-01 to S-2-F3-05, S-2-F4-01 to S-2-F4-04 |
| F5 | Document Upload and Analysis | F4 (Upload) + F5 (Extraction) | S-2-F4-01 to S-2-F4-04, S-2-F5-01 to S-2-F5-04 |
| F6 | Application Status and Timeline Tracking | F6 (Document Completeness + Status) | S-2-F6-01 to S-2-F6-05 |
| F7 | Loan Officer Pipeline Management | F7 | S-3-F7-01 to S-3-F7-04 |
| F8 | Loan Officer Workflow Actions | F8 | S-3-F8-01 to S-3-F8-04 |
| F9 | Underwriter Review Workspace | F9 | S-4-F9-01 to S-4-F9-05 |
| F10 | Compliance Knowledge Base | F10 | S-4-F10-01 to S-4-F10-04 |
| F11 | Underwriter Decision and Conditions Workflow | F11 (Compliance Checks) + F16 (Conditions) + F17a (Decisions) | S-4-F11-* + S-4-F16-* + S-4-F17-01 to S-4-F17-05 |
| F12 | CEO Executive Dashboard | F12 | S-5-F12-01 to S-5-F12-05 |
| F13 | CEO Conversational Analytics | F13a (Audit Trail) + F13b (Business Analytics) | S-5-F13-01 to S-5-F13-09 |
| F14 | Role-Based Access Control | F2 (Auth) + F14 (RBAC) | S-1-F2-* + S-1-F14-* |
| F15 | Comprehensive Audit Trail | F15 | S-2-F15-01 to S-2-F15-06, S-5-F15-07 |
| F16 | Fair Lending Guardrails | F26 (Agent Adversarial Defenses) | S-4-F26-01 to S-4-F26-04 |
| F17 | Regulatory Awareness and TRID | F11 (TRID Checks) + F17b (Disclosure Generation) | S-4-F11-03 + S-4-F17-06, S-4-F17-07 |
| F18 | AI Observability Dashboard | F18 | S-1-F18-01 to S-1-F18-03 |
| F19 | Cross-Session Conversation Memory | F19 | S-2-F19-01 to S-2-F19-04 |
| F20 | Pre-Seeded Demo Data | F20 | S-1-F20-01 to S-1-F20-05 |
| F21 | Model Routing | F21 | S-1-F21-01 to S-1-F21-04 |
| F22 | Single-Command Local Setup | F22 | S-1-F22-01 to S-1-F22-04 |
| F23 | Container Platform Deployment | F23 | S-5-F23-01 to S-5-F23-05 |
| F24 | Loan Officer Communication Drafting | F24 | S-3-F24-01 to S-3-F24-03 |
| F25 | HMDA Demographic Data Collection | F25 | S-1-F25-01 to S-1-F25-05 |
| F26 | Adverse Action Notices | F17a (Decisions: S-4-F17-02 to S-4-F17-04) | S-4-F17-02, S-4-F17-03, S-4-F17-04 |
| F27 | Rate Lock and Closing Date Tracking | F27 | S-2-F27-01 to S-2-F27-03 |
| F28 | Document Contextual Completeness | F6 (Doc Completeness) + F28 (Condition Response) | S-2-F6-* + S-2-F28-* |
| F38 | TrustyAI Fair Lending Metrics | F38 | S-4-F38-01 to S-4-F38-04 |
| F39 | Model Monitoring Overlay | F39 | S-5-F39-01 to S-5-F39-05 |

## Architecture Consistency Notes

During requirements writing, I verified the architecture for clarity and completeness. Key findings:

**Confirmed clear:**
- 7 domain services with distinct boundaries (Application, Document, Underwriting, Compliance with KB submodule, Audit, Analytics, Conversation)
- HMDA isolation architecture (dual connection pools, four-stage isolation)
- Agent security model (four layers: input validation, system prompt hardening, tool authorization, output filtering)
- Template-aligned project structure (packages/api, packages/ui, packages/db, packages/agents)
- CEO document access restriction enforced at API, service, query, and audit layers
- Knowledge Base Service folded into Compliance Service as submodule

**No gaps found that prevent requirements writing.**

The architecture is sufficiently detailed to write requirements against. All component boundaries, data flows, and integration patterns are clear.

## Next Steps

1. **Pass 2 (Chunk Files):** Write the five chunk files with full Given/When/Then acceptance criteria for all 109 stories.
2. **Parallel Execution:** Execute chunk files 1-5 as parallel agents to flag inter-chunk inconsistencies.
3. **Consistency Pass:** After all chunks are complete, verify cross-feature dependencies and cross-cutting requirements are addressed.
4. **Phase 8 (Requirements Review):** Product Manager and Architect review this hub and all chunk files.

---

*Generated during SDD Phase 7 (Requirements). This is Pass 1 (master document / hub). Pass 2 will produce the detailed chunk files.*
