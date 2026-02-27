# Interface Contracts: Phase 2

This document defines the **boundary-level agreements** for Phase 2. It covers only the shapes that cross component boundaries -- what goes in and out at integration points. It does not prescribe internal implementation details.

Engineers own how they build their piece. This document owns the seams between pieces.

---

## 1. API Routes

These are the HTTP endpoints added in Phase 2. Both sides must agree on method, path, auth requirement, and request/response shape.

### Document Management (F4)

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| POST | `/api/applications/{id}/documents` | Yes | admin, borrower, loan_officer | multipart/form-data | `DocumentUploadResponse` |
| GET | `/api/applications/{id}/documents` | Yes | all authenticated | -- | `DocumentListResponse` |
| GET | `/api/applications/{id}/documents/{did}` | Yes | all authenticated | -- | `DocumentDetailResponse` |
| GET | `/api/applications/{id}/documents/{did}/content` | Yes | admin, borrower, loan_officer, underwriter | -- | `DocumentFilePathResponse` |
| GET | `/api/applications/{id}/completeness` | Yes | all authenticated | -- | `CompletenessResponse` |

**Document upload notes:**
- Request format: `multipart/form-data` with `file` (UploadFile) and `doc_type` (DocumentType enum string)
- Max file size: 50MB
- Allowed content types: `application/pdf`, `image/jpeg`, `image/png`, `image/tiff`
- Returns 201 on success, 413 if file too large, 422 if invalid content type
- CEO role can list documents but `file_path` is masked to `null` in detail responses
- CEO role is blocked from `/content` endpoint entirely (403 Forbidden)

### Conditions (F28)

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| GET | `/api/applications/{id}/conditions` | Yes | admin, borrower, loan_officer, underwriter | -- | `ConditionListResponse` |
| POST | `/api/applications/{id}/conditions/{cid}/respond` | Yes | borrower, admin | `ConditionRespondRequest` | `ConditionResponse` |

**Conditions notes:**
- `GET` supports `open_only` query parameter (boolean, default false) to filter open conditions
- Response is not paginated (all conditions returned)
- `POST` allows borrower to submit text response to an underwriting condition

### Rate Lock (F27)

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| GET | `/api/applications/{id}/rate-lock` | Yes | all authenticated | -- | `RateLockResponse` |

**Rate lock notes:**
- Returns status: "active", "expired", or "none"
- Includes `days_remaining` and `is_urgent` flag for active locks

### Application Status

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| GET | `/api/applications/{id}/status` | Yes | all authenticated | -- | `ApplicationStatusResponse` |

**Status notes:**
- Aggregates document completeness, open conditions, rate lock status, and stage info
- Returns human-readable stage labels and next steps

### Co-Borrower Management (F26)

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| POST | `/api/applications/{id}/borrowers` | Yes | loan_officer, underwriter, admin | `AddBorrowerRequest` | `ApplicationResponse` |
| DELETE | `/api/applications/{id}/borrowers/{bid}` | Yes | loan_officer, underwriter, admin | -- | `ApplicationResponse` |

**Co-borrower notes:**
- `POST` adds a borrower to the application via junction table
- Returns 409 if borrower already linked
- `DELETE` removes a borrower
- Cannot remove last borrower (400)
- Cannot remove primary borrower without reassigning first (400)

### HMDA Demographics (F5)

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| POST | `/api/hmda/demographics` | Yes | borrower, admin | `HmdaCollectionRequest` | `HmdaCollectionResponse` |

**HMDA notes:**
- Uses `compliance_app` DB role for schema isolation
- Endpoint path changed from Phase 1's `/hmda/collect` to `/hmda/demographics`
- All HMDA data isolated in `hmda.demographics` table (separate schema)
- Response includes `conflicts` field if multiple demographics exist for borrower

### Borrower Chat (F3, F19)

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| WS | `/api/borrower/chat?token=<jwt>` | Yes | borrower | WebSocket protocol | WebSocket protocol |
| GET | `/api/borrower/conversations/history` | Yes | borrower, admin | -- | `{data: [{role, content, timestamp}, ...]}` |

