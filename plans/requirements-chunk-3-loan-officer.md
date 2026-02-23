# Requirements: AI Banking Quickstart -- Chunk 3: Loan Officer Experience

## About This Document

This is **Chunk 3** of the requirements document, covering Phase 3 features for the Loan Officer persona. This chunk contains detailed Given/When/Then acceptance criteria for all stories listed in the master requirements document (hub) for this feature area.

**Master document:** `plans/requirements.md` (the hub)

**Covered in this chunk:**
- **F7:** Loan Officer Pipeline Management (S-3-F7-01 through S-3-F7-04)
- **F8:** Loan Officer Workflow Actions (S-3-F8-01 through S-3-F8-04)
- **F24:** Loan Officer Communication Drafting (S-3-F24-01 through S-3-F24-03)

**Total stories in this chunk:** 11

**Cross-cutting concerns:** All stories in this chunk are subject to the cross-cutting requirements defined in the hub (REQ-CC-01 through REQ-CC-22). These are not repeated here -- reference the hub for details.

**Cross-references to other chunks:**
- F7 and F8 depend on F5 (Document extraction results, Chunk 2)
- F7 and F8 depend on F6 (Document completeness, Chunk 2)
- F8 feeds into F11 (Underwriting workflow, Chunk 4)
- F24 references F27 (Rate locks, Chunk 2) and F28 (Document completeness for drafts, Chunk 2)
- All stories reference the application state machine and RBAC enforcement from the hub

---

## Feature F7: Loan Officer Pipeline Management

The Loan Officer (LO) persona views their assigned applications in a pipeline dashboard with urgency indicators. The pipeline view is the LO's primary workspace for tracking loan files, identifying stalled applications, and selecting files for review.

### S-3-F7-01: LO views pipeline with urgency indicators

**User Story:**

As a Loan Officer,
I want to view my pipeline with urgency indicators for each application,
so that I can prioritize my workload and address time-sensitive issues first.

**Acceptance Criteria:**

**Scenario: LO accesses pipeline view**

Given I am authenticated as a Loan Officer
When I navigate to the pipeline dashboard
Then I see a list of all applications assigned to me
And each application displays:
  - Borrower name
  - Loan amount
  - Application state (e.g., "application", "underwriting", "conditional_approval")
  - Current stage timing (days in current stage)
  - Urgency indicator (visual: color-coded or icon-based)
  - Last activity timestamp
And the list is sorted by urgency (highest urgency first)

**Scenario: Urgency indicator levels**

Given I have applications in my pipeline with varying urgency factors
When I view the pipeline
Then each application's urgency indicator reflects the highest severity factor:
  - **Critical (red)**: Rate lock expires within 3 days OR application is 7+ days overdue for LO action OR outstanding conditions blocking closing within 5 days
  - **High (orange)**: Rate lock expires within 7 days OR application is 4-6 days overdue for LO action OR borrower submitted documents awaiting LO review for 48+ hours
  - **Medium (yellow)**: Application approaching stage timing target (e.g., 80% of expected time in stage) OR document quality flags requiring attention
  - **Normal (green)**: All factors within expected timelines
And the urgency calculation is real-time (updates when I refresh the page)

**Scenario: No applications assigned**

Given I am a Loan Officer with no assigned applications
When I view the pipeline dashboard
Then I see an empty state message: "No applications assigned to you yet."
And I see a suggestion to check with management or wait for new applications

**Scenario: Pipeline filtering**

Given I have multiple applications in my pipeline
When I apply a filter for "by stage" (e.g., show only "application" stage)
Then the pipeline displays only applications in the selected stage
And urgency indicators remain visible on filtered results
When I apply a filter for "closing date" (e.g., closing within 30 days)
Then the pipeline displays only applications with closing dates in the specified range
When I apply a filter for "stalled" (applications with no activity for 7+ days)
Then the pipeline displays only stalled applications

**Scenario: Pipeline sorting**

Given I have applications with different urgency levels and attributes
When I select "Sort by urgency" (default)
Then applications are ordered: Critical > High > Medium > Normal
When I select "Sort by closing date"
Then applications are ordered by earliest closing date first
When I select "Sort by loan amount"
Then applications are ordered by highest loan amount first
When I select "Sort by last activity"
Then applications are ordered by most recent activity first

