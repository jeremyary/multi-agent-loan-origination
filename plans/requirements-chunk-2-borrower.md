# Requirements Chunk 2: Borrower Experience

## Chunk Overview

This chunk covers **Phase 2 features** that deliver the borrower persona experience. It includes 34 stories spanning:

- **F3:** Borrower Authentication and Personal Assistant (5 stories)
- **F4:** Document Upload Workflow (4 stories)
- **F5:** Document Extraction and Analysis (4 stories)
- **F6:** Document Completeness and Application Status (5 stories)
- **F15:** Comprehensive Audit Trail (6 stories)
- **F19:** Cross-Session Conversation Memory (4 stories)
- **F27:** Rate Lock and Closing Date Tracking (3 stories)
- **F28:** Borrower Condition Response (3 stories)

**Cross-references:**
- Hub document: `/home/jary/git/agent-scaffold/plans/requirements.md`
- Product plan: `/home/jary/git/agent-scaffold/plans/product-plan.md` (see Flow 2: Borrower Application Submission, Flow 3: Borrower Document Upload, Flow 8: Borrower Responds to Conditions)
- Architecture: `/home/jary/git/agent-scaffold/plans/architecture.md` (see Section 2.3 Agent Layer, Section 2.5 Document Processing, Section 3.4 Audit Trail, Section 3.5 Conversation Persistence)
- Related chunks:
  - Chunk 1 (Foundation): Authentication (S-1-F2-*), RBAC (S-1-F14-*), HMDA isolation (S-1-F25-*)
  - Chunk 3 (Loan Officer): LO reviews documents and submissions from this chunk
  - Chunk 4 (Underwriting): Underwriter issues conditions that borrowers respond to (F28)

**Key architectural notes:**
- All stories in this chunk assume cross-cutting requirements from the hub (REQ-CC-01 through REQ-CC-22)
- RBAC enforcement is three-layer (API, service, agent) per REQ-CC-01
- Audit events are append-only per REQ-CC-09
- HMDA demographic data filter is enforced during document extraction per REQ-CC-05
- Conversation checkpoints are user-scoped per F19 and Section 3.5 of architecture
- F4 form fallback contingency: conversational intake is primary; structured forms are a fallback if conversational-only proves unreliable for specific sections

---

## F3: Borrower Authentication and Personal Assistant

### S-2-F3-01: Borrower initiates new application via chat

**User Story:**

As a borrower,
I want to initiate a formal mortgage application through a conversational interface,
so that I can start the application process naturally without navigating complex forms.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I am an authenticated borrower (role = 'borrower')
  And I have no existing application in progress
When I open the chat interface
  And I say "I want to apply for a mortgage"
Then the agent confirms it will help me start an application
  And the agent asks for the first required piece of information (loan type or property address)
  And the application state transitions from nonexistent to 'application'
  And an audit event is logged with event_type = 'query' and application_id set
```

**Error Scenarios:**

```gherkin
Given I am an authenticated borrower
  And I already have an application in state 'application'
When I say "I want to apply for a mortgage"
Then the agent informs me that I have an existing application
  And the agent offers to continue the existing application or review its status
  And no new application is created
```

```gherkin
Given I am an unauthenticated user (no valid token)
When I attempt to access the borrower chat interface
Then I am redirected to the Keycloak login page
  And no chat interaction occurs
```

**Edge Cases:**

```gherkin
Given I am an authenticated borrower
When I say "I'd like to start a loan application"
Then the agent interprets the intent as starting a mortgage application (synonym matching)
  And proceeds with the initiation flow
```

```gherkin
Given I am an authenticated borrower
  And I have an application in state 'withdrawn'
When I say "I want to apply for a mortgage"
Then the agent treats this as a new application request
  And creates a new application (not reviving the withdrawn one)
```

**Notes:**
- Per REQ-CC-08, the user query and agent response are logged to the audit trail
- State transition is logged per the Application State Machine (Section: State transition audit)
- Cross-reference: S-1-F2-01 (Authentication), S-1-F14-01 (RBAC enforcement)

---

### S-2-F3-02: Borrower provides application data conversationally

**User Story:**

As a borrower,
I want to provide application details through natural conversation,
so that I can complete the application without filling out traditional forms.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I am an authenticated borrower
  And I have an application in state 'application'
When the agent asks "What is your annual income?"
  And I respond "I make $75,000 per year"
Then the agent acknowledges the data
  And the agent stores the income value in the application_financials table
  And the agent proceeds to the next required field
  And an audit event is logged with event_type = 'data_access' and event_data containing the collected field
```

```gherkin
Given I am providing application data conversationally
When the agent asks "What type of property are you purchasing?"
  And I respond "A single-family home"
Then the agent extracts the property type (standardized: 'single_family')
  And stores it in the applications table
  And proceeds to the next question
```

**Error Scenarios:**

```gherkin
Given the agent asks "What is your annual income?"
When I respond "I'm not sure"
Then the agent offers to skip this field for now or provides guidance on where to find the information
  And the field remains unfilled in the application
  And the agent marks this field as pending follow-up
```

```gherkin
Given the agent asks "What is your date of birth?"
When I respond "My birthday is next Tuesday"
Then the agent detects an invalid date format
  And the agent asks for clarification: "I need your full date of birth, like January 15, 1985"
  And no data is stored until a valid date is provided
```

**Co-Borrower Support:**

```gherkin
Given I am providing application data conversationally
When I say "My spouse will be on the loan with me"
Then the agent acknowledges co-borrower presence
  And the agent asks for co-borrower information (name, income, employment)
  And co-borrower data is stored in the co_borrowers table linked to my application
```

**Data Correction:**

```gherkin
Given I previously stated "My annual income is $75,000"
  And the agent has stored this value
When I say "Actually, my salary is $85,000"
Then the agent detects a correction intent
  And the agent confirms "I'll update your annual income to $85,000"
  And the agent updates the application_financials record
  And an audit event is logged with event_type = 'data_access' and event_data showing the correction (old value -> new value)
```

**Edge Cases:**

```gherkin
Given the agent asks "What is your employment status?"
When I respond "I'm self-employed as a consultant"
Then the agent extracts employment_status = 'self_employed'
  And the agent follows up with self-employed-specific questions (business name, tax returns)
```

```gherkin
Given I am providing financial data conversationally
When I respond with multiple data points in one message: "I make $75,000 per year, I've been at my job for 5 years, and my employer is Acme Corp"
Then the agent extracts all three data points (income, tenure, employer)
  And stores each in the appropriate field
  And proceeds to the next unanswered required field
```

**Notes:**
- Data validation occurs at extraction time -- the agent validates format and reasonableness before storage
- All data collection is logged per REQ-CC-08
- Per REQ-CC-13, the agent must not ask for or store demographic data (HMDA data is collected separately per F25)
- Cross-reference: S-2-F3-04 (data review and correction), S-1-F25-01 (HMDA data is collected on a separate path)

---

### S-2-F3-03: Agent validates data format and completeness

**User Story:**

As a borrower,
I want the agent to validate my input and guide me toward complete data,
so that I don't submit an incomplete or incorrectly formatted application.

**Acceptance Criteria:**

**Format Validation:**

```gherkin
Given the agent asks for a Social Security Number
When I respond "123-45-6789"
Then the agent validates the format (XXX-XX-XXXX)
  And stores the value
  And proceeds to the next field
```

```gherkin
Given the agent asks for a Social Security Number
When I respond "12345"
Then the agent detects an invalid format
  And the agent responds: "That doesn't look like a full Social Security Number. It should be 9 digits, like 123-45-6789."
  And the agent waits for a valid input before proceeding
```

**Reasonableness Validation:**

```gherkin
Given the agent asks for annual income
When I respond "I make $500,000,000 per year"
Then the agent detects an unreasonably high value
  And the agent asks for confirmation: "Just to confirm, your annual income is $500 million?"
  And if I confirm, the agent stores it (but flags for LO review)
```

```gherkin
Given the agent asks for my date of birth
When I respond "January 1, 2020"
Then the agent detects an unreasonably recent date (borrower would be 6 years old)
  And the agent asks for clarification: "That would make you very young. Can you double-check your birth year?"
```

**Completeness Checking:**

```gherkin
Given I have provided 80% of required application fields
When I say "Am I done yet?"
Then the agent lists the remaining required fields
  And the agent offers to continue collecting them or save progress
```

```gherkin
Given I have provided all required fields for my loan type
When I say "I think I'm done"
Then the agent confirms: "You've provided all required information. Your application is ready for review."
  And the agent offers to summarize the application or proceed to document upload
```

**Edge Cases:**

```gherkin
Given the agent asks for an email address
When I respond "john at example dot com"
Then the agent extracts the email format (john@example.com)
  And validates the format
  And stores the normalized value
```

```gherkin
Given the agent asks for a property address
When I respond "123 Main Street"
Then the agent detects a partial address (missing city, state, ZIP)
  And the agent follows up: "What city is that in?"
  And continues collecting the full address components
```

**Notes:**
- Validation rules are data-type-specific (SSN format, email format, date reasonableness, numeric ranges)
- Validation failures are logged as warnings in the audit trail
- The agent does not proceed to the next field until validation passes or the user explicitly skips the field
- Cross-reference: S-2-F3-02 (data collection), S-2-F3-04 (review and correction)

---

### S-2-F3-04: Borrower can review and correct collected data

**User Story:**

As a borrower,
I want to review the data I've provided and make corrections,
so that I can ensure my application is accurate before submission.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I have provided application data conversationally
When I say "Can you show me what you have so far?"
Then the agent displays a structured summary of all collected fields
  And the summary includes field names and values (e.g., "Annual Income: $75,000")
  And the agent asks if I'd like to make any corrections