**Chat notes:**
- WebSocket requires `?token=<jwt>` query param for authentication
- Conversations persist across sessions using deterministic thread IDs
- See Section 3 for WebSocket protocol details
- History endpoint returns prior conversation messages for initial render

### Audit (F15)

| Method | Path | Auth | Roles | Request Body | Response Body |
|--------|------|------|-------|-------------|---------------|
| POST | `/api/admin/seed` | Yes | admin | -- | `SeedResponse` |
| GET | `/api/admin/seed/status` | Yes | admin | -- | `SeedStatusResponse` |
| GET | `/api/admin/audit` | Yes | admin | -- | `AuditEventsResponse` |
| GET | `/api/admin/audit/verify` | Yes | admin | -- | `AuditChainVerifyResponse` |

**Audit notes:**
- `/audit` requires `session_id` query parameter for filtering events
- `/audit/verify` checks hash chain integrity across all audit events
- Seed endpoint accepts `force=true` query param to re-seed (returns 409 if already seeded without force)

Error responses use `ErrorResponse` (RFC 7807) for all 4xx/5xx.

---

## 2. Shared Data Models

### Python (Pydantic) -- `packages/api/src/schemas/`

These models are the contract. If you consume or produce data that crosses a boundary, use these exact shapes.

```python
# document.py

class DocumentResponse(BaseModel):
    """Document metadata response (safe for all roles including CEO)."""
    id: int
    application_id: int
    borrower_id: int | None = None
    doc_type: DocumentType
    status: DocumentStatus
    quality_flags: str | None = None
    uploaded_by: str | None = None
    created_at: datetime
    updated_at: datetime

class DocumentDetailResponse(DocumentResponse):
    """Full document response including file_path (masked for CEO)."""
    file_path: str | None = None

class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    id: int
    application_id: int
    borrower_id: int | None = None
    doc_type: DocumentType
    status: DocumentStatus
    file_path: str | None = None
    created_at: datetime

class DocumentFilePathResponse(BaseModel):
    """Response for document content endpoint."""
    file_path: str

class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    data: list[DocumentResponse]
    pagination: Pagination
```

```python
# completeness.py

class DocumentRequirement(BaseModel):
    """A single required document with its fulfillment status."""
    doc_type: DocumentType
    label: str
    is_provided: bool = False
    document_id: int | None = None
    status: DocumentStatus | None = None
    quality_flags: list[str] = []

class CompletenessResponse(BaseModel):
    """Document completeness summary for an application."""
    application_id: int
    is_complete: bool
    requirements: list[DocumentRequirement]
    provided_count: int
    required_count: int
```

```python
# condition.py

class ConditionItem(BaseModel):
    """Single condition in a list response."""
    id: int
    description: str
    severity: str | None = None
    status: str | None = None
    response_text: str | None = None
    issued_by: str | None = None
    created_at: datetime | None = None

class ConditionListResponse(BaseModel):
    """Response for GET /applications/{id}/conditions."""
    data: list[ConditionItem]
    pagination: Pagination

class ConditionRespondRequest(BaseModel):
    """Request body for responding to a condition with text."""
    response_text: str

class ConditionResponse(BaseModel):
    """Response for a single condition after an update."""
    data: ConditionItem
```

```python
# rate_lock.py

class RateLockResponse(BaseModel):
    """Response for GET /api/applications/{id}/rate-lock."""
    application_id: int
    status: str  # "active", "expired", "none"
    locked_rate: float | None = None
    lock_date: datetime | None = None
    expiration_date: datetime | None = None
    days_remaining: int | None = None
    is_urgent: bool | None = None
```

```python
# status.py

class PendingAction(BaseModel):
    """A single action the borrower or LO needs to take."""
    action_type: str
    description: str

class StageInfo(BaseModel):
    """Human-readable info about the current application stage."""
    label: str
    description: str
    next_step: str
    typical_timeline: str

class ApplicationStatusResponse(BaseModel):
    """Aggregated status summary for an application."""
    application_id: int
    stage: str
    stage_info: StageInfo
    is_document_complete: bool
    provided_doc_count: int
    required_doc_count: int
    open_condition_count: int
    pending_actions: list[PendingAction]
```