**Notes:**
- Urgency factors include: rate lock expiration (from F27 data), stage timing expectations (compared to historical averages or configured thresholds), overdue document requests (from F6 completeness tracking), outstanding conditions (from F16 in Chunk 4), and borrower responsiveness (time since last borrower activity).
- "Stalled" is defined as: no activity (no document uploads, no LO actions, no borrower interactions) for 7+ days, excluding applications in terminal states ("closed", "denied", "withdrawn").
- The pipeline view uses data-scope injection (REQ-CC-01) to ensure the LO sees only their own assigned applications. The API middleware injects `WHERE assigned_loan_officer_id = :current_user_id` on all pipeline queries.

---

### S-3-F7-02: Pipeline filtered to LO's own assigned applications

**User Story:**

As a Loan Officer,
I want to see only applications assigned to me,
so that I am not distracted by applications managed by other loan officers.

**Acceptance Criteria:**

**Scenario: LO sees only own applications**

Given I am authenticated as Loan Officer "Alice" (ID: `alice_lo`)
And application A001 is assigned to me
And application A002 is assigned to Loan Officer "Bob" (ID: `bob_lo`)
When I request the pipeline view
Then I see application A001 in my pipeline
And I do NOT see application A002
And the pipeline count reflects only applications assigned to me

**Scenario: RBAC enforcement at API layer**

Given I am authenticated as Loan Officer "Alice"
When the API gateway receives my pipeline request
Then the middleware injects a data scope filter: `assigned_loan_officer_id = 'alice_lo'`
And the domain service query includes this filter
And no applications outside my assignment are returned

**Scenario: RBAC enforcement at service layer (defense-in-depth)**

Given the API middleware correctly injects data scope
But hypothetically the middleware is bypassed
When the Application Service executes a pipeline query
Then the service re-applies the data scope filter from `user_context.user_id`
And only applications assigned to the requesting LO are returned
And the bypass attempt is logged

**Scenario: Attempt to access another LO's application directly**

Given I am Loan Officer "Alice"
And application A002 is assigned to Loan Officer "Bob"
When I attempt to access application A002 via direct URL or API call (`GET /api/applications/A002`)
Then the API returns 403 Forbidden
And the audit trail logs the access denial (event_type: "authorization_failure", user_id: "alice_lo", application_id: "A002")

**Scenario: CEO views all applications (aggregate, masked PII)**

Given I am authenticated as the CEO
When I request the pipeline summary
Then I see aggregate metrics across all loan officers
And I can see application counts by stage and LO
And individual application details include masked PII per REQ-CC-02

**Notes:**
- This story enforces REQ-CC-01 (three-layer RBAC) at the pipeline query level.
- The data scope filter is applied at API middleware, domain service, and query construction layers.
- Authorization failures are logged to the audit trail per REQ-CC-08.

---

### S-3-F7-03: Urgency based on rate lock expiration and stage timing

**User Story:**

As a Loan Officer,
I want urgency indicators that reflect rate lock expiration and stage timing,
so that I can prevent rate lock expirations and keep applications moving through the pipeline.

**Acceptance Criteria:**

**Scenario: Rate lock expiration drives urgency**

Given application A001 has a rate lock expiring in 2 days
When I view the pipeline
Then application A001 displays a **Critical** urgency indicator
And the urgency tooltip shows: "Rate lock expires in 2 days (MM/DD/YYYY)"
And the application is sorted to the top of the pipeline

**Scenario: Rate lock approaching expiration**

Given application A002 has a rate lock expiring in 5 days
When I view the pipeline
Then application A002 displays a **High** urgency indicator
And the urgency tooltip shows: "Rate lock expires in 5 days (MM/DD/YYYY)"

**Scenario: Stage timing threshold exceeded**

Given application A003 has been in "application" stage for 12 days
And the expected time in "application" stage is 5-7 days
When I view the pipeline
Then application A003 displays a **Critical** urgency indicator (7+ days overdue)
And the urgency tooltip shows: "In application stage for 12 days (expected: 5-7 days)"

**Scenario: Stage timing approaching threshold**

Given application A004 has been in "application" stage for 5 days
And the expected time is 5-7 days
When I view the pipeline
Then application A004 displays a **Medium** urgency indicator (80% of expected time)
And the urgency tooltip shows: "In application stage for 5 days (expected: 5-7 days)"

**Scenario: Outstanding conditions with approaching closing date**

Given application A005 has outstanding underwriting conditions
And the closing date is in 4 days
And the conditions are not yet cleared
When I view the pipeline
Then application A005 displays a **Critical** urgency indicator
And the urgency tooltip shows: "Closing in 4 days with outstanding conditions"

**Scenario: Document request overdue**