```

```gherkin
Given the agent displays my application summary
When I say "Change my income to $85,000"
Then the agent updates the income field
  And the agent confirms: "I've updated your annual income to $85,000"
  And an audit event is logged showing the correction
```

**Proactive Correction:**

```gherkin
Given I previously stated "My annual income is $75,000"
When I say later in the conversation "Actually, my salary is $85,000"
Then the agent detects a correction without requiring explicit "review" mode
  And the agent updates the field
  And confirms the change
```

**Batch Correction:**

```gherkin
Given the agent displays my application summary
When I say "My income is $85,000, and I've been at my job for 6 years, not 5"
Then the agent updates both fields
  And confirms both changes: "I've updated your annual income to $85,000 and your employment tenure to 6 years"
```

**Ambiguous Correction:**

```gherkin
Given my application includes both my income and my co-borrower's income
When I say "Change the income to $90,000"
Then the agent asks for clarification: "Do you mean your income or your co-borrower's income?"
  And waits for clarification before applying the change
```

**Edge Cases:**

```gherkin
Given I have not yet provided any data
When I say "Can you show me what you have so far?"
Then the agent responds: "You haven't provided any information yet. Let's start with the basics."
  And the agent offers to begin data collection
```

```gherkin
Given I have provided application data
When I say "Delete my income"
Then the agent warns: "Annual income is a required field. If you remove it, your application won't be complete."
  And the agent asks for confirmation before clearing the field
```

**Notes:**
- All corrections are logged to the audit trail per REQ-CC-08
- The review summary masks sensitive fields if displayed in a non-secure context (though the chat interface is secure, this is defense-in-depth)
- Cross-reference: S-2-F3-02 (data collection), S-2-F3-03 (validation)

---

### S-2-F3-05: Form fallback for complex financial data entry (contingency)

**User Story:**

As a borrower,
I want to use a structured form if the conversational interface becomes too cumbersome for specific sections,
so that I can complete my application efficiently even if conversational-only proves too brittle.

**Acceptance Criteria:**

**Fallback Trigger:**

```gherkin
Given I am providing financial data conversationally
  And the agent detects that I have made multiple correction attempts or expressed frustration
When the agent determines that a structured form may be more appropriate for this section
Then the agent offers: "Would you like to fill out this section using a form instead? It might be easier."
  And if I accept, the agent transitions to a form view for that section
```

```gherkin
Given I am at a section with many interdependent numeric fields (e.g., detailed asset breakdown)
When I say "This is getting confusing, can I just type it all in?"
Then the agent offers a form fallback
  And the form is pre-populated with any data I've already provided conversationally
```

**Form-to-Conversational Transition:**

```gherkin
Given I am using the form fallback for a section
When I complete the form and submit
Then the data is validated and stored (same as conversational path)
  And the agent returns to conversational mode: "Thanks! I've recorded that. Let's move on to..."
```

**Edge Cases:**

```gherkin
Given conversational intake is working smoothly
When I never request a form fallback
Then the entire application is completed conversationally (no form is shown)
  And the form fallback remains unused
```

```gherkin
Given I am using the form fallback for financial data
When I leave a required field blank and click submit
Then the form displays validation errors (same validation rules as conversational path)
  And I cannot proceed until the field is filled
```

**Notes:**
- The form fallback is a **contingency** per architecture Section 2.1. Conversational-only is the primary path. Forms are used only if conversational proves too brittle for a specific section (e.g., complex asset/liability breakdown).
- The agent does not proactively suggest forms unless the user expresses frustration or the agent detects repeated correction cycles
- All form-submitted data is logged to the audit trail identically to conversational data (no separate audit path)
- Cross-reference: Architecture Section 2.1 (F4 form fallback contingency)

---

## F4: Document Upload Workflow

### S-2-F4-01: Borrower uploads documents through chat

**User Story:**

As a borrower,
I want to upload documents directly within the chat interface,
so that I can provide required documentation without leaving the conversation.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I am an authenticated borrower with an application in state 'application'
When I say "I have my W-2 to upload"
Then the agent responds: "Great! You can upload your W-2 here." and provides an upload button/link
  And I select a file (e.g., w2-2024.pdf) and upload
  And the agent confirms: "I've received your W-2. Processing it now."
  And the document is stored with status = 'processing'
```

```gherkin
Given the agent has asked me to provide a specific document (e.g., "Can you upload your most recent pay stub?")
When I upload the file through the chat interface
Then the agent links the uploaded document to the application
  And the document type is inferred from the agent's request (document_type = 'pay_stub')
```

**Error Scenarios:**

```gherkin
Given I attempt to upload a document
When the file size exceeds the maximum allowed size (e.g., 50 MB)
Then the upload is rejected
  And the agent responds: "That file is too large. Please upload a file smaller than 50 MB."
```

```gherkin
Given I attempt to upload a document
When the file type is not supported (e.g., .exe, .zip)
Then the upload is rejected
  And the agent responds: "I can't process that file type. Please upload a PDF, JPG, or PNG."
```

**Multiple Document Upload:**

```gherkin
Given I say "I have my W-2s for the last two years"
When I upload two files (w2-2024.pdf, w2-2023.pdf)
Then the agent accepts both uploads
  And the agent confirms: "I've received both W-2s. Processing them now."
  And each document is stored as a separate record with document_type = 'w2'
```

**Edge Cases:**

```gherkin
Given I upload a document without context
When I just drop a file into the chat interface without saying what it is
Then the agent asks: "I've received your file. What document is this? (e.g., W-2, pay stub, bank statement)"
  And I provide the document type
  And the agent stores it with the correct document_type
```

```gherkin
Given I have no application in progress
When I attempt to upload a document
Then the agent responds: "I don't have an application to attach this to. Would you like to start a new application?"
```

**Notes:**
- Per REQ-CC-08, the document upload event is logged to the audit trail
- Uploaded files are stored to object storage per architecture Section 2.5
- Document metadata is stored in the documents table immediately; extraction happens asynchronously
- Cross-reference: S-2-F4-02 (storage), S-2-F5-01 (extraction), Architecture Section 2.5 (Document Processing)

---

### S-2-F4-02: Document upload stores raw file to object storage

**User Story:**