```python
# application.py (additions)

class AddBorrowerRequest(BaseModel):
    """Add a borrower to an application."""
    borrower_id: int
    is_primary: bool = False

class BorrowerSummary(BaseModel):
    """Borrower info nested inside application responses."""
    id: int
    first_name: str
    last_name: str
    email: str
    ssn: str | None = None
    dob: datetime | None = None
    employment_status: EmploymentStatus | None = None
    is_primary: bool = False

class ApplicationResponse(BaseModel):
    """Single application response (updated with borrowers list)."""
    id: int
    stage: ApplicationStage
    loan_type: LoanType | None = None
    property_address: str | None = None
    loan_amount: Decimal | None = None
    property_value: Decimal | None = None
    assigned_to: str | None = None
    created_at: datetime
    updated_at: datetime
    borrowers: list[BorrowerSummary] = []
```

```python
# hmda.py (updated)

class HmdaCollectionRequest(BaseModel):
    """Request body for HMDA demographic data collection."""
    application_id: int
    borrower_id: int | None = None
    race: str | None = None
    ethnicity: str | None = None
    sex: str | None = None
    age: str | None = None
    race_collected_method: str = Field(default="self_reported")
    ethnicity_collected_method: str = Field(default="self_reported")
    sex_collected_method: str = Field(default="self_reported")
    age_collected_method: str = Field(default="self_reported")

class HmdaCollectionResponse(BaseModel):
    """Response after collecting HMDA demographic data."""
    id: int
    application_id: int
    borrower_id: int | None = None
    collected_at: datetime
    conflicts: list[dict] | None = None
    status: str = "collected"
```

```python
# admin.py

class AuditEventItem(BaseModel):
    """Single audit event in a query response."""
    id: int
    timestamp: datetime
    event_type: str
    user_id: str | None = None
    user_role: str | None = None
    application_id: int | None = None
    event_data: dict | str | None = None

class AuditEventsResponse(BaseModel):
    """Response for GET /api/admin/audit."""
    session_id: str
    count: int
    events: list[AuditEventItem]

class AuditChainVerifyResponse(BaseModel):
    """Response for GET /api/admin/audit/verify."""
    status: str
    events_checked: int
    first_break_id: int | None = None

class SeedResponse(BaseModel):
    """Response for POST /api/admin/seed."""
    status: str
    seeded_at: datetime | None = None
    config_hash: str | None = None
    borrowers: int | None = None
    active_applications: int | None = None
    historical_loans: int | None = None
    hmda_demographics: int | None = None

class SeedStatusResponse(BaseModel):
    """Response for GET /api/admin/seed/status."""
    seeded: bool
    seeded_at: datetime | None = None
    config_hash: str | None = None
    summary: dict | None = None
```

```python
# error.py (RFC 7807)

class ErrorResponse(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""
    type: str = Field(default="about:blank")
    title: str
    status: int
    detail: str = ""
    request_id: str = ""
```

```python
# shared (__init__.py)

class Pagination(BaseModel):
    """Offset-based pagination metadata for list responses."""
    total: int
    offset: int
    limit: int
    has_more: bool
```

### TypeScript -- `packages/ui/src/services/types.ts`

Frontend equivalents of the Python models above. Must stay in sync.