Given application A006 has a document request sent to the borrower 8 days ago
And the borrower has not responded
When I view the pipeline
Then application A006 displays a **High** urgency indicator
And the urgency tooltip shows: "Document request pending for 8 days"

**Scenario: Multiple urgency factors present**

Given application A007 has:
  - Rate lock expiring in 2 days (Critical factor)
  - Stage timing within expected range (Normal factor)
When I view the pipeline
Then application A007 displays the highest urgency level: **Critical**
And the urgency tooltip lists all contributing factors:
  - "Rate lock expires in 2 days"
  - "In underwriting stage for 3 days (expected: 3-5 days)"

**Scenario: No urgency factors present**

Given application A008 has:
  - Rate lock expiration more than 7 days away
  - Stage timing within expected range
  - No overdue document requests
  - No outstanding conditions
When I view the pipeline
Then application A008 displays a **Normal** urgency indicator
And the tooltip shows: "On track"

**Notes:**
- Rate lock expiration dates are sourced from F27 (rate lock tracking, Chunk 2).
- Stage timing expectations are configured per-stage in `config/app.yaml` or derived from historical averages.
- Urgency calculation logic should be testable independently of the UI (service-layer function).
- The urgency calculation runs on every pipeline request (real-time, not pre-computed) -- acceptable at PoC scale.

---

### S-3-F7-04: LO clicks application to view detail

**User Story:**

As a Loan Officer,
I want to click an application in the pipeline to view its details,
so that I can review the application data, documents, and history before taking action.

**Acceptance Criteria:**

**Scenario: LO selects application from pipeline**

Given I am viewing my pipeline dashboard
When I click on application A001
Then the application detail view opens
And I see:
  - Borrower name, contact information
  - Loan amount, loan type, property address
  - Current state and stage timing
  - Rate lock status (if applicable)
  - Document list with status indicators (complete, pending, flagged)
  - Recent activity timeline (last 5 events)
  - Available actions (e.g., "Submit to Underwriting", "Request Documents", "Draft Communication")

**Scenario: Application detail includes document quality flags**

Given application A001 has uploaded documents
And one document has a quality flag: "blurry_scan"
When I view the application detail
Then the document list includes a quality indicator next to the flagged document
And I can click the document to see extraction results and quality details

**Scenario: Application detail includes extraction results**

Given application A001 has a W-2 document that has been processed
When I view the document in the application detail
Then I see:
  - Extracted fields (income, employer, tax year)
  - Extraction confidence scores (if available)
  - Link to view raw document (opens in viewer)

**Scenario: Application detail loads conversation history**

Given I have previously chatted with the borrower about application A001
When I open the application detail
Then the chat interface displays the conversation history
And I can continue the conversation in context

**Scenario: Application not found**

Given I am Loan Officer "Alice"
When I attempt to view application A999 (does not exist)
Then the API returns 404 Not Found
And the UI displays: "Application not found or you do not have access."

**Scenario: Application assigned to another LO (access denied)**

Given I am Loan Officer "Alice"
And application A002 is assigned to Loan Officer "Bob"
When I attempt to view application A002
Then the API returns 403 Forbidden
And the UI displays: "You do not have access to this application."
And the access attempt is logged to the audit trail

**Notes:**
- Application detail view is the transition point from pipeline list to the chat-based review workflow (F8).
- Document quality flags are sourced from F5 (document extraction and quality assessment, Chunk 2).
- Extraction results are sourced from F5 (document_extractions table).
- Conversation history is loaded via F19 (cross-session conversation memory, Chunk 2).
- Access control follows REQ-CC-01 (three-layer RBAC).

---

## Feature F8: Loan Officer Workflow Actions

The Loan Officer persona reviews applications via a chat interface with AI assistance. The LO can review documents, check completeness, respond to conditions, and submit applications to underwriting. AI recommendations are advisory; human confirmation is required for all state-changing actions.

### S-3-F8-01: LO reviews application detail in chat interface

**User Story:**

As a Loan Officer,
I want to review application details through a conversational interface,
so that I can ask questions and get AI assistance while reviewing the file.

**Acceptance Criteria:**

**Scenario: LO asks for application summary**

Given I am in the chat interface for application A001
When I ask: "Give me a summary of this application"
Then the agent responds with:
  - Borrower name, loan type, loan amount
  - Property address, purchase price
  - Current state and days in stage
  - Document completeness status (e.g., "8 of 10 required documents received")
  - Any outstanding issues (quality flags, missing documents, overdue requests)