As the system,
I want to store the raw uploaded file immediately to object storage,
so that the original document is preserved regardless of extraction success.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given a borrower uploads a document through the chat interface
When the file is received by the API gateway
Then the file is written to object storage with a unique identifier
  And a document metadata record is created in the documents table with:
    - document_id (UUID)
    - application_id (linked to the borrower's application)
    - document_type (inferred or user-provided)
    - file_path (object storage path)
    - upload_date (timestamp)
    - status = 'processing'
    - uploaded_by = user_id
  And the raw file is NOT deleted after extraction (original is preserved)
```

**Error Scenarios:**

```gherkin
Given a borrower uploads a document
When the object storage backend is unavailable
Then the upload fails
  And the agent responds: "I couldn't save your file right now. Please try again in a moment."
  And no document metadata record is created
  And an audit event is logged with event_type = 'system' and event_data indicating the storage failure
```

**Edge Cases:**

```gherkin
Given a borrower uploads a document with the same filename as a previously uploaded document
When the file is stored to object storage
Then the new file is stored with a unique identifier (UUID-based path, not filename-based)
  And both documents coexist without collision
```

```gherkin
Given a borrower uploads a very large document (e.g., 48 MB, just under the limit)
When the file is stored to object storage
Then the upload succeeds
  And the file is written in chunks to handle large files efficiently
```

**Notes:**
- Object storage path format: `{application_id}/{document_id}/{filename}`
- Local development uses local filesystem; production uses S3-compatible storage (ODF/MinIO) per architecture Section 7.1
- The raw file is never deleted, even if extraction fails -- this supports human review and re-extraction
- Cross-reference: Architecture Section 2.5 (Document Processing), Section 3.2 (document domain schema)

---

### S-2-F4-03: Document processing status visible to borrower

**User Story:**

As a borrower,
I want to see the processing status of my uploaded documents,
so that I know whether the system has successfully extracted information from them.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I have uploaded a document
When the document is being processed (extraction in progress)
Then the chat interface shows a status indicator: "Processing your W-2..."
  And the document status in the documents table is 'processing'
```

```gherkin
Given the document extraction completes successfully
When I view the document status (via chat or document list UI)
Then the status is 'completed'
  And the agent confirms: "I've processed your W-2 and extracted the key information."
```

**Error Scenarios:**

```gherkin
Given a document extraction fails (e.g., file is corrupted, unreadable)
When I view the document status
Then the status is 'failed'
  And the agent explains: "I couldn't read that document. It may be corrupted or blurry. Can you upload it again?"
```

**Quality Flags Visible:**

```gherkin
Given a document is processed but flagged with quality issues (e.g., 'blurry')
When I view the document status
Then the status is 'completed_with_issues'
  And the agent explains: "I processed your W-2, but the image is a bit blurry. Please review the extracted information and consider uploading a clearer version."
```

**Polling for Status:**

```gherkin
Given I have uploaded a document
  And extraction is in progress
When I ask "Is my W-2 processed yet?"
Then the agent checks the current document status
  And responds with the current state: "Still processing. I'll let you know when it's done."
```

**Edge Cases:**

```gherkin
Given I have uploaded multiple documents
When I ask "What documents have you processed?"
Then the agent lists all uploaded documents with their statuses
  And the list shows document_type and status for each
```

```gherkin
Given a document has been processing for an unusually long time (> 5 minutes)
When I check the status
Then the agent acknowledges the delay: "This is taking longer than usual. Let me check on it."
  And a system alert is logged for operator investigation
```

**Notes:**
- Document status is stored in the documents table: 'processing', 'completed', 'completed_with_issues', 'failed'
- The agent has access to the `document_status` tool per architecture Section 2.3 (Borrower Assistant tools)
- Cross-reference: S-2-F4-04 (agent notification on completion), S-2-F5-02 (quality assessment flags)

---

### S-2-F4-04: Agent notifies borrower when document processing completes

**User Story:**

As a borrower,
I want to be notified when my uploaded document has been processed,
so that I know the system is ready for the next step.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I have uploaded a document
  And I am still in the chat session
When the document extraction completes successfully
Then the agent sends a message: "I've finished processing your W-2. Here's what I found: [summary of extracted data]."
  And the agent offers to continue with the next required document
```

**Asynchronous Notification:**

```gherkin
Given I have uploaded a document
  And I have closed the chat session
When the document extraction completes
Then a notification is recorded for the next time I open the chat
  And when I return, the agent says: "Welcome back! I've processed the W-2 you uploaded earlier."
```

**Error Notification:**

```gherkin
Given I have uploaded a document
When the document extraction fails
Then the agent notifies me: "I had trouble processing your W-2. It may be unreadable. Can you upload it again or try a different file?"
```

**Quality Issue Notification:**

```gherkin
Given I have uploaded a document
When the document is processed but flagged with quality issues (e.g., 'wrong_period')
Then the agent notifies me: "I processed your pay stub, but it's from 2022. I need your most recent pay stub. Can you upload a more recent one?"
```

**Edge Cases:**

```gherkin
Given I have uploaded multiple documents simultaneously
When all documents finish processing
Then the agent sends a batch notification: "I've finished processing all three documents: W-2, pay stub, and bank statement."
  And the agent summarizes the results for each
```

```gherkin
Given I upload a document and immediately ask a different question
When the document processing completes while I'm mid-conversation
Then the agent interleaves the notification naturally: "By the way, I've finished processing your W-2. [returns to the current topic]."
```

**Notes:**
- Notification is delivered through the chat interface (WebSocket message)
- If the user is offline, the notification is queued and delivered on the next session (via conversation memory)
- Extraction results summary includes key extracted fields (income, employer, document period) but not the full raw data
- Cross-reference: S-2-F5-01 (extraction), S-2-F19-01 (cross-session memory for offline notifications)

---

## F5: Document Extraction and Analysis

### S-2-F5-01: Document extraction produces structured data

**User Story:**

As the system,
I want to extract structured data from uploaded documents using LLM-based extraction,
so that key information is available for underwriting without manual data entry.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given a borrower has uploaded a W-2 document (PDF)
When the extraction pipeline processes the document
Then structured data is extracted including:
  - employer_name (text)
  - employee_name (text)
  - tax_year (integer)
  - wages (decimal)
  - federal_tax_withheld (decimal)
  And the extracted data is stored in the document_extractions table with source_document_id = document_id
  And the document status is updated to 'completed'
```

```gherkin
Given a borrower has uploaded a pay stub document
When the extraction pipeline processes the document
Then structured data is extracted including:
  - employer_name (text)
  - pay_period_start (date)
  - pay_period_end (date)
  - gross_pay (decimal)
  - net_pay (decimal)
  - ytd_gross_pay (decimal)
  And the extraction is stored in document_extractions
```

**Document-Type-Specific Extraction:**

```gherkin
Given a borrower has uploaded a bank statement
When the extraction pipeline processes the document
Then structured data is extracted including:
  - bank_name (text)
  - account_number (text, last 4 digits only)
  - statement_period_start (date)
  - statement_period_end (date)
  - ending_balance (decimal)
  - average_balance (decimal)
  And the extraction is stored in document_extractions
```

**Error Scenarios:**

```gherkin
Given a borrower has uploaded a document
When the extraction pipeline detects the document is unreadable (corrupted file)
Then no structured data is extracted
  And the document status is set to 'failed'
  And an audit event is logged with event_type = 'system' and event_data indicating extraction failure
```

```gherkin
Given a borrower has uploaded a document
When the extraction pipeline detects the document type does not match the declared type (e.g., labeled as W-2 but is actually a pay stub)
Then a quality flag is set: document_type_mismatch = true
  And the document status is set to 'completed_with_issues'
  And the agent notifies the borrower of the mismatch
```

**Edge Cases:**

```gherkin
Given a borrower has uploaded a multi-page document (e.g., 3-page bank statement)
When the extraction pipeline processes the document
Then data is extracted from all pages
  And the extraction result is a single consolidated record (not per-page records)
```

```gherkin
Given a borrower has uploaded a document with handwritten annotations
When the extraction pipeline processes the document
Then the LLM attempts to extract typed text and ignores handwriting (PoC limitation)
  And if key fields are handwritten only, the extraction may fail or be incomplete
```

**Notes:**
- Extraction uses LLM-based structured output per architecture Section 2.5
- Extraction prompts are document-type-specific (W-2 prompt, pay stub prompt, bank statement prompt)
- Extraction results are stored in document_extractions with provenance (source_document_id)
- Per REQ-CC-08, extraction events are logged to the audit trail
- Cross-reference: S-2-F5-03 (demographic data filter), Architecture Section 2.5 (Document Processing)

---

### S-2-F5-02: Quality assessment flags blurry/incomplete/incorrect documents

**User Story:**

As the system,
I want to assess document quality during extraction and flag issues,
so that borrowers and loan officers are alerted to documents that may require resubmission.

**Acceptance Criteria:**

**Blurry Documents:**

```gherkin
Given a borrower has uploaded a blurry or low-resolution document
When the extraction pipeline assesses quality
Then a quality flag is set: blurry = true
  And the document status includes 'completed_with_issues'
  And the agent notifies the borrower: "The document you uploaded is a bit blurry. I did my best to extract the information, but please review it and consider uploading a clearer version."
```

**Incorrect Time Period:**

```gherkin
Given a borrower has uploaded a pay stub
  And the pay stub is from 2022 (more than 30 days old)
When the extraction pipeline assesses quality
Then a quality flag is set: wrong_period = true
  And the agent notifies the borrower: "This pay stub is from 2022. I need your most recent pay stub (within the last 30 days)."
```

**Missing Pages:**

```gherkin
Given a borrower has uploaded a W-2
  And the W-2 is missing key sections (e.g., page 2 with state tax withholding)
When the extraction pipeline assesses quality
Then a quality flag is set: incomplete = true
  And the agent notifies the borrower: "This W-2 appears to be missing pages. Can you upload the complete document?"
```

**Unsigned Documents:**

```gherkin
Given a borrower has uploaded a loan application form that requires a signature
When the extraction pipeline assesses quality
Then a quality flag is set: unsigned = true
  And the agent notifies the borrower: "This form needs to be signed. Please sign and re-upload."
```

**Wrong Document Type:**

```gherkin
Given a borrower uploads a document labeled as "W-2"
  And the document is actually a pay stub
When the extraction pipeline assesses quality
Then a quality flag is set: document_type_mismatch = true
  And the agent notifies the borrower: "This looks like a pay stub, not a W-2. Can you upload your W-2?"
```

**Edge Cases:**

```gherkin
Given a borrower uploads a document with no quality issues
When the extraction pipeline assesses quality
Then no quality flags are set
  And the document status is 'completed' (not 'completed_with_issues')
  And the agent confirms extraction success without warnings
```

```gherkin
Given a borrower uploads a document with multiple quality issues (blurry AND wrong period)
When the extraction pipeline assesses quality
Then multiple quality flags are set: blurry = true, wrong_period = true
  And the agent notifies the borrower of both issues
```

**Notes:**
- Quality assessment is LLM-based per architecture Section 2.5
- Quality flags are stored in the documents table as boolean columns or a JSONB quality_flags field
- Quality assessment happens after extraction (both are part of the async processing pipeline)
- Cross-reference: S-2-F4-03 (status visibility), S-2-F6-01 (missing documents), Architecture Section 2.5

---

### S-2-F5-03: Demographic data filter excludes HMDA data from lending path

**User Story:**

As the system,
I want to detect and exclude demographic data during document extraction,
so that HMDA data does not enter the lending decision path.

**Acceptance Criteria:**

**Happy Path (No Demographic Data Detected):**

```gherkin
Given a borrower has uploaded a W-2 document
When the extraction pipeline processes the document
  And the document contains no demographic data
Then the extraction completes normally
  And all extracted fields are stored in document_extractions
  And no exclusion event is logged
```

**Demographic Data Detected and Excluded:**

```gherkin
Given a borrower has uploaded a document that contains demographic data (e.g., a form with race/ethnicity checkboxes)
When the extraction pipeline processes the document
  And the demographic data filter detects the presence of demographic fields (keyword matching: race, ethnicity, sex, marital status)
Then the demographic data is excluded from the extraction result
  And the lending-path fields are stored in document_extractions
  And the exclusion is logged to the audit trail with:
    - event_type = 'system'
    - event_data = { "reason": "demographic_data_excluded", "document_id": "...", "excluded_fields": ["race", "ethnicity"] }
  And the borrower is NOT notified (this is a silent system operation)
```

**Semantic Similarity Detection:**

```gherkin
Given a borrower has uploaded a document with indirect demographic references (e.g., "applicant identifies as Hispanic")
When the extraction pipeline processes the document
  And the demographic data filter uses semantic similarity to detect demographic content
Then the indirect reference is excluded from the extraction result
  And the exclusion is logged to the audit trail
```

**False Negative Mitigation:**

```gherkin
Given the demographic data filter misses an indirect demographic reference
When the lending agent uses the extracted data to generate a response
Then the agent output filter (Layer 4 per REQ-CC-12) scans the agent response for demographic patterns
  And if detected, the response is redacted and the incident is logged
  And a system alert is generated for operator review
```

**Edge Cases:**

```gherkin
Given a borrower has uploaded a document with the word "race" in a non-demographic context (e.g., "rate race", "race to close")
When the demographic data filter processes the document
Then the filter distinguishes context using semantic similarity
  And the non-demographic usage is NOT excluded
```

```gherkin
Given a borrower has uploaded a document with demographic data in an image (e.g., a scanned form with handwritten demographic checkboxes)
When the extraction pipeline processes the document
Then the filter attempts OCR-based detection (PoC limitation: may miss handwritten content)
  And if the handwritten data is extracted by the LLM, the filter excludes it
```

**Notes:**
- Per REQ-CC-05, demographic data filtering is the second stage of HMDA isolation (after collection, before storage)
- Detection uses keyword matching + semantic similarity per architecture Section 2.5
- The demographic data filter is a separate step in the extraction pipeline, not part of the main extraction LLM call
- False negative mitigation relies on the agent output filter (Layer 4) as a secondary defense
- Cross-reference: S-1-F25-03 (HMDA isolation), REQ-CC-05 (four-stage isolation), Architecture Section 2.5 (Document Processing)

---

### S-2-F5-04: Exclusion events logged to audit trail

**User Story:**

As the system,
I want to log every demographic data exclusion to the audit trail,
so that HMDA isolation compliance can be verified through audit queries.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given the demographic data filter excludes data during document extraction
When the exclusion occurs
Then an audit event is written to the audit_events table with:
  - event_type = 'system'
  - user_id = null (system operation, not user-initiated)
  - user_role = 'system'
  - application_id = the borrower's application_id
  - source_document_id = the document being processed
  - event_data = {
      "reason": "demographic_data_excluded",
      "document_id": "...",
      "excluded_fields": ["race", "ethnicity"],
      "detection_method": "keyword_match" | "semantic_similarity"
    }
  And the event is append-only per REQ-CC-09
```

**Query for Exclusion Events:**

```gherkin
Given demographic data has been excluded from multiple documents
When an auditor queries the audit trail with event_type = 'system' AND event_data->'reason' = 'demographic_data_excluded'
Then all exclusion events are returned
  And the results include document_id, application_id, and excluded_fields for each event
```

**No Exclusion, No Log:**

```gherkin
Given a document is processed and contains no demographic data
When the demographic data filter completes
Then no exclusion event is logged (nothing to report)
```

**Edge Cases:**

```gherkin
Given the demographic data filter excludes data from a document
  And the extraction pipeline subsequently fails for an unrelated reason (e.g., corrupted file)
When the audit trail is queried
Then the exclusion event is logged BEFORE the extraction failure event
  And both events reference the same document_id
```

```gherkin
Given a single document contains multiple demographic fields (race, ethnicity, sex)
When the demographic data filter excludes all of them
Then a single audit event is logged with excluded_fields = ["race", "ethnicity", "sex"]
  And not three separate events
```

**Notes:**
- Per REQ-CC-08, all system actions (including demographic data exclusions) must be logged
- Exclusion events are logged synchronously during extraction -- not deferred to a background job
- The audit event references the source_document_id for data provenance
- Cross-reference: S-2-F15-01 (audit event schema), REQ-CC-09 (append-only enforcement), Architecture Section 3.4 (Audit Trail)

---

## F6: Document Completeness and Proactive Requests

### S-2-F6-01: Agent identifies missing documents

**User Story:**

As a borrower,
I want the agent to tell me which documents I still need to provide,
so that I know what's required to complete my application.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I have an application in state 'application'
  And I have uploaded a W-2 but not a pay stub or bank statement
When I ask "What documents do I still need to provide?"
Then the agent lists the missing documents: "I still need: (1) your most recent pay stub, (2) two months of bank statements"
  And the agent explains why each is required
```

**Proactive Notification:**

```gherkin
Given I have uploaded some but not all required documents
When I say "Am I ready to submit my application?"
Then the agent checks document completeness
  And the agent responds: "Not quite yet. I still need your pay stub and bank statements. Can you upload those?"
```

**Loan-Type-Specific Requirements:**

```gherkin
Given I have a conventional loan application
When the agent checks document completeness
Then the agent requires: W-2, pay stubs, bank statements, credit report authorization
```

```gherkin
Given I have an FHA loan application
When the agent checks document completeness
Then the agent requires: W-2, pay stubs, bank statements, credit report authorization, FHA-specific disclosures
```

**Employment-Type-Specific Requirements:**

```gherkin
Given I am self-employed (employment_status = 'self_employed')
When the agent checks document completeness
Then the agent requires: 2 years of personal tax returns, 2 years of business tax returns, profit & loss statement, bank statements
```

```gherkin
Given I am a W-2 employee
When the agent checks document completeness
Then the agent requires: W-2, pay stubs, bank statements (no tax returns required)
```

**Edge Cases:**

```gherkin
Given I have uploaded all required documents for my loan type and employment status
When I ask "What documents do I still need to provide?"
Then the agent responds: "You've provided all required documents. Your application is complete!"
```

```gherkin
Given I have uploaded a document that doesn't match any standard category
When the agent checks completeness
Then the agent excludes the unrecognized document from the completeness check
  And the agent may ask: "I see you uploaded [filename]. What type of document is this?"
```

**Notes:**
- Document requirements are contextual per REQ-CC-21: loan type, employment status, property type, loan purpose (purchase vs. refinance)
- The agent uses the `document_completeness` tool to check requirements against uploaded documents
- Completeness logic is implemented in the Document Service, not hardcoded in the agent
- Cross-reference: S-2-F6-02 (proactive requests), S-2-F6-03 (freshness check), Architecture Section 2.4 (Document Service)

---

### S-2-F6-02: Agent proactively requests missing documents

**User Story:**

As a borrower,
I want the agent to proactively ask for missing documents at natural points in the conversation,
so that I don't have to remember to ask what's needed.

**Acceptance Criteria:**

**Proactive Request After Data Collection:**

```gherkin
Given I have completed the conversational data collection for my application
  And I have not yet uploaded any documents
When the agent finishes collecting application data
Then the agent says: "Great! Now I need a few documents to verify your information. Let's start with your W-2."
  And the agent provides an upload prompt
```

**Proactive Request After One Document Upload:**

```gherkin
Given I have uploaded a W-2
  And I have not uploaded a pay stub
When the agent confirms the W-2 is processed
Then the agent says: "Thanks for the W-2. Next, I need your most recent pay stub."
```

**Contextual Timing:**

```gherkin
Given I am mid-conversation about a different topic (e.g., asking about loan rates)
When the agent answers my question
Then the agent does NOT interrupt with a document request
  And waits for a natural break in the conversation before requesting documents
```

**Edge Cases:**

```gherkin
Given I have uploaded all required documents
When the agent checks completeness
Then the agent does NOT request additional documents
  And the agent confirms: "You've provided everything I need."
```

```gherkin
Given I say "I don't have my pay stub yet, I'll upload it later"
When the agent records this intent
Then the agent does NOT repeatedly nag for the pay stub
  And the agent reminds me later (e.g., when I return to the chat): "Just a reminder, I still need your pay stub when you have it."
```

**Notes:**
- Proactive requests are triggered by conversation state transitions (data collection complete, document upload complete, application submitted for review)
- The agent does not interrupt unrelated conversations to request documents
- Cross-reference: S-2-F6-01 (missing document identification), S-2-F19-01 (cross-session reminders)

---

### S-2-F6-03: Agent flags outdated documents (freshness check)

**User Story:**

As a borrower,
I want the agent to alert me if a document I uploaded is too old,
so that I can provide a more recent version before submission.

**Acceptance Criteria:**

**Freshness Check for Pay Stubs:**

```gherkin
Given I have uploaded a pay stub
  And the pay stub is dated more than 30 days ago
When the agent processes the document
Then the agent flags the document: wrong_period = true
  And the agent notifies me: "This pay stub is from [date]. I need your most recent pay stub (within the last 30 days)."
```

**Freshness Check for Bank Statements:**

```gherkin
Given I have uploaded a bank statement
  And the bank statement is dated more than 60 days ago
When the agent processes the document
Then the agent flags the document: wrong_period = true
  And the agent notifies me: "This bank statement is from [date]. I need your most recent bank statement (within the last 60 days)."
```

**Tax Returns (No Freshness Check):**

```gherkin
Given I have uploaded a tax return from 2023
  And the current year is 2026
When the agent processes the document
Then the agent does NOT flag the document for freshness (tax returns are inherently dated)
  And the agent accepts the document
```

**Edge Cases:**

```gherkin
Given I have uploaded a pay stub dated 29 days ago
When the agent processes the document
Then the agent accepts the document (within the 30-day window)
  And no freshness flag is set
```

```gherkin
Given I have uploaded a pay stub dated 31 days ago
When the agent processes the document
Then the agent flags the document: wrong_period = true
  And the agent requests a more recent pay stub
```

```gherkin
Given I have uploaded a bank statement from a future date (e.g., next month)
When the agent processes the document
Then the agent detects the date anomaly
  And the agent asks for clarification: "This bank statement appears to be dated in the future. Can you double-check the date?"
```

**Notes:**
- Freshness thresholds are document-type-specific: pay stubs (30 days), bank statements (60 days), tax returns (no freshness requirement)
- Freshness is checked during quality assessment (S-2-F5-02)
- The freshness flag is stored in the documents table as part of quality_flags
- Cross-reference: S-2-F5-02 (quality assessment), S-2-F6-01 (document requirements)

---

### S-2-F6-04: Borrower asks application status

**User Story:**

As a borrower,
I want to ask my application status,
so that I know what is happening and what I should expect next.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I am an authenticated borrower with an active application
When I ask "What is the status of my application?"
Then the agent responds with:
  - Current stage name (e.g., "Application", "Underwriting", "Conditional Approval")
  - What is happening at that stage (e.g., "Your application is being reviewed by an underwriter")
  - What I should expect next (e.g., "The underwriter may issue conditions or make a decision")
  - Estimated timeline for the next step (e.g., "Underwriting typically takes 3-5 business days")
  - Any outstanding actions required from me (e.g., "You need to upload your most recent pay stub")
```

**Error Scenarios:**

```gherkin
Given I am an authenticated borrower with no active application
When I ask "What is the status of my application?"
Then the agent responds: "You don't have an active application yet. Would you like to start a new application?"
```

**Edge Cases:**

```gherkin
Given my application is in a terminal state (denied or closed)
When I ask "What is the status of my application?"
Then the agent responds with the terminal state and the date: "Your application was [denied/closed] on [date]."
  And the agent offers to answer questions about the outcome or start a new application
```

```gherkin
Given my application has pending conditions
When I ask "What is the status of my application?"
Then the agent includes the pending conditions in the status response: "Your application is in conditional approval. You have 2 pending conditions: [list conditions]."
```

**Notes:**
- This story implements the borrower status query from product plan Flow 3.
- The agent should provide context-appropriate information based on the application's current state.
- Cross-reference: Application state machine in the hub defines all possible states.

---

### S-2-F6-05: Agent notes approaching regulatory deadlines

**User Story:**

As a borrower,
I want the agent to mention regulatory deadlines when relevant to my application timeline,
so that I understand the regulatory context for my application process.

**Acceptance Criteria:**

**Reg B 30-Day Action Requirement:**

```gherkin
Given my application is subject to Reg B's 30-day action requirement
  And I ask about my application status or timeline
When the agent responds
Then the agent includes a note: "Under federal regulations, you should receive a decision within 30 days of your application date. Your application date was [date], so a decision is expected by [date]."
  And the response includes the disclaimer: "This content is simulated for demonstration purposes and does not constitute legal or regulatory advice." (per REQ-CC-17)
```

**TRID LE Delivery Timing:**

```gherkin
Given my application is subject to TRID Loan Estimate delivery requirements
  And I ask about my application timeline
When the agent responds
Then the agent notes: "Under TRID regulations, you should receive a Loan Estimate within 3 business days of your application. Your Loan Estimate was delivered on [date]."
  And the response includes the regulatory disclaimer
```

**No Applicable Deadline:**

```gherkin
Given my application is in a stage with no immediate regulatory deadline
When I ask about the timeline
Then the agent provides operational timeline estimates (e.g., "Underwriting typically takes 3-5 business days") without mentioning regulatory deadlines
```

**Edge Cases:**

```gherkin
Given a regulatory deadline is approaching (e.g., 3 days until Reg B 30-day limit)
When I ask about my application status
Then the agent flags the approaching deadline: "Your application decision is due by [date] per federal regulations. Your loan officer is working to meet this deadline."
```

**Notes:**
- This story adds regulatory context awareness to borrower timeline queries.
- The agent should mention regulatory deadlines naturally when they are relevant to the borrower's question, not as unsolicited alerts.
- All regulatory content carries the disclaimer per REQ-CC-17.
- Cross-reference: F11 (TRID compliance checks in underwriting) for the underwriter-facing version of TRID deadline tracking.

---

## F15: Comprehensive Audit Trail

### S-2-F15-01: Audit event written for every AI action

**User Story:**

As the system,
I want to log every AI action to the audit trail,
so that all agent behavior is traceable and auditable.

**Acceptance Criteria:**

**User Query Logging:**

```gherkin
Given a borrower sends a message to the agent: "What is my application status?"
When the agent processes the query
Then an audit event is written with:
  - event_type = 'query'
  - user_id = borrower's user_id
  - user_role = 'borrower'
  - application_id = borrower's application_id
  - event_data = { "query": "What is my application status?", "response": "[agent response]" }
  - session_id = current conversation session_id
  - timestamp = server-generated timestamp
```

**Tool Call Logging:**

```gherkin
Given the agent invokes a tool (e.g., `document_status`)
When the tool executes
Then an audit event is written with:
  - event_type = 'tool_call'
  - user_id = borrower's user_id
  - user_role = 'borrower'
  - event_data = { "tool_name": "document_status", "parameters": { "document_id": "..." }, "result": { "status": "completed" } }
  - session_id = current conversation session_id
```

**Data Access Logging:**

```gherkin
Given the agent retrieves application data from the database
When the query executes
Then an audit event is written with:
  - event_type = 'data_access'
  - user_id = borrower's user_id
  - user_role = 'borrower'
  - event_data = { "operation": "read", "table": "applications", "record_id": "..." }
  - application_id = the application being accessed
```

**State Transition Logging:**

```gherkin
Given a borrower's application transitions from 'prospect' to 'application'
When the state transition occurs
Then an audit event is written with:
  - event_type = 'state_transition'
  - user_id = borrower's user_id
  - user_role = 'borrower'
  - application_id = the application
  - event_data = { "from_state": "prospect", "to_state": "application", "reason": "borrower initiated formal application" }
```

**Security Event Logging:**

```gherkin
Given the agent input filter detects a prompt injection attempt
When the input is rejected
Then an audit event is written with:
  - event_type = 'security_event'
  - user_id = borrower's user_id
  - user_role = 'borrower'
  - event_data = { "reason": "prompt_injection_detected", "pattern": "[pattern description]", "input": "[sanitized input]" }
```

**Edge Cases:**

```gherkin
Given a borrower sends multiple messages in rapid succession
When the agent processes each message
Then a separate audit event is written for each query
  And events are ordered by timestamp
```

```gherkin
Given the agent performs a tool call that fails (e.g., database timeout)
When the tool call fails
Then an audit event is still written with:
  - event_type = 'tool_call'
  - event_data including "error": "[error description]"
```

**Notes:**
- Per REQ-CC-08, ALL AI actions must be logged
- Audit events are written synchronously (not deferred) to ensure completeness
- Sensitive data (SSN, account numbers) is masked in event_data before logging
- Cross-reference: REQ-CC-08 (audit completeness), REQ-CC-10 (audit event schema), Architecture Section 3.4 (Audit Trail)

---

### S-2-F15-02: Audit events are append-only (no UPDATE/DELETE grants)

**User Story:**

As the system,
I want to enforce append-only semantics on the audit trail at the database level,
so that audit events cannot be modified or deleted after creation.

**Acceptance Criteria:**

**Database Role Grants:**

```gherkin
Given the FastAPI application connects to PostgreSQL with the `lending_app` role
When the role's grants are inspected
Then the `lending_app` role has INSERT and SELECT grants on the audit_events table
  And the `lending_app` role has NO UPDATE or DELETE grants on audit_events
```

```gherkin
Given the Compliance Service connects to PostgreSQL with the `compliance_app` role
When the role's grants are inspected
Then the `compliance_app` role has INSERT and SELECT grants on audit_events
  And the `compliance_app` role has NO UPDATE or DELETE grants on audit_events
```

**Application-Level Enforcement:**

```gherkin
Given the application code attempts to update an existing audit event
When the UPDATE statement executes
Then the database returns a permission denied error
  And the application logs the error
  And no audit event is modified
```

```gherkin
Given the application code attempts to delete an audit event
When the DELETE statement executes
Then the database returns a permission denied error
  And the application logs the error
  And no audit event is deleted
```

**Edge Cases:**

```gherkin
Given an administrator connects to PostgreSQL with the `postgres` superuser role
When the administrator attempts to modify or delete an audit event
Then the database trigger (S-2-F15-03) rejects the operation
  And the attempt is logged to the audit_violations table
```

**Notes:**
- Per REQ-CC-09, append-only semantics are enforced at the database level (not just application-level validation)
- The database role grants are defined in the Alembic migration that creates the audit_events table
- Cross-reference: S-2-F15-03 (trigger enforcement), REQ-CC-09 (immutability), Architecture Section 3.4 (Audit Trail)

---

### S-2-F15-03: Database trigger rejects UPDATE/DELETE on audit_events

**User Story:**

As the system,
I want a database trigger to reject any UPDATE or DELETE attempt on the audit_events table,
so that even superuser actions cannot modify the audit trail.

**Acceptance Criteria:**

**Trigger Behavior:**

```gherkin
Given a database user attempts to UPDATE an audit event record
When the UPDATE statement executes
Then a database trigger fires BEFORE the update
  And the trigger rejects the operation with an error: "Audit events are immutable"
  And the trigger logs the attempt to the audit_violations table with:
    - timestamp
    - attempted_operation = 'UPDATE'
    - user = database session user
    - audit_event_id = the event ID that was targeted
```

```gherkin
Given a database user attempts to DELETE an audit event record
When the DELETE statement executes
Then a database trigger fires BEFORE the delete
  And the trigger rejects the operation with an error: "Audit events are immutable"
  And the trigger logs the attempt to the audit_violations table
```

**Violation Logging:**

```gherkin
Given multiple violation attempts occur
When the audit_violations table is queried
Then all violation attempts are recorded
  And each record includes timestamp, operation, user, and targeted audit_event_id
```

**Edge Cases:**

```gherkin
Given a database user attempts a batch UPDATE (UPDATE audit_events SET ... WHERE ...)
When the trigger fires
Then the trigger rejects the entire batch
  And a single violation is logged (not one per row)
```

```gherkin
Given a database user attempts to DROP the audit_events table
When the DROP statement executes
Then the database rejects the operation based on table ownership and grants (not the trigger)
  And the rejection is logged to PostgreSQL logs
```

**Notes:**
- The trigger is defined in the Alembic migration that creates the audit_events table
- The trigger fires BEFORE the operation to prevent any data modification
- Violations are logged to a separate audit_violations table to preserve evidence of tampering attempts
- Cross-reference: S-2-F15-02 (role grants), REQ-CC-09 (immutability), Architecture Section 3.4 (Audit Trail)

---

### S-2-F15-04: Hash chain provides tamper evidence

**User Story:**

As the system,
I want each audit event to include a hash of the previous event,
so that any tampering with the audit trail is detectable.

**Acceptance Criteria:**

**Hash Chain Computation:**

```gherkin
Given a new audit event is being inserted
When the event is written to the database
Then the system computes prev_hash as:
  - hash = SHA-256(previous_event.id + previous_event.timestamp + previous_event.event_data)
  And the prev_hash is stored in the new event record
```

```gherkin
Given the first audit event in the table (id = 1)
When the event is written
Then prev_hash is set to a sentinel value (e.g., "genesis" or null)
  And subsequent events link back to this first event
```

**Tamper Detection:**

```gherkin
Given an audit trail with 100 events
When an attacker modifies event #50 (changes event_data)
Then the hash chain breaks at event #51
  And event #51's prev_hash no longer matches the recomputed hash of event #50
  And a verification query detects the break: "SELECT * FROM audit_events WHERE id = 51 AND prev_hash != compute_hash(event_50)"
```

**Verification Query:**

```gherkin
Given an auditor wants to verify audit trail integrity
When the auditor runs a verification query that recomputes all hashes
Then the query returns:
  - "OK" if all prev_hash values match recomputed hashes
  - "TAMPERED" with the first mismatched event ID if the chain is broken
```

**Edge Cases:**

```gherkin
Given two audit events are inserted in rapid succession
When both events attempt to compute prev_hash concurrently
Then the advisory lock (S-2-F15-05) ensures serial computation
  And the hash chain remains unbroken
```

```gherkin
Given the audit_events table is empty
When the first event is inserted
Then prev_hash is set to "genesis"
  And the hash chain begins
```

**Notes:**
- Hash chain is a PoC-level tamper evidence mechanism per architecture Section 3.4
- Production would replace with cryptographic verification or external ledger
- Hash computation uses SHA-256 for consistency and reproducibility
- The hash chain does NOT prevent deletion (gaps in the sequence are detectable but not preventable by the hash chain alone)
- Cross-reference: S-2-F15-05 (advisory lock for serial computation), Architecture Section 3.4 (Audit Trail)

---

### S-2-F15-05: Advisory lock ensures serial hash chain computation

**User Story:**

As the system,
I want to use a PostgreSQL advisory lock around audit event inserts,
so that the hash chain is computed serially even under concurrent load.

**Acceptance Criteria:**

**Advisory Lock Usage:**

```gherkin
Given two concurrent transactions attempt to insert audit events
When both transactions reach the audit insert operation
Then the first transaction acquires the advisory lock (pg_advisory_lock)
  And the second transaction blocks until the first transaction commits
  And the hash chain is computed serially (no race condition)
```

```gherkin
Given a transaction acquires the advisory lock
When the transaction inserts an audit event
  And computes the prev_hash based on the most recent event
  And commits the transaction
Then the advisory lock is released
  And the next waiting transaction can proceed
```

**Lock Scope:**

```gherkin
Given the advisory lock is scoped to audit event inserts only
When other database operations occur (e.g., application data inserts)
Then those operations are NOT blocked by the advisory lock
  And only audit event inserts are serialized
```

**Edge Cases:**

```gherkin
Given a transaction acquires the advisory lock
  And the transaction crashes before committing
When the database session terminates
Then the advisory lock is automatically released
  And the next transaction can proceed
```

```gherkin
Given the audit trail is under high write load (100+ events per second)
When the advisory lock serializes all inserts
Then the lock contention may become a bottleneck
  And at PoC scale (small number of concurrent users), this is acceptable
```

**Notes:**
- Advisory lock is PostgreSQL-specific: `pg_advisory_lock(hash_key)` where hash_key is a unique identifier for the audit trail
- The lock is acquired within the transaction that inserts the audit event
- The lock is released automatically when the transaction commits or rolls back
- At PoC scale, advisory lock contention is negligible. Production would replace the hash chain entirely (not incrementally upgrade it).
- Cross-reference: S-2-F15-04 (hash chain), Architecture Section 3.4 (Audit Trail), REQ-A-03 (PoC-level hash chain assumption)

---

### S-2-F15-06: Borrower acknowledges disclosures during application

**User Story:**

As a borrower,
I want to acknowledge receipt of required disclosures during the application process,
so that the lender has a record of my consent and compliance is maintained.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I am completing my mortgage application
When the agent presents a required disclosure (Loan Estimate, privacy notice, HMDA notice, equal opportunity notice)
Then the agent explains the disclosure briefly
  And the agent asks me to acknowledge: "I have received and reviewed the [disclosure name]."
  And I respond with acknowledgment (e.g., "yes", "I acknowledge", "I agree")
  And the agent records the acknowledgment in the audit trail with:
    - event_type = 'disclosure_acknowledged'
    - disclosure_identifier (e.g., "loan_estimate", "privacy_notice")
    - timestamp
    - borrower confirmation text
```

**Multiple Disclosures:**

```gherkin
Given my application requires multiple disclosures (LE, privacy notice, HMDA notice, ECOA notice)
When the agent presents the disclosures
Then each disclosure requires a separate acknowledgment
  And the agent tracks which disclosures have been acknowledged and which are pending
  And each acknowledgment is logged as a separate audit event
```

**Disclosure Refusal:**

```gherkin
Given the agent presents a required disclosure
When I refuse to acknowledge (e.g., "I don't agree", "I need to read this first")
Then the agent notes the refusal: "No problem. Take your time to review. Let me know when you're ready to acknowledge."
  And the application remains in progress but the disclosure acknowledgment is marked as pending
  And no acknowledgment audit event is logged until I provide acknowledgment
```

**Edge Cases:**

```gherkin
Given I acknowledge a disclosure
  And I later ask "What disclosures have I acknowledged?"
When the agent queries the audit trail
Then the agent lists all acknowledged disclosures with their timestamps
```

```gherkin
Given the agent presents the Loan Estimate disclosure
When I acknowledge receipt
Then the audit event includes the LE delivery date per TRID requirements
  And this event can be referenced during F11 TRID compliance checks in underwriting
```

**Notes:**
- This story operationalizes disclosure delivery and consent tracking required by TRID, ECOA, and privacy regulations.
- Each disclosure is a separate audit event for compliance traceability.
- Cross-reference: Product plan Flow 2 step 8 (borrower acknowledges disclosures during intake).
- Cross-reference: F11 (TRID compliance checks reference LE delivery date from audit trail).

---

## F19: Cross-Session Conversation Memory

### S-2-F19-01: Borrower conversation persists across sessions

**User Story:**

As a borrower,
I want my conversation with the agent to resume where I left off,
so that I don't have to repeat information when I return.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I am an authenticated borrower
  And I had a conversation with the agent yesterday
  And I closed the chat session
When I open the chat interface today
Then the agent greets me: "Welcome back! Last time we were discussing your W-2 upload."
  And the agent has access to the full conversation history
  And I can continue the conversation without repeating prior information
```

**Conversation State Recovery:**

```gherkin
Given I provided my annual income in a previous session
  And I closed the chat before uploading documents
When I return to the chat
  And I say "I'm ready to upload my W-2"
Then the agent remembers my income: "Great! I already have your annual income ($75,000). Let's upload your W-2 now."
```

**Multi-Device Continuity:**

```gherkin
Given I had a conversation on my laptop
When I open the chat on my phone (same authenticated user)
Then the agent resumes the conversation from where it left off
  And the conversation history is consistent across devices
```

**Edge Cases:**

```gherkin
Given I am a new borrower with no prior conversation
When I open the chat for the first time
Then the agent greets me: "Welcome! I'm here to help you apply for a mortgage."
  And no prior conversation history is referenced
```

```gherkin
Given I had a conversation 6 months ago
  And I return to the chat today
When the agent greets me
Then the agent acknowledges the time gap: "Welcome back! It's been a while since we last spoke."
  And the agent offers to review the prior conversation or start fresh
```

**Notes:**
- Conversation persistence is implemented via LangGraph checkpoints stored in PostgreSQL per architecture Section 3.5
- Checkpoints are user-scoped (S-2-F19-02)
- Cross-reference: Architecture Section 3.5 (Conversation Persistence), S-2-F19-02 (user_id filtering)

---

### S-2-F19-02: Conversation checkpoints filtered by user_id

**User Story:**

As the system,
I want to filter conversation checkpoints by user_id,
so that each user sees only their own conversation history.

**Acceptance Criteria:**

**Query Filtering:**

```gherkin
Given a borrower (user_id = 'user-123') requests their conversation history
When the system queries the conversation_checkpoints table
Then the query includes WHERE user_id = 'user-123'
  And the query returns only checkpoints for user-123
  And no other user's checkpoints are returned
```

**Parameterized Queries:**

```gherkin
Given the conversation service retrieves checkpoints
When the query is constructed
Then the user_id is passed as a parameterized query parameter (not string interpolation)
  And the query is safe from SQL injection
```

**No Cross-User Access:**

```gherkin
Given a borrower (user_id = 'user-123') is authenticated
When the system retrieves conversation checkpoints
Then the system never retrieves checkpoints for user_id = 'user-456'
  And there is no query path that returns checkpoints across users
```

**Edge Cases:**

```gherkin
Given an administrator (role = 'admin') is authenticated
When the administrator attempts to access another user's conversation checkpoints
Then the query still filters by user_id (admin user_id, not the target user)
  And the admin sees their own conversation, not the target user's conversation
  And there is NO admin override for conversation checkpoints per architecture Section 3.5
```

```gherkin
Given a borrower has no prior checkpoints (first-time user)
When the system queries conversation_checkpoints
Then the query returns zero rows
  And the system initializes a new checkpoint
```

**Notes:**
- Per architecture Section 3.5, checkpoints include user_id as a mandatory column
- All checkpoint queries use parameterized queries for user_id
- There is no admin or CEO override for conversation checkpoints -- even admins can only see their own conversations
- Cross-reference: S-2-F19-03 (post-retrieval verification), S-2-F19-04 (no cross-user access), Architecture Section 3.5

---

### S-2-F19-03: Post-retrieval verification of checkpoint user_id

**User Story:**

As the system,
I want to verify the user_id of a retrieved checkpoint after retrieval,
so that any ORM misconfiguration or query builder error is caught before data is used.

**Acceptance Criteria:**

**Post-Retrieval Check:**

```gherkin
Given a checkpoint is retrieved from the database
When the Conversation Service receives the checkpoint object
Then the service verifies: checkpoint.user_id == requesting_user_id
  And if the verification fails, the service raises an exception
  And the checkpoint is NOT used
  And an audit event is logged with event_type = 'security_event' and reason = 'checkpoint_user_mismatch'
```

**ORM Misconfiguration Detection:**

```gherkin
Given an ORM misconfiguration causes a checkpoint for user-456 to be returned
  And the requesting user is user-123
When the post-retrieval verification executes
Then the verification detects the mismatch (checkpoint.user_id = 'user-456', requesting_user_id = 'user-123')
  And the service raises an exception
  And the checkpoint is discarded
  And an alert is logged for operator investigation
```

**Happy Path (No Mismatch):**

```gherkin
Given a checkpoint is retrieved for user-123
  And the requesting user is user-123
When the post-retrieval verification executes
Then the verification passes
  And the checkpoint is used to resume the conversation
```

**Edge Cases:**

```gherkin
Given the checkpoint table is corrupted and returns a checkpoint with user_id = null
  And the requesting user is user-123
When the post-retrieval verification executes
Then the verification fails (null != 'user-123')
  And the service raises an exception
  And the checkpoint is discarded
```

**Notes:**
- Post-retrieval verification is defense-in-depth per architecture Section 3.5
- This check catches ORM misconfiguration, query builder errors, and database-level issues
- The verification is a simple assertion: `assert checkpoint.user_id == requesting_user_id`
- Cross-reference: S-2-F19-02 (query filtering), Architecture Section 3.5 (Defense-in-depth)

---

### S-2-F19-04: No cross-user checkpoint access (including CEO/admin)

**User Story:**

As the system,
I want to enforce strict user isolation for conversation checkpoints,
so that even admin and CEO roles cannot access other users' conversation history.

**Acceptance Criteria:**

**CEO Role Restriction:**

```gherkin
Given a CEO (role = 'ceo', user_id = 'ceo-789') is authenticated
When the CEO attempts to access a borrower's conversation history
Then the system rejects the request
  And the CEO sees their own conversation history only
  And there is no API endpoint or tool that allows the CEO to access another user's checkpoints
```

**Admin Role Restriction:**

```gherkin
Given an admin (role = 'admin', user_id = 'admin-999') is authenticated
When the admin attempts to access a borrower's conversation history
Then the system rejects the request
  And the admin sees their own conversation history only
```

**No Query Path for Cross-User Access:**

```gherkin
Given the Conversation Service API is inspected
When all API methods are reviewed
Then there is no method signature that accepts a target_user_id parameter
  And all methods retrieve checkpoints for the authenticated user only
```

**Audit Trail Access (CEO):**

```gherkin
Given a CEO wants to understand a borrower's interaction history
When the CEO queries the audit trail (F13)
Then the CEO sees audit events for the borrower (queries, tool calls, data access)
  And the CEO sees WHAT happened, but not the full conversational context
  And the audit trail is separate from conversation checkpoints
```

**Edge Cases:**

```gherkin
Given a borrower's conversation includes sensitive data (e.g., financial details)
When the borrower closes the session
Then the checkpoint is stored with user_id = borrower's user_id
  And no other user (including CEO) can retrieve this checkpoint
```

**Notes:**
- Per architecture Section 3.5, conversation memory is strictly user-scoped with no admin override
- The CEO can see audit events (what happened) but not the full conversational context (how the conversation flowed)
- This is stricter than typical admin access models, reflecting the sensitivity of financial conversations
- Cross-reference: S-2-F19-02 (query filtering), S-5-F13-01 (CEO audit trail access), Architecture Section 3.5

---

## F27: Rate Lock and Closing Date Tracking

### S-2-F27-01: Borrower views current rate lock status

**User Story:**

As a borrower,
I want to see my current rate lock status,
so that I know if my interest rate is locked and when it expires.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I have a rate lock on my application
  And the rate lock is active (not expired)
When I ask "What is my rate lock status?"
Then the agent responds with:
  - rate_lock_status = 'active'
  - locked_rate (e.g., 6.5%)
  - lock_expiration_date (e.g., "March 15, 2026")
  - days_remaining (e.g., "14 days remaining")
```

**No Rate Lock:**

```gherkin
Given I do not have a rate lock on my application
When I ask "What is my rate lock status?"
Then the agent responds: "You don't have a rate lock yet. Would you like me to explain how rate locks work?"
```

**Expired Rate Lock:**

```gherkin
Given I had a rate lock that expired yesterday
When I ask "What is my rate lock status?"
Then the agent responds: "Your rate lock expired on [date]. You'll need to request a new rate lock. The current rate is [current rate]."
```

**Edge Cases:**

```gherkin
Given my rate lock expires in 2 days
When I ask "What is my rate lock status?"
Then the agent highlights the urgency: "Your rate lock expires in 2 days (March 15, 2026). Please coordinate with your loan officer to close soon."
```

```gherkin
Given my application is in state 'prospect' (no formal application yet)
When I ask "What is my rate lock status?"
Then the agent responds: "You don't have a formal application yet, so there's no rate lock. Would you like to start an application?"
```

**Notes:**
- Rate lock data is stored as first-class application data per architecture Section 3.2
- The rate_locks table includes: application_id, locked_rate, lock_date, expiration_date, status
- Cross-reference: S-2-F27-03 (expiration alerts), S-3-F7-03 (LO urgency indicators), Architecture Section 3.2

---

### S-2-F27-02: Rate lock data stored as first-class application data

**User Story:**

As the system,
I want to store rate lock data as first-class application data,
so that rate locks are queryable and traceable like other application attributes.

**Acceptance Criteria:**

**Data Model:**

```gherkin
Given a loan officer locks a rate for an application
When the rate lock is created
Then a record is inserted into the rate_locks table with:
  - rate_lock_id (UUID)
  - application_id (UUID, foreign key to applications)
  - locked_rate (decimal, e.g., 6.500)
  - lock_date (date, when the lock was created)
  - expiration_date (date, when the lock expires)
  - lock_duration_days (integer, e.g., 30, 45, 60)
  - status (text: 'active', 'expired', 'extended', 'voided')
  - created_by (UUID, user_id of the loan officer)
```

**Queryability:**

```gherkin
Given multiple applications have rate locks
When a loan officer queries applications by rate lock expiration
Then the query can filter: SELECT * FROM applications JOIN rate_locks ON applications.id = rate_locks.application_id WHERE rate_locks.expiration_date < NOW() + INTERVAL '7 days'
  And the results include all applications with rate locks expiring in the next 7 days
```

**Audit Trail Integration:**

```gherkin
Given a rate lock is created
When the rate lock record is inserted
Then an audit event is logged with:
  - event_type = 'data_access'
  - event_data = { "operation": "create", "table": "rate_locks", "record_id": "...", "locked_rate": "6.5", "expiration_date": "..." }
  - user_id = loan officer's user_id
```

**Edge Cases:**

```gherkin
Given a rate lock expires
When the expiration_date is reached
Then the status is updated to 'expired'
  And the agent alerts the borrower (S-2-F27-03)
```

```gherkin
Given a loan officer extends a rate lock
When the extension is applied
Then a new rate_locks record is created (or the existing record is updated with a new expiration_date)
  And an audit event is logged showing the extension
```

**Notes:**
- Rate locks are NOT stored in a generic JSONB field -- they are first-class schema entities
- This supports querying, reporting, and urgency calculations
- Cross-reference: S-3-F7-03 (LO urgency based on rate lock), Architecture Section 3.2 (application domain schema)

---

### S-2-F27-03: Agent alerts borrower when rate lock nears expiration

**User Story:**

As a borrower,
I want to be alerted when my rate lock is nearing expiration,
so that I can take action to close on time or extend the lock.

**Acceptance Criteria:**

**Proactive Alert (7 Days Before Expiration):**

```gherkin
Given my rate lock expires in 7 days
When I open the chat interface
Then the agent proactively alerts me: "Your rate lock expires in 7 days (March 15, 2026). Please work with your loan officer to close soon."
```

**Escalation Alert (3 Days Before Expiration):**

```gherkin
Given my rate lock expires in 3 days
When I open the chat interface
Then the agent escalates the alert: "Urgent: Your rate lock expires in 3 days. You need to close by March 15, or you may need to re-lock at a different rate."
```

**No Alert (More Than 7 Days Remaining):**

```gherkin
Given my rate lock expires in 20 days
When I open the chat interface
Then the agent does NOT proactively alert me about the rate lock
  And I can still ask for the status manually
```

**Alert in Response to Unrelated Query:**

```gherkin
Given my rate lock expires in 3 days
  And I ask "What is my application status?"
When the agent responds
Then the agent includes the rate lock alert: "Your application is in underwriting. By the way, your rate lock expires in 3 days."
```

**Edge Cases:**

```gherkin
Given my rate lock expires today
When I open the chat interface
Then the agent alerts: "Your rate lock expires today! Contact your loan officer immediately."
```

```gherkin
Given my rate lock expired yesterday
When I open the chat interface
Then the agent alerts: "Your rate lock expired yesterday. You'll need to request a new rate lock."
```

**Notes:**
- Alert thresholds: 7 days (initial alert), 3 days (escalation), 0 days (critical)
- Alerts are delivered proactively when the borrower opens the chat or during natural conversation pauses
- Alerts are NOT sent via email/SMS at PoC maturity (just in-chat notifications)
- Cross-reference: S-2-F27-01 (rate lock status), REQ-OQ-02 (threshold confirmation from stakeholder)

---

## F28: Borrower Condition Response

### S-2-F28-01: Borrower responds to underwriting conditions via chat

**User Story:**

As a borrower,
I want to respond to underwriting conditions through the chat interface,
so that I can address issues naturally without navigating a separate form.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given an underwriter has issued conditions on my application
  And I open the chat interface
When the agent greets me
Then the agent notifies me of the pending conditions: "You have 2 conditions from the underwriter: (1) provide an explanation for the large deposit on your bank statement, (2) upload a signed copy of your employment verification letter."
  And the agent asks: "Would you like to address these now?"
```

```gherkin
Given the agent has notified me of a condition
When I respond: "The large deposit was a gift from my parents for the down payment"
Then the agent records my response
  And the agent stores the response in the conditions table linked to the condition_id
  And the agent confirms: "Got it. I've recorded your explanation. I still need the signed employment verification letter."
```

**Conversational Clarification:**

```gherkin
Given the agent asks me to address a condition
When I say "I'm not sure what you mean by large deposit"
Then the agent provides clarification: "The underwriter flagged a $15,000 deposit on your bank statement from January 10. Can you explain where that came from?"
```

**Partial Response:**

```gherkin
Given I have 2 pending conditions
When I respond to condition #1 but not condition #2
Then the agent records my response for condition #1
  And the agent reminds me of condition #2: "Thanks! Now, about the signed employment verification letter..."
```

**Edge Cases:**

```gherkin
Given I have no pending conditions
When I ask "Do I have any conditions to address?"
Then the agent responds: "No, you don't have any pending conditions right now."
```

```gherkin
Given a condition requires a document upload (e.g., "upload signed letter")
When I respond with text instead of uploading a document
Then the agent clarifies: "I need you to upload the signed letter. Can you upload it here?"
  And the agent provides an upload prompt
```

**Notes:**
- Conditions are stored in the conditions table with lifecycle states (issued, responded, cleared, waived) per architecture Section 3.2
- Borrower responses are recorded as text in a conditions_responses table or as updates to the conditions record
- Cross-reference: S-2-F28-02 (document upload for conditions), S-4-F16-04 (underwriter clears conditions), Architecture Section 3.2

---

### S-2-F28-02: Borrower uploads documents to satisfy conditions

**User Story:**

As a borrower,
I want to upload documents to satisfy underwriting conditions,
so that I can provide the required documentation to move my application forward.

**Acceptance Criteria:**

**Happy Path:**

```gherkin
Given I have a condition: "Upload signed employment verification letter"
When I upload the document through the chat interface
Then the agent confirms: "I've received your employment verification letter. Processing it now."
  And the document is linked to the condition_id in the documents table
  And the condition status is updated to 'responded'
```

**Document Processing for Conditions:**

```gherkin
Given I have uploaded a document to satisfy a condition
When the document processing completes
Then the agent reviews the extraction result
  And the agent checks if the document satisfies the condition (e.g., is the letter signed?)
  And if satisfied, the agent notifies me: "The document looks good. The underwriter will review it."
  And if NOT satisfied, the agent requests a correction: "The letter doesn't appear to be signed. Can you upload a signed version?"
```

**Multiple Documents for One Condition:**

```gherkin
Given I have a condition: "Provide two months of bank statements"
When I upload two bank statement files
Then the agent links both documents to the same condition_id
  And the agent confirms: "I've received both bank statements. Processing them now."
```

**Edge Cases:**

```gherkin
Given I upload a document without specifying which condition it's for
  And I have multiple pending conditions
When the agent receives the document
Then the agent asks: "Which condition is this document for? (1) explanation for large deposit, (2) employment verification letter"
  And I clarify which condition
  And the agent links the document to the correct condition
```

```gherkin
Given I upload a document to satisfy a condition
  And the document is flagged with quality issues (e.g., blurry, unsigned)
When the agent reviews the quality flags
Then the agent notifies me of the issue: "The document is a bit blurry. Can you upload a clearer version?"
  And the condition remains in 'responded' status (not 'cleared') until a satisfactory document is provided
```

**Notes:**
- Documents uploaded for conditions are linked via a condition_id foreign key in the documents table
- The agent uses the same document processing pipeline as initial application documents (extraction, quality assessment)
- Cross-reference: S-2-F4-01 (document upload), S-2-F5-02 (quality assessment), S-4-F16-04 (underwriter clears conditions)

---

### S-2-F28-03: Agent confirms condition satisfaction or requests clarification

**User Story:**

As a borrower,
I want the agent to confirm when I've satisfied a condition,
so that I know my response was adequate.

**Acceptance Criteria:**

**Condition Satisfied:**

```gherkin
Given I have responded to a condition with a text explanation
  And the agent determines the response is sufficient
When the agent reviews my response
Then the agent confirms: "Thanks! Your explanation is clear. The underwriter will review it."
  And the condition status is updated to 'responded'
  And an audit event is logged showing the borrower response
```

**Condition Requires Clarification:**

```gherkin
Given I have responded to a condition with an incomplete explanation
When the agent reviews my response
Then the agent requests clarification: "Can you provide more detail about where the $15,000 came from? For example, was it a gift, a loan, or from the sale of an asset?"
  And the condition remains in 'responded' status until I provide additional detail
```

**Document-Based Condition:**

```gherkin
Given I have uploaded a document to satisfy a condition
  And the document extraction shows the document is signed
When the agent reviews the extraction result
Then the agent confirms: "The document looks good. The underwriter will review it."
  And the condition status is updated to 'responded'
```

```gherkin
Given I have uploaded a document to satisfy a condition
  And the document extraction shows the document is NOT signed
When the agent reviews the extraction result
Then the agent requests a correction: "The letter doesn't appear to be signed. Can you upload a signed version?"
  And the condition remains in 'responded' status until a satisfactory document is provided
```

**Edge Cases:**

```gherkin
Given I have responded to all pending conditions
When the agent confirms the last condition
Then the agent says: "Great! You've addressed all the conditions. The underwriter will review your responses and let you know if anything else is needed."
  And I can continue the conversation or close the session
```

```gherkin
Given the agent detects that my response doesn't actually address the condition
When the agent reviews my response
Then the agent explains what's needed: "I see you uploaded a pay stub, but the condition is asking for an employment verification letter. Can you provide that instead?"
```

**Notes:**
- The agent uses extraction results and pattern matching to assess condition satisfaction
- Final clearance of conditions happens at the underwriter level (S-4-F16-04), not the agent level
- The agent's role is to collect and validate responses, not to approve conditions
- Cross-reference: S-2-F28-01 (conversational response), S-2-F28-02 (document upload), S-4-F16-04 (underwriter clears conditions)

---

## Coverage Summary

This chunk covers 33 stories:
- F3: 5 stories (S-2-F3-01 through S-2-F3-05)
- F4: 4 stories (S-2-F4-01 through S-2-F4-04)
- F5: 4 stories (S-2-F5-01 through S-2-F5-04)
- F6: 5 stories (S-2-F6-01 through S-2-F6-05)
- F15: 6 stories (S-2-F15-01 through S-2-F15-06)
- F19: 4 stories (S-2-F19-01 through S-2-F19-04)
- F27: 3 stories (S-2-F27-01 through S-2-F27-03)
- F28: 3 stories (S-2-F28-01 through S-2-F28-03)

All stories include:
- User story in As a / I want / So that format
- Happy path Given/When/Then acceptance criteria
- Error/failure scenarios
- Edge cases and boundary conditions
- Notes with cross-references and architectural context

Cross-cutting requirements (REQ-CC-01 through REQ-CC-22) are referenced but not duplicated.

---

**End of Chunk 2: Borrower Experience**