```typescript
interface DocumentResponse {
    id: number;
    application_id: number;
    borrower_id: number | null;
    doc_type: string;
    status: string;
    quality_flags: string | null;
    uploaded_by: string | null;
    created_at: string;
    updated_at: string;
}

interface DocumentDetailResponse extends DocumentResponse {
    file_path: string | null;
}

interface DocumentUploadResponse {
    id: number;
    application_id: number;
    borrower_id: number | null;
    doc_type: string;
    status: string;
    file_path: string | null;
    created_at: string;
}

interface DocumentRequirement {
    doc_type: string;
    label: string;
    is_provided: boolean;
    document_id: number | null;
    status: string | null;
    quality_flags: string[];
}

interface CompletenessResponse {
    application_id: number;
    is_complete: boolean;
    requirements: DocumentRequirement[];
    provided_count: number;
    required_count: number;
}

interface ConditionItem {
    id: number;
    description: string;
    severity: string | null;
    status: string | null;
    response_text: string | null;
    issued_by: string | null;
    created_at: string | null;
}

interface RateLockResponse {
    application_id: number;
    status: "active" | "expired" | "none";
    locked_rate: number | null;
    lock_date: string | null;
    expiration_date: string | null;
    days_remaining: number | null;
    is_urgent: boolean | null;
}

interface PendingAction {
    action_type: string;
    description: string;
}

interface StageInfo {
    label: string;
    description: string;
    next_step: string;
    typical_timeline: string;
}

interface ApplicationStatusResponse {
    application_id: number;
    stage: string;
    stage_info: StageInfo;
    is_document_complete: boolean;
    provided_doc_count: number;
    required_doc_count: number;
    open_condition_count: number;
    pending_actions: PendingAction[];
}

interface BorrowerSummary {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    ssn: string | null;
    dob: string | null;
    employment_status: string | null;
    is_primary: boolean;
}

interface ApplicationResponse {
    id: number;
    stage: string;
    loan_type: string | null;
    property_address: string | null;
    loan_amount: string | null;
    property_value: string | null;
    assigned_to: string | null;
    created_at: string;
    updated_at: string;
    borrowers: BorrowerSummary[];
}

interface AddBorrowerRequest {
    borrower_id: number;
    is_primary: boolean;
}

interface HmdaCollectionRequest {
    application_id: number;
    borrower_id?: number;
    race?: string;
    ethnicity?: string;
    sex?: string;
    age?: string;
    race_collected_method?: string;
    ethnicity_collected_method?: string;
    sex_collected_method?: string;
    age_collected_method?: string;
}

interface HmdaCollectionResponse {
    id: number;
    application_id: number;
    borrower_id: number | null;
    collected_at: string;
    conflicts: Record<string, unknown>[] | null;
    status: string;
}

interface AuditEventItem {
    id: number;
    timestamp: string;
    event_type: string;
    user_id: string | null;
    user_role: string | null;
    application_id: number | null;
    event_data: Record<string, unknown> | string | null;
}

interface AuditEventsResponse {
    session_id: string;
    count: number;
    events: AuditEventItem[];
}

interface AuditChainVerifyResponse {
    status: string;
    events_checked: number;
    first_break_id: number | null;
}

interface SeedResponse {
    status: string;
    seeded_at: string | null;
    config_hash: string | null;
    borrowers: number | null;
    active_applications: number | null;
    historical_loans: number | null;
    hmda_demographics: number | null;
}

interface SeedStatusResponse {
    seeded: boolean;
    seeded_at: string | null;
    config_hash: string | null;
    summary: Record<string, unknown> | null;
}

interface Pagination {
    total: number;
    offset: number;
    limit: number;
    has_more: boolean;
}

interface ErrorResponse {
    type: string;
    title: string;
    status: number;
    detail: string;
    request_id: string;
}
```

---

## 3. WebSocket Protocol (Borrower Chat)

### Connection

```
WS /api/borrower/chat?token=<jwt>
```

- JWT required in query parameter
- Role must be `borrower`
- Returns 401 if token invalid
- Connection persists until client or server closes

### Message Format

**Client to Server:**

```json
{
    "type": "message",
    "content": "What documents do I need to upload?"
}
```

**Server to Client:**

```json
{
    "type": "message",
    "content": "You need to upload the following documents..."
}
```

**Error Messages:**

```json
{
    "type": "error",
    "content": "Our chat assistant is temporarily unavailable."
}
```

**Stream Chunks (during agent processing):**

```json
{
    "type": "chunk",
    "content": "partial response text"
}
```

### Conversation Persistence

- Conversations persist across WebSocket reconnections
- Thread ID derived from authenticated user ID and agent name
- Uses PostgreSQL checkpointer when available
- Falls back to session-local memory if checkpointer unavailable

---

## 4. Database Schema Updates

### New Tables (public schema)