And the response is generated by the LO Assistant agent

**Scenario: LO asks about specific financial data**

Given application A001 has financial data extracted from documents
When I ask: "What is the borrower's monthly income?"
Then the agent responds with the extracted income value
And cites the source document: "According to the W-2 uploaded on [date], monthly income is $X,XXX."

**Scenario: LO asks about document quality**

Given application A001 has a document with a quality flag: "blurry_scan"
When I ask: "Are there any document issues?"
Then the agent responds: "Yes, the paystub uploaded on [date] has a quality issue: blurry scan. You may want to request a clearer copy."

**Scenario: LO requests document completeness check**

Given application A001 is missing 2 required documents
When I ask: "Is the application complete?"
Then the agent responds: "No, the application is incomplete. Missing documents: [list]. Recommended action: request these documents from the borrower."

**Scenario: LO asks a question outside agent's scope (RBAC enforcement)**

Given I am the LO Assistant agent
When the LO asks: "Show me all applications in the system"
Then I refuse and respond: "I can only show applications assigned to you. You currently have [N] applications in your pipeline."
And the refusal is logged to the audit trail (event_type: "tool_authorization_failure")

**Scenario: Agent provides AI recommendation (not a command)**

Given I am reviewing application A001
When I ask: "Is this application ready for underwriting?"
Then the agent responds with an assessment:
  - "Document completeness: 10 of 10 required documents received."
  - "Quality flags: None."
  - "Financial data: Income, debts, and assets verified."
  - "Recommendation: This application appears ready for underwriting submission."
And the agent does NOT automatically submit the application
And I must explicitly confirm submission (see S-3-F8-03)

**Notes:**
- The LO Assistant agent has access to tools: `application_detail`, `document_status`, `completeness_check`, `draft_communication`, `submit_to_underwriting`, `respond_to_conditions`.
- All tool calls are subject to REQ-CC-12 (four-layer agent security): input validation, system prompt hardening, tool authorization, output filtering.
- The agent provides advisory recommendations, not commands. State-changing actions require explicit LO confirmation.

---

### S-3-F8-02: LO reviews document quality flags and extraction results

**User Story:**

As a Loan Officer,
I want to review document quality flags and extraction results,
so that I can verify the accuracy of extracted data and identify documents that need resubmission.

**Acceptance Criteria:**

**Scenario: LO requests document review**

Given application A001 has uploaded documents
When I ask: "Show me the documents for this application"
Then the agent lists all documents with:
  - Document type (e.g., "W-2", "Paystub", "Bank Statement")
  - Upload date
  - Processing status ("complete", "processing", "failed")
  - Quality flags (if any)
And I can select a document to view details

**Scenario: LO views extraction results for a document**

Given application A001 has a processed W-2 document
When I ask: "Show me the W-2 details"
Then the agent responds with:
  - Extracted fields: employer name, income, tax year
  - Extraction confidence (if available, e.g., "High confidence")
  - Link to view raw document
And the response cites the extraction timestamp

**Scenario: Document has quality flag (blurry scan)**

Given application A001 has a paystub with quality flag "blurry_scan"
When I ask: "Are there any document issues?"
Then the agent responds: "Yes, the paystub uploaded on [date] has a quality issue: blurry scan. Recommended action: request a clearer copy from the borrower."

**Scenario: Document has quality flag (unsigned document)**

Given application A001 has a purchase agreement with quality flag "unsigned_document"
When I ask: "Is the purchase agreement signed?"
Then the agent responds: "No, the purchase agreement uploaded on [date] is unsigned. Recommended action: request a signed copy from the borrower."

**Scenario: Document has quality flag (incorrect time period)**

Given application A001 has a bank statement covering the wrong month
When I ask: "Are the bank statements correct?"
Then the agent responds: "The bank statement uploaded on [date] covers [month/year], but we need statements for [expected month/year]. Recommended action: request the correct bank statements."

**Scenario: Document extraction failed**

Given application A001 has a document with processing status "failed"
When I ask: "Show me document processing status"
Then the agent responds: "Document [type] failed to process. Error: [reason]. Recommended action: review the raw document or request a clearer copy."

**Scenario: LO confirms extraction accuracy**

Given application A001 has extracted income data
When I ask: "Is the extracted income correct?"
Then the agent shows the extracted value and the source document
And I can confirm or correct the value (via form or chat)
And any manual corrections are logged to the audit trail

**Scenario: LO marks a document for resubmission**