| Table | Key Columns | Used By |
|-------|-------------|---------|
| `documents` | id, application_id, borrower_id, doc_type, file_path, status, quality_flags, uploaded_by | Document services, extraction pipeline |
| `document_extractions` | id, document_id, field_name, field_value, confidence, source_page | Extraction pipeline |
| `conditions` | id, application_id, description, severity, status, response_text, issued_by | Underwriting, borrower response |
| `rate_locks` | id, application_id, locked_rate, lock_date, expiration_date, is_active | Rate lock status |
| `conversation_checkpoints` | id, user_id, thread_id, checkpoint_data, created_at | Agent conversation persistence |

### Updated Tables (public schema)

| Table | New Columns | Notes |
|-------|------------|-------|
| `application_borrowers` | is_primary | Supports co-borrower relationships with primary designation |
| `audit_events` | session_id | Links audit events to LangFuse traces for correlation |

### Schema Isolation (hmda schema)

| Table | Key Columns | Access |
|-------|-------------|--------|
| `hmda.demographics` | id, application_id, borrower_id, race, ethnicity, sex, age, collected_at | `compliance_app` role only (full CRUD); `lending_app` role has SELECT only |

### Access Rules

| Role | public schema | hmda schema | audit_events |
|------|--------------|-------------|-------------|
| `lending_app` | Full CRUD | SELECT only | INSERT + SELECT only |
| `compliance_app` | SELECT only | Full CRUD | INSERT + SELECT |

This is enforced at the PostgreSQL level. Two connection pools in the application map to these roles. The `compliance_app` pool is used exclusively by the Compliance Service (`services/compliance/`).

---

## 5. Storage Contract (MinIO)

### Connection

- Endpoint: `http://minio:9000` (container) or `http://localhost:9000` (host)
- Console: `http://localhost:9001`
- Credentials: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` from env vars
- Default bucket: `summit-cap-documents`

### Document Path Structure

```
{bucket}/applications/{application_id}/documents/{document_id}/{filename}
```

Example: `summit-cap-documents/applications/42/documents/101/w2_2023.pdf`

### File Metadata

- Content-Type header preserved from upload
- Document ID embedded in path for retrieval
- Application ID for first-level organization

### Health Check

```
GET /minio/health/live
```

---

## 6. RBAC Extensions

### New Data Scope Flags

| Field | Purpose |
|-------|---------|
| `document_metadata_only` | CEO role sees document metadata but not `file_path` |
| `full_pipeline` | Loan officers and underwriters see all documents in their assigned applications |

### CEO Document Access Behavior

- **Allowed:** List documents, view metadata
- **Blocked:** View `file_path` in detail responses (masked to `null`)
- **Blocked:** Access `/content` endpoint (403 Forbidden at route level)

This is enforced at two layers:
1. Route-level role check (Layer 1) blocks CEO from `/content` endpoint
2. Response serialization (Layer 2) masks `file_path` to `null` for detail responses

---

## 7. Cross-Boundary Dependencies

This shows which Phase 2 features connect to other engineers' work at integration points.

| Boundary | Producer | Consumer | Contract to Agree On |
|----------|----------|----------|---------------------|
| Document Upload <-> MinIO | Backend (document service) | MinIO storage | Section 5 (path structure, content types) |
| Document Upload <-> Extraction | Upload endpoint | Extraction pipeline | Document ID, file path in MinIO |
| WebSocket <-> Checkpointer | WebSocket handler | Conversation service, PostgreSQL | Thread ID format, checkpoint schema |
| HMDA <-> Dual Pool | HMDA endpoint | Compliance service, DB layer | Section 4 (schema isolation, dual roles) |
| Borrower Chat <-> Agent Registry | Chat endpoint | Agent loader, LangGraph | Agent name resolution, checkpointer injection |
| Audit <-> LangFuse | Audit service | LangFuse trace correlation | `session_id` field linking |

---

## Contract Change Protocol

If you discover that an agreed contract doesn't work:

1. **Propose** the change (describe what and why) before implementing around it
2. **Check** who else depends on the contract (use Section 7)
3. **Update** this document once agreed
4. **Notify** affected engineers

Do not implement workarounds for a broken contract. Fix the contract.