Given application A001 has a blurry paystub
When I say: "Mark this paystub for resubmission"
Then the agent updates the document status to "resubmission_requested"
And the agent drafts a communication to the borrower (see F24, S-3-F24-01)
And the document resubmission request is logged to the audit trail

**Notes:**
- Document quality flags are generated by F5 (document extraction and quality assessment, Chunk 2).
- Extraction results are stored in the `document_extractions` table (linked to source documents).
- The LO can view raw documents via a document viewer endpoint (`GET /api/documents/{id}/content`), subject to RBAC (CEO cannot access content, LO can access documents in their pipeline).
- Manual corrections to extracted data are captured in the audit trail per REQ-CC-08.

---

### S-3-F8-03: LO submits application to underwriting via agent tool

**User Story:**

As a Loan Officer,
I want to submit an application to underwriting through the chat interface,
so that I can move the application to the next stage with AI confirmation of readiness.

**Acceptance Criteria:**

**Scenario: LO requests submission readiness assessment**

Given I am reviewing application A001
When I ask: "Is this application ready for underwriting?"
Then the agent performs a completeness check:
  - All required documents received
  - All documents processed (no "processing" or "failed" status)
  - No critical quality flags (blurry scans, unsigned documents)
  - Financial data extracted and verified
And the agent responds: "This application is ready for underwriting. Required documents: [list]. All documents processed successfully. No quality issues. Recommendation: submit to underwriting."
Or if not ready: "This application is not ready. Missing: [list]. Recommended action: [action]."

**Scenario: LO submits application (human-in-the-loop confirmation required)**

Given application A001 is ready for underwriting
When I say: "Submit this application to underwriting"
Then the agent asks for confirmation: "You are about to submit application A001 to underwriting. The application state will change from 'application' to 'underwriting'. Do you want to proceed? (Yes/No)"
When I confirm: "Yes"
Then the agent invokes the `submit_to_underwriting` tool
And the tool transitions the application state from "application" to "underwriting"
And the state transition is logged to the audit trail (event_type: "state_transition", from_state: "application", to_state: "underwriting", user_id: [LO ID])
And the agent responds: "Application A001 has been submitted to underwriting. An underwriter will review it soon."

**Scenario: LO cancels submission**

Given the agent asks for confirmation to submit application A001
When I respond: "No" or "Cancel"
Then the agent does NOT invoke the `submit_to_underwriting` tool
And the application state remains unchanged
And the agent responds: "Submission cancelled. Application A001 remains in the 'application' stage."

**Scenario: Submission attempt when application not ready**

Given application A001 is missing required documents
When I say: "Submit this application to underwriting"
Then the agent refuses: "This application is not ready for underwriting. Missing documents: [list]. Please resolve these issues before submitting."
And no state transition occurs
And the refusal is logged to the audit trail

**Scenario: Unauthorized submission attempt (wrong role)**

Given I am authenticated as a Borrower (not a Loan Officer)
When I attempt to submit an application to underwriting
Then the tool authorization layer (REQ-CC-04) blocks the action
And the agent responds: "You do not have permission to submit applications to underwriting. Only Loan Officers can perform this action."
And the attempt is logged to the audit trail (event_type: "tool_authorization_failure")

**Scenario: Submission attempt for application not assigned to LO**

Given I am Loan Officer "Alice"
And application A002 is assigned to Loan Officer "Bob"
When I attempt to submit application A002
Then the tool authorization layer blocks the action (data scope violation)
And the agent responds: "You do not have permission to modify this application."
And the attempt is logged to the audit trail

**Notes:**
- The `submit_to_underwriting` tool is available only to the LO Assistant agent (role-based tool registry).
- Tool authorization is enforced at execution time (LangGraph pre-tool node) per REQ-CC-12, Layer 3.
- Human-in-the-loop confirmation prevents accidental submissions. The confirmation prompt is part of the agent's system prompt guidance.
- State transitions follow the application state machine defined in the hub (`requirements.md`, Section "Application State Machine").
- All state transitions are audited per REQ-CC-08.

---

### S-3-F8-04: Submission triggers application state transition

**User Story:**

As a Loan Officer,
I want application submission to trigger a state transition,
so that the application enters the underwriting queue and is no longer in my active pipeline stage.

**Acceptance Criteria:**

**Scenario: Successful state transition on submission**

Given application A001 is in state "application"
When I submit the application to underwriting (via S-3-F8-03)
Then the Application Service transitions the state to "underwriting"
And the state transition timestamp is recorded
And the assigned underwriter is set (via round-robin or configured assignment logic)
And the application appears in the underwriting queue (visible to the assigned underwriter)
And the application remains visible in my pipeline but with updated state "underwriting"

**Scenario: State transition audit event**

Given application A001 transitions from "application" to "underwriting"
When the state transition completes
Then an audit event is written with:
  - event_type: "state_transition"
  - user_id: [LO ID]
  - user_role: "loan_officer"
  - application_id: [A001 ID]
  - event_data: { "from_state": "application", "to_state": "underwriting", "reason": "LO submitted application" }
  - session_id: [current session]
And the audit event is append-only per REQ-CC-09

**Scenario: Invalid state transition rejected**

Given application A001 is in state "underwriting"
When I attempt to submit it to underwriting again (invalid transition)
Then the Application Service rejects the transition
And the agent responds: "This application is already in underwriting. You cannot submit it again."
And the invalid transition attempt is logged to the audit trail

**Scenario: State transition allowed transitions (from application state machine)**

Given the application state machine defines valid transitions
When an application is in state "application"
Then valid transitions are: "application" → "underwriting", "application" → "withdrawn"
When an application is in state "underwriting"
Then valid transitions are: "underwriting" → "conditional_approval", "underwriting" → "denied", "underwriting" → "application" (returned for corrections)
And any invalid transition is rejected

**Scenario: Application reappears in underwriting queue**

Given application A001 was submitted to underwriting
When the assigned underwriter views their queue
Then application A001 appears in the underwriter's queue
And the application detail shows: "Submitted by [LO name] on [date/time]"

**Notes:**
- State transitions are governed by the application state machine in the hub (`requirements.md`, Section "Application State Machine").
- Only valid transitions are allowed. Invalid transitions are rejected at the service layer.
- State transitions are audited per REQ-CC-08.
- The transition logic is in the Application Service (`services/application/`), not in the agent layer. The agent calls the service method; the service enforces the state machine.

---

## Feature F24: Loan Officer Communication Drafting

The Loan Officer persona drafts borrower communications with AI assistance. The AI generates drafts incorporating application context, regulatory language, and clarity. The LO reviews and edits drafts before sending. This feature reduces LO workload for routine communications while preserving human oversight.

### S-3-F24-01: LO drafts borrower communication via agent

**User Story:**

As a Loan Officer,
I want the AI to draft borrower communications for me,
so that I can save time on routine messages while ensuring clear, professional communication.

**Acceptance Criteria:**

**Scenario: LO requests initial document request draft**

Given I am reviewing application A001
And the application is missing 3 required documents
When I say: "Draft a document request to the borrower"
Then the agent generates a draft email/message including:
  - Greeting (borrower's name)
  - Context: "We're reviewing your mortgage application for [property address]."
  - List of missing documents: [document types]
  - Instructions: "Please upload these documents through your borrower portal or reply to this message."
  - Closing: "If you have any questions, feel free to reach out."
  - Signature: [LO name, contact info]
And the draft is displayed in the chat interface for review

**Scenario: LO requests condition explanation draft**

Given application A001 has underwriting conditions issued
And one condition is: "Provide explanation for 3-month employment gap in 2023"
When I say: "Draft a message explaining the condition to the borrower"
Then the agent generates a draft including:
  - Context: "The underwriter has reviewed your application and identified a condition that needs clarification."
  - Condition in plain language: "We need an explanation for the 3-month gap in your employment history (March-May 2023). This could be a letter from you explaining the circumstances."
  - Instructions: "Please provide this information as soon as possible so we can move forward with your application."
And the draft avoids underwriting jargon (e.g., replaces "DTI ratio" with "debt-to-income comparison")

**Scenario: LO requests status update draft**

Given application A001 is in "underwriting" stage
And the borrower asked: "What's the status of my application?"
When I say: "Draft a status update for the borrower"
Then the agent generates a draft including:
  - Context: "Your application is currently under review by our underwriting team."
  - Stage description: "This step involves verifying your income, assets, and creditworthiness."
  - Timeline: "Underwriting typically takes 3-5 business days. You should hear from us by [estimated date]."
  - Next steps: "We'll contact you if we need any additional information."

**Scenario: LO requests missing information notice**

Given application A001 has a document with quality flag "blurry_scan"
When I say: "Draft a message asking the borrower to resubmit the paystub"
Then the agent generates a draft including:
  - Context: "We received your paystub, but the scan quality is too low for us to verify the information."
  - Request: "Please upload a clearer copy of your most recent paystub."
  - Instructions: "Make sure the document is well-lit, in focus, and all text is readable."

**Scenario: LO requests document resubmission notice**

Given application A001 has a bank statement with quality flag "incorrect_time_period"
When I say: "Draft a message requesting the correct bank statements"
Then the agent generates a draft including:
  - Context: "We received bank statements for [wrong month/year], but we need statements for [correct month/year]."
  - Request: "Please upload bank statements covering [correct period]."
  - Explanation: "This is required to verify your assets and account activity."

**Scenario: Draft incorporates rate lock urgency (cross-reference F27)**

Given application A001 has a rate lock expiring in 4 days
When I say: "Draft a status update for the borrower"
Then the agent's draft includes urgency language:
  - "Your rate lock is set to expire on [date] ([X] days from now). To preserve your current interest rate, we need to complete underwriting and receive all required documents by [date]."
  - "Please respond to any outstanding requests as soon as possible."

**Notes:**
- The `draft_communication` tool is available to the LO Assistant agent.
- Drafts incorporate application context: borrower name, loan type, property address, current stage, outstanding documents, conditions, rate lock status.
- Drafts avoid jargon and translate underwriting terms into borrower-friendly language (e.g., "debt-to-income ratio" → "comparison of your monthly debts to your income").
- Drafts are advisory. The LO must review and approve before sending (see S-3-F24-03).
- The agent does not send messages automatically. Sending is a manual LO action (or a separate tool invocation with confirmation).

---

### S-3-F24-02: Agent incorporates application context into draft

**User Story:**

As a Loan Officer,
I want drafted communications to include specific details from the application,
so that messages are accurate, personalized, and require minimal editing.

**Acceptance Criteria:**

**Scenario: Draft includes borrower name**

Given I am drafting a message for application A001
And the borrower's name is "Jane Smith"
When the agent generates a draft
Then the greeting is: "Dear Jane," or "Hi Jane,"
And the signature includes my name as the LO

**Scenario: Draft includes loan details**

Given application A001 is for a $350,000 purchase loan
And the property address is "123 Main St, Denver, CO"
When the agent generates a draft
Then the draft includes: "We're reviewing your mortgage application for the property at 123 Main St, Denver, CO (loan amount: $350,000)."

**Scenario: Draft includes specific missing documents**

Given application A001 is missing:
  - W-2 for 2023
  - Recent paystub
  - Bank statements for August 2024
When the agent generates a document request draft
Then the draft lists all three documents by name
And provides instructions for each (if applicable)

**Scenario: Draft includes rate lock expiration date**

Given application A001 has a rate lock expiring on 12/15/2024
When the agent generates a status update
Then the draft includes: "Your rate lock expires on December 15, 2024."
And if the expiration is within 7 days, includes urgency language

**Scenario: Draft includes condition details**

Given application A001 has a condition: "Provide letter of explanation for large deposit on 08/10/2024 ($12,000)"
When the agent generates a condition explanation draft
Then the draft includes the specific condition text
And translates it to borrower-friendly language: "We noticed a large deposit of $12,000 on August 10, 2024. Please provide a letter explaining the source of this deposit."

**Scenario: Draft references current stage and timeline**

Given application A001 is in "underwriting" stage
And the expected time in underwriting is 3-5 days
And the application entered underwriting 2 days ago
When the agent generates a status update
Then the draft includes: "Your application has been in underwriting for 2 days. This step typically takes 3-5 business days."

**Scenario: Draft avoids including HMDA data (cross-cutting concern)**

Given application A001 has HMDA demographic data
When the agent generates any communication draft
Then the draft does NOT include any demographic information (race, ethnicity, sex)
And the output filter (REQ-CC-12, Layer 4) blocks any inadvertent demographic references
And if a demographic reference is detected, the draft is flagged and regenerated

**Notes:**
- Application context is sourced from: `applications` table (borrower name, loan details, property address, current state), `documents` table (missing documents, quality flags), `rate_locks` table (expiration date), `conditions` table (issued conditions).
- The agent queries these tables via tools (subject to data scope filtering per REQ-CC-01).
- Drafts are generated with full context but never include HMDA demographic data (enforced by output filtering per REQ-CC-12 and REQ-CC-14).

---

### S-3-F24-03: LO reviews and edits before sending

**User Story:**

As a Loan Officer,
I want to review and edit AI-drafted communications before sending,
so that I can ensure accuracy, tone, and compliance with my communication standards.

**Acceptance Criteria:**

**Scenario: LO reviews draft in chat interface**

Given the agent has generated a communication draft
When the draft is displayed
Then I see the full draft text in a structured format:
  - Subject line (if email)
  - Greeting
  - Body
  - Closing
  - Signature
And I see options: "Edit", "Send", "Regenerate", "Cancel"

**Scenario: LO edits draft before sending**

Given the agent has generated a draft
When I click "Edit"
Then a text editor opens with the draft content
And I can modify any part of the draft (subject, body, closing)
When I save my edits
Then the edited version is displayed for final review
And the agent does not regenerate or overwrite my edits

**Scenario: LO sends edited draft**

Given I have reviewed and edited a draft
When I click "Send"
Then the message is sent to the borrower via the configured channel (email, SMS, in-app notification)
And the sent message is logged to the audit trail (event_type: "communication_sent", user_id: [LO ID], application_id: [A001 ID], message_content: [draft text])
And I receive confirmation: "Message sent to [borrower name]."

**Scenario: LO regenerates draft**

Given the agent has generated a draft
And I am not satisfied with the draft
When I click "Regenerate"
Then I can provide additional instructions (e.g., "Make it shorter" or "Include the closing date")
And the agent generates a new draft incorporating my feedback
And the previous draft is discarded

**Scenario: LO cancels draft**

Given the agent has generated a draft
When I click "Cancel"
Then the draft is discarded
And no message is sent
And I return to the chat interface

**Scenario: Draft is NOT sent automatically**

Given the agent has generated a draft
When the draft is displayed
Then the message is NOT sent automatically
And I must explicitly click "Send" to deliver the message
And the agent waits for my confirmation

**Scenario: Sent communication is audited**

Given I send a communication to the borrower
When the message is sent
Then an audit event is written with:
  - event_type: "communication_sent"
  - user_id: [LO ID]
  - application_id: [A001 ID]
  - event_data: { "channel": "email", "subject": "[subject]", "body_length": [N characters], "edited": true/false }
  - session_id: [current session]
And the audit event does not include the full message body (to avoid audit log bloat), only metadata

**Scenario: Communication template library (future enhancement)**

Given I frequently send similar messages
When I draft a communication
Then the agent suggests: "Would you like to save this as a template for future use?"
And if I save it, I can reuse the template for other applications
And templates are personal to the LO (not shared across LOs)

**Notes:**
- The "Send" action is a separate tool invocation (`send_communication`) or a manual LO action outside the agent (e.g., email client, CRM integration).
- Sent communications are logged to the audit trail per REQ-CC-08.
- The draft review/edit flow is implemented in the frontend UI (text editor, confirmation buttons).
- The agent does NOT send messages automatically. Human-in-the-loop is required for all outbound communications.

---

## Phase 3 Summary

**Phase 3 deliverable:** Loan Officer persona fully functional. LOs can view their pipeline, identify urgent applications, review documents and extraction results, submit applications to underwriting, and draft borrower communications with AI assistance.

**Key integration points:**
- **F7 (Pipeline)** integrates with F27 (rate lock tracking), F6 (document completeness), and the application state machine.
- **F8 (Review and submission)** integrates with F5 (document extraction), F6 (completeness), and feeds into F11 (underwriting workflow, Chunk 4).
- **F24 (Communication drafting)** integrates with F27 (rate lock status), F28 (document requests), and application context.

**Cross-cutting enforcement:**
- All stories enforce REQ-CC-01 (three-layer RBAC) -- LO sees only own pipeline.
- All state transitions are audited per REQ-CC-08.
- All tool calls are subject to REQ-CC-12 (four-layer agent security).
- All communications are human-in-the-loop per AI compliance guidelines (REQ-CC-15, REQ-CC-16).

**Open questions (none specific to this chunk):**
- REQ-OQ-03: What fields constitute "application context" for LO communication drafts? -- Suggested: borrower name, application ID, loan type, property address, current stage. (See hub.)

**Assumptions:**
- Rate lock expiration thresholds: < 3 days = Critical, < 7 days = High (per REQ-OQ-02 suggested defaults).
- Stage timing expectations are configured per-stage in `config/app.yaml` or derived from historical averages.
- The LO Assistant agent's system prompt includes human-in-the-loop confirmation guidance for state-changing actions.
- Communication delivery mechanism (email, SMS, in-app) is outside the scope of this chunk -- the "Send" action is modeled as a tool or manual LO action.

---

**Chunk 3 complete. Total acceptance criteria scenarios: 46 (F7: 14, F8: 18, F24: 14). Estimated line count: ~1100 lines.**

