# Requirements Chunk 5: Executive Experience and Deployment

## Overview

This chunk covers **Phase 4a Executive persona features** and **Phase 4b container platform deployment features**:

- **F12:** CEO Executive Dashboard (visual dashboard with pipeline metrics, fairness analysis, LO performance)
- **F13:** CEO Conversational Analytics (drill-down on dashboard data)
- **F15:** Audit Trail Export Capability (export audit data for external analysis)
- **F23:** Container Platform Deployment (Helm charts for OpenShift/Kubernetes)
- **F39:** Model Monitoring Overlay (lightweight inference health metrics)

**Cross-references to master document:**
- Story IDs: S-5-F12-01 through S-5-F39-05 (25 stories total)
- Cross-cutting concerns: REQ-CC-01 through REQ-CC-22 (see master document)
- State machine: Applications transition through states from Prospect to Closed/Denied/Withdrawn (see master document)

**Key dependencies:**
- **F12, F13, F39** depend on F17 (decisions exist to aggregate), F25 (HMDA aggregates for fair lending), F38 (TrustyAI fairness metrics), and F18 (LangFuse metrics for monitoring overlay)
- **F23** depends on F22 (Compose services as the architecture to translate into Kubernetes)
- **F13** consumes F15 audit trail data with partial PII masking consistent with F12
- **F15** (audit export capability) complements the audit trail query features in F13

---

## Feature 12: CEO Executive Dashboard

The CEO Executive Dashboard is a **visual dashboard** (not conversational-only) displaying business intelligence across six metric categories. This is the CEO's primary interface for monitoring portfolio health, operational efficiency, and compliance risk. The dashboard uses **partial PII masking** — borrower names are visible, but SSN, DOB, and account numbers are masked before data reaches the frontend.

### S-5-F12-01: CEO views pipeline summary (volume, stages, turn times)

**User Story:**
As a CEO,
I want to view a pipeline summary showing volume, stage distribution, and turn times by stage,
so that I understand the operational health of our lending portfolio.

**Acceptance Criteria:**

**Given** the CEO is authenticated and has applications in the system across multiple stages

**When** the CEO navigates to the executive dashboard

**Then** the dashboard displays a pipeline summary panel containing:
- Total application count
- Applications by stage (Prospect, Application, Underwriting, Conditional Approval, Final Approval, Closing, Closed)
- Pull-through rate (percentage of applications that reach Closed stage)
- Average turn time from Application to Underwriting submission
- Average turn time from Underwriting to Conditional Approval
- Average turn time from Conditional Approval to Final Approval
- Average turn time from Final Approval to Closing
- Average turn time from Underwriting to Conditions Clearing (time spent satisfying conditions)
- Overall average application-to-close time

**And** turn times are calculated as average days in each stage across all applications that have passed through that stage in the selected time period (default: last 90 days)

**And** pull-through rate is calculated as (Closed applications) / (Total applications initiated) over the time period

**And** stage distribution is displayed as a horizontal bar chart or funnel visualization

---

**Given** the CEO has selected a time range filter (30/60/90/180 days or custom date range)

**When** the dashboard reloads metrics

**Then** all metrics recalculate for the selected time range

**And** the time range selection is displayed prominently in the dashboard header

---

**Given** there are no applications in the system

**When** the CEO views the dashboard

**Then** the pipeline summary displays zero values for all metrics

**And** a message states "No applications in this time period"

---

**Given** an application has incomplete stage data (e.g., submitted to underwriting but no subsequent state transition)

**When** calculating stage-specific turn times

**Then** the incomplete application is excluded from turn time calculations for stages it has not completed

**And** the incomplete application is included in the stage distribution count for its current stage

---

**Notes:**
- The Analytics Service composes this data by querying the Application Service's state transition history.
- "Pull-through rate" is defined at the portfolio level (not LO-specific) in this story. S-5-F12-04 covers LO-specific metrics.
- Turn times are measured **by stage** (not just overall), as turn time bottlenecks often occur in specific stages (e.g., conditions clearing).

---

### S-5-F12-02: CEO views denial rate trends over time

**User Story:**
As a CEO,
I want to view denial rate trends with top denial reasons,
so that I can identify adverse action patterns and product fit issues.

**Acceptance Criteria:**

**Given** the CEO is authenticated and the system has decision history with denials

**When** the CEO views the denial rate section of the dashboard

**Then** the dashboard displays:
- Overall denial rate (percentage of applications reaching Underwriting that result in Denied status)
- Denial rate trend over time (line chart, monthly granularity for 90-day view, weekly for 30-day view)
- Top 5 denial reasons with count and percentage
- Denial rate by product type (Conventional, FHA, VA, USDA, Jumbo, Renovation) if multiple products exist

**And** denial reasons are extracted from the `decision.rationale` field in underwriting decisions

**And** if a decision includes multiple reasons, each reason is counted separately in the "top reasons" distribution

---

**Given** a denial reason appears in fewer than 3 decisions in the time period

**When** calculating top denial reasons

**Then** that reason is aggregated into an "Other" category to avoid revealing individual application details

---

**Given** there are no denials in the selected time period

**When** the CEO views the denial rate section

**Then** the dashboard displays "Denial rate: 0%" with a message "No denials in this time period"

**And** the top denial reasons chart is not displayed

---

**Given** the CEO filters denial data by product type (Conventional, FHA, VA, etc.)

**When** the dashboard recalculates denial metrics

**Then** all denial metrics (rate, trend, top reasons) are filtered to the selected product type

**And** the product type filter is displayed above the denial rate section

---

**Notes:**
- Top denial reasons must be aggregated to avoid revealing individual application details, per PII masking principles.
- The "top denial reasons" distribution should use categorical labels that reflect the business language used in underwriting (e.g., "Insufficient income", "High DTI", "Credit score below threshold").
- Cross-reference: F17 (Decisions) defines the structure of denial rationale and adverse action data.

---

### S-5-F12-03: CEO views fair lending metrics (SPD, DIR)

**User Story:**
As a CEO,
I want to view fair lending metrics including Statistical Parity Difference and Disparate Impact Ratio,
so that I can monitor for potential fair lending concerns and ensure compliance with ECOA and fair lending regulations.

**Acceptance Criteria:**

**Given** the CEO is authenticated and the system has sufficient HMDA-correlated decision data (minimum 30 decisions with HMDA demographic data)

**When** the CEO views the fair lending section of the dashboard

**Then** the dashboard displays:
- Statistical Parity Difference (SPD) for protected classes (race, ethnicity, sex)
- Disparate Impact Ratio (DIR) for protected classes
- Trend chart showing SPD/DIR over time (quarterly granularity for 12-month view)
- Color-coded indicators: green (within acceptable range), yellow (approaching concern threshold), red (exceeds concern threshold)
- A regulatory disclaimer: "These metrics are computed on aggregate data for internal monitoring. This content is simulated for demonstration purposes and does not constitute legal or regulatory advice."

**And** SPD and DIR are computed using the `trustyai` Python library within the Compliance Service

**And** SPD and DIR are computed only on **pre-aggregated HMDA-correlated lending outcomes** — individual HMDA records are never exposed through any API

**And** thresholds for concern indicators are configurable (default: SPD > 0.1 = yellow, SPD > 0.2 = red; DIR < 0.8 = red, DIR < 0.9 = yellow)

---

**Given** the Compliance Service computes fairness metrics

**When** the CEO queries the dashboard

**Then** the API returns only pre-aggregated SPD and DIR statistics — no individual-level HMDA data is included in the response

**And** the response includes only aggregate counts (e.g., "approval rate for group A: 78%, approval rate for group B: 72%"), not individual application records

---

**Given** the system has insufficient HMDA data to compute reliable fairness metrics (fewer than 30 decisions with HMDA data)

**When** the CEO views the fair lending section

**Then** the dashboard displays a message: "Insufficient data for fairness metrics. Minimum 30 decisions with demographic data required."

**And** no metrics are displayed

---

**Given** a fairness metric exceeds the concern threshold (e.g., DIR < 0.8)

**When** the dashboard displays the metric

**Then** the metric is highlighted in red

**And** a warning message states: "Disparate Impact Ratio below regulatory guidance threshold. Review recommended."

**And** the warning includes a link to the audit trail filtered to relevant decisions for that time period

---

**Notes:**
- This story integrates F38 (TrustyAI fairness metrics) into the CEO dashboard.
- **HMDA isolation is preserved:** The Compliance Service computes SPD/DIR on aggregate data within the HMDA-accessible path, then exposes only the final statistics. The CEO dashboard never queries the `hmda` schema directly.
- SPD (Statistical Parity Difference): difference in approval rates between protected and reference groups. A value of 0 indicates perfect parity; positive values indicate the protected group has a higher approval rate; negative values indicate lower approval rate.
- DIR (Disparate Impact Ratio): ratio of approval rates (protected group / reference group). A value of 1 indicates perfect parity; values below 0.8 are typically considered evidence of disparate impact under the "80% rule."
- Cross-reference: F38 defines the TrustyAI metric computation within the Compliance Service.

---

### S-5-F12-04: CEO views LO performance metrics

**User Story:**
As a CEO,
I want to view loan officer performance metrics including pipeline volume, pull-through rate, and average turn times,
so that I can compare LO workload, efficiency, and outcomes.

**Acceptance Criteria:**

**Given** the CEO is authenticated and there are loan officers with assigned applications

**When** the CEO views the LO performance section of the dashboard

**Then** the dashboard displays a table or chart with the following columns for each loan officer:
- LO name (partial PII masking applies — names visible, sensitive fields masked)
- Active application count (applications in LO pipeline, stages: Application, Underwriting, Conditional Approval, Final Approval, Closing)
- Closed application count (applications in Closed state, time period filtered)
- Pull-through rate (Closed / Total initiated by LO, time period filtered)
- Average turn time from Application to Underwriting submission (LO's own applications)
- Average turn time from Conditions Issued to Conditions Cleared (measures LO responsiveness to conditions)
- Denial rate (percentage of LO's applications that result in Denied status)

**And** LO performance metrics are scoped to the selected time period (default: last 90 days for closed/denied applications, current for active pipeline)

---

**Given** the CEO sorts the LO performance table by a column (e.g., pull-through rate, turn time)

**When** the table re-sorts

**Then** LOs are ranked by the selected metric

**And** the sort direction (ascending/descending) is indicated by a visual icon

---

**Given** an LO has no applications in the selected time period

**When** the dashboard displays LO performance

**Then** that LO is included in the table with zero values for all metrics

**And** a message in the row states "No activity in this period"

---

**Given** the CEO filters LO performance by product type (Conventional, FHA, VA, etc.)

**When** the dashboard recalculates LO metrics

**Then** all LO metrics are filtered to applications of the selected product type

---

**Notes:**
- LO names are visible because REQ-CC-02 (CEO PII masking) specifies that names remain visible while SSN/DOB/account numbers are masked.
- This story supports operational dashboards that compare LO workload distribution and efficiency.
- "Turn time from Conditions Issued to Conditions Cleared" is a proxy for LO responsiveness — how quickly the LO helps borrowers satisfy conditions.
- Cross-reference: F7 (LO Pipeline) defines LO data scope (LO sees own pipeline only). The CEO sees all LOs' aggregated metrics.

---

### S-5-F12-05: All metrics use masked PII (names visible, SSN/DOB hidden)

**User Story:**
As a CEO,
I want all dashboard data to apply partial PII masking,
so that I can monitor portfolio health without access to borrowers' full sensitive data.

**Acceptance Criteria:**

**Given** the CEO is authenticated and viewing any section of the executive dashboard

**When** the dashboard displays data that includes borrower information

**Then** the following PII masking rules are applied before data reaches the CEO:
- **Borrower names:** Visible (e.g., "Sarah Martinez")
- **SSN:** Masked to show only last 4 digits (e.g., "***-**-1234")
- **DOB:** Masked to show only year or age (e.g., "1985-**-**" or "Age: 39")
- **Account numbers:** Masked to show only last 4 digits (e.g., "****5678")
- **Property addresses:** Visible (street address, city, state, ZIP)
- **Loan amounts and financial data:** Visible

**And** masking occurs at the API response middleware layer **before** the response is sent to the frontend

**And** no unmasked sensitive fields are present in the API response payload

---

**Given** the dashboard queries include joins to borrower or application data

**When** the Analytics Service constructs the query

**Then** the query projects only non-sensitive columns or applies masking functions at the query level

**And** no query returns raw SSN, DOB, or account number columns to the API layer

---

**Given** the CEO attempts to access a detail view that would normally show full PII (e.g., clicking an application ID to see full application detail)

**When** the detail view is rendered

**Then** the same PII masking rules apply in the detail view

**And** if the detail view is not applicable to the CEO role, a 403 Forbidden response is returned

---

**Given** the dashboard includes drill-down functionality (e.g., clicking a denial rate bar to see individual applications)

**When** the drill-down view is displayed

**Then** each listed application shows:
- Borrower name (visible)
- Application ID (visible)
- Loan type and amount (visible)
- Current stage (visible)
- SSN, DOB, account numbers (masked per PII masking rules)

---

**Notes:**
- This story operationalizes REQ-CC-02 (CEO PII masking) for the dashboard.
- Masking is applied at the **API gateway middleware** layer, not in the frontend — the frontend never receives unmasked data.
- Cross-reference: F14 defines RBAC enforcement layers. CEO PII masking is a specialized RBAC rule enforced at API response time.
- Cross-reference: F15 (Audit Trail) uses the same PII masking rules when the CEO queries audit events.

---

## Feature 13: CEO Conversational Analytics

The CEO Conversational Analytics feature allows the CEO to interact with a natural language AI agent to drill down on dashboard metrics, query the audit trail, and ask exploratory questions. This is the **conversational complement** to the visual dashboard (F12). The agent accesses the same data sources as the dashboard (Analytics Service, Audit Service, Compliance Service) and applies the same PII masking rules.

### S-5-F13-01: CEO queries audit trail by application ID

**User Story:**
As a CEO,
I want to query the audit trail by application ID using natural language,
so that I can trace all events associated with a specific application.

**Acceptance Criteria:**

**Given** the CEO is authenticated and has access to the audit trail

**When** the CEO asks the AI agent "Show me the audit trail for application #2024-0847"

**Then** the agent invokes the `audit_search` tool with `application_id = "2024-0847"`

**And** the tool returns all audit events for that application, ordered by timestamp

**And** the agent summarizes the audit trail in natural language, highlighting key events: application created, documents uploaded, submission to underwriting, decision rendered, conditions issued/cleared

**And** the response includes masked PII per REQ-CC-02 (borrower name visible, SSN/DOB/account numbers masked)

---

**Given** the CEO asks for the audit trail of a non-existent application ID

**When** the agent queries the audit trail

**Then** the agent responds: "No audit events found for application ID [provided ID]. Please verify the application ID."

---

**Given** the CEO asks a vague query like "Show me recent audit events"

**When** the agent processes the query

**Then** the agent asks a clarifying question: "Would you like to see audit events for a specific application, decision, or event type? Or would you like a summary of recent activity across all applications?"

---

**Given** the audit trail for an application includes a large number of events (e.g., 50+ events)

**When** the agent returns the audit trail

**Then** the agent provides a summary of event types (e.g., "10 document uploads, 3 conditions issued, 2 conditions cleared, 1 decision rendered") and offers to show details for a specific event type

**And** the full event list is available if the CEO asks for it

---

**Notes:**
- The `audit_search` tool is available to the CEO agent only (not to LO or Underwriter agents).
- Cross-reference: F15 (Audit Trail) defines the audit event schema and query patterns. This story implements the **application-centric query pattern**.

---

### S-5-F13-02: CEO queries audit trail by decision ID

**User Story:**
As a CEO,
I want to query the audit trail by decision ID,
so that I can trace backward from a decision to all contributing events.

**Acceptance Criteria:**

**Given** the CEO is authenticated and has access to the audit trail

**When** the CEO asks "Show me the audit trail for decision #dec-2024-1234"

**Then** the agent invokes the `audit_search` tool with `decision_id = "dec-2024-1234"`

**And** the tool returns all audit events linked to that decision, including:
- The decision event itself (approval or denial)
- All risk assessment tool calls that contributed to the decision
- All compliance check tool calls that contributed to the decision
- All document review events for the associated application
- All prior events for the application linked to the decision

**And** the agent summarizes the decision trace: "Decision #dec-2024-1234 was a denial. The decision was based on a risk assessment that flagged high DTI (52%) and a compliance check that identified an ATR/QM concern. The borrower's income documentation was reviewed on [date]."

**And** the response includes masked PII per REQ-CC-02

---

**Given** the CEO asks for the audit trail of a non-existent decision ID

**When** the agent queries the audit trail

**Then** the agent responds: "No audit events found for decision ID [provided ID]. Please verify the decision ID."

---

**Given** the decision trace includes events from multiple domain services (risk assessment, compliance check, document extraction)

**When** the agent summarizes the trace

**Then** the agent organizes the summary by event type (e.g., "Risk Assessment: ...", "Compliance Check: ...", "Document Review: ...") to make the trace human-readable

---

**Notes:**
- This story implements the **decision-centric query pattern** from REQ-CC-11.
- The decision trace is critical for explaining denials, especially in response to borrower inquiries or regulatory audits.
- Cross-reference: F17 (Decisions) defines decision structure and rationale capture.

---

### S-5-F13-03: CEO queries audit trail by time range and event type

**User Story:**
As a CEO,
I want to query the audit trail by time range and event type,
so that I can identify patterns across the portfolio (e.g., all denials in the last 90 days).

**Acceptance Criteria:**

**Given** the CEO is authenticated and has access to the audit trail

**When** the CEO asks "Show me all denials in the last 90 days"

**Then** the agent invokes the `audit_search` tool with `event_type = "decision"`, `time_range = "last_90_days"`, and a filter for `event_data.decision_outcome = "denied"`

**And** the tool returns all denial events in that time period

**And** the agent summarizes the results: "There were 12 denials in the last 90 days. Top denial reasons: High DTI (5 cases), Insufficient income (4 cases), Credit score below threshold (3 cases)."

**And** the response includes aggregated denial reasons with counts

---

**Given** the CEO asks "Show me all tool call events in the last 30 days"

**When** the agent queries the audit trail

**Then** the agent filters for `event_type = "tool_call"` and `time_range = "last_30_days"`

**And** the agent summarizes the tool call distribution: "Top tools called: risk_assessment (45 calls), compliance_check (38 calls), document_status (29 calls), kb_search (15 calls)."

---

**Given** the CEO asks for a pattern that returns zero results (e.g., "Show me all data_access events with security failures in the last 7 days")

**When** the agent queries the audit trail

**Then** the agent responds: "No security failure events found in the last 7 days. The system has not logged any security events in this period."

---

**Given** the CEO asks for a time range or event type that is ambiguous (e.g., "Show me recent overrides")

**When** the agent processes the query

**Then** the agent clarifies: "Do you mean decision overrides, or all override events? And how far back should I search (30/60/90 days)?"

---

**Notes:**
- This story implements the **pattern-centric query pattern** from REQ-CC-11.
- Aggregated audit queries support portfolio-level compliance monitoring and operational analysis.
- Event types include: `query`, `tool_call`, `data_access`, `decision`, `override`, `system` (per REQ-CC-10).

---

### S-5-F13-04: Audit responses include masked PII

**User Story:**
As a CEO,
I want all audit trail responses to apply partial PII masking,
so that I can trace decisions and events without access to full borrower sensitive data.

**Acceptance Criteria:**

**Given** the CEO queries the audit trail through the conversational agent

**When** the agent returns audit events that include borrower data

**Then** the same PII masking rules from S-5-F12-05 are applied:
- Borrower names: Visible
- SSN: Masked to last 4 digits
- DOB: Masked to year or age
- Account numbers: Masked to last 4 digits

**And** the `event_data` JSONB field in audit events is filtered to remove or mask sensitive fields before being returned to the CEO

---

**Given** an audit event includes a tool call with parameters that contain sensitive data (e.g., `risk_assessment` tool called with full SSN in parameters)

**When** the agent returns that audit event to the CEO

**Then** the sensitive fields in the tool parameters are masked before the response is sent

**And** the masking is applied at the Audit Service layer (not in the agent layer), ensuring defense in depth

---

**Given** the CEO queries an audit event that references a document

**When** the agent returns the audit event

**Then** the event includes the document reference (document ID, type, status) but does not inline document content

**And** the agent notes: "This event references [document type]. Metadata is available; content is not accessible in your role."

---

**Notes:**
- This story operationalizes REQ-CC-02 (CEO PII masking) for audit trail queries.
- The Audit Service applies PII masking when responding to CEO queries — this is a service-layer defense, not just an API-layer defense.
- Cross-reference: S-5-F12-05 defines the CEO PII masking rules. This story applies the same rules to audit trail responses.

---

### S-5-F13-05: Audit trail supports backward tracing from decision

**User Story:**
As a CEO,
I want the audit trail to support backward tracing from a decision to all contributing factors,
so that I can understand the data and reasoning that led to a specific outcome.

**Acceptance Criteria:**

**Given** the CEO is authenticated and queries a decision by ID

**When** the agent traces backward from the decision

**Then** the agent identifies and summarizes:
- The risk assessment that contributed to the decision (DTI, LTV, credit score thresholds)
- The compliance checks that contributed to the decision (ECOA, ATR/QM, TRID results)
- The documents that were reviewed as part of the decision (paystubs, tax returns, credit report)
- The AI recommendation provided by the risk assessment tool
- Whether the underwriter's decision agreed with or overrode the AI recommendation

**And** each contributing factor is linked back to its audit event with timestamp and user who triggered it

---

**Given** the decision includes an override (human decision differed from AI recommendation)

**When** the agent traces backward from the decision

**Then** the agent highlights the override: "The AI recommended approval, but the underwriter denied the application. Rationale: [underwriter's rationale from decision record]."

---

**Given** the backward trace spans multiple domain services (Application, Document, Underwriting, Compliance)

**When** the agent assembles the trace

**Then** the agent organizes the trace chronologically, showing the sequence of events from application creation to decision

**And** the agent groups events by domain service to make the trace readable (e.g., "Document Review: ...", "Risk Assessment: ...", "Compliance Check: ...")

---

**Given** the decision being traced is a denial

**When** the agent summarizes the backward trace

**Then** the agent includes the denial reasons from the decision record and links them to the contributing audit events (e.g., "Denial reason: High DTI (52%). Risk assessment event: [timestamp, event ID].")

---

**Notes:**
- Backward tracing is critical for explainability, especially for denials and regulatory audits.
- This story demonstrates the **decision-centric audit query pattern** (REQ-CC-11) in a conversational interface.
- The agent must synthesize data from multiple audit events into a coherent narrative trace.
- Cross-reference: F17 (Decisions) defines decision rationale capture and AI recommendation comparison.

---

### S-5-F13-06: CEO asks pipeline and performance questions conversationally

**User Story:**
As a CEO,
I want to ask the AI assistant business questions about pipeline performance,
so that I can get answers conversationally instead of only reading dashboard charts.

**Acceptance Criteria:**

**Given** the CEO is authenticated and asks "How many loans does James have in underwriting?"

**When** the agent processes the query

**Then** the agent queries the Analytics Service for application counts filtered by loan officer name and stage

**And** the agent responds with a natural language answer: "James Torres currently has [N] applications in underwriting: [list brief summaries with borrower name, loan amount, days in underwriting]."

---

**Given** the CEO asks "Show me turn times for the conditions clearing stage"

**When** the agent processes the query

**Then** the agent returns average, median, min, and max turn times for the conditional_approval-to-final_approval transition

---

**Given** the CEO asks about an empty dataset (e.g., no applications in a particular stage)

**When** the agent processes the query

**Then** the agent responds "There are currently no applications in [stage]." rather than returning an error

---

**Given** the conversational analytics agent executes a query

**When** the query completes

**Then** the query is logged to the audit trail with event_type='query', including the natural language question and the structured query executed

---

**Given** the agent returns conversational analytics results

**When** the response includes borrower data

**Then** PII masking per REQ-CC-02 applies to all responses (borrower SSN, DOB, account numbers masked; names are visible to CEO)

---

**Notes:**
- This story implements the product plan's F13 PRIMARY purpose: enabling the CEO to ask business questions conversationally.
- The conversational analytics agent uses the same Analytics Service data source as the F12 visual dashboard.
- Cross-reference: F12 (visual dashboard data), F17 (decisions exist to aggregate), REQ-CC-02 (CEO PII masking).

---

### S-5-F13-07: CEO asks comparative questions (time-based)

**User Story:**
As a CEO,
I want to ask comparative questions like "this quarter vs. last quarter",
so that I can identify trends without manually comparing dashboard time ranges.

**Acceptance Criteria:**

**Given** the CEO asks "What is our pull-through rate this quarter vs. last?"

**When** the agent processes the query

**Then** the agent calculates pull-through rate for the current quarter and the previous quarter and presents both with the delta

**And** the response format is: "Pull-through rate this quarter: X% (N closed / M initiated). Last quarter: Y% (P closed / Q initiated). Change: +/-Z percentage points."

---

**Given** the CEO asks "How do denial rates compare month over month?"

**When** the agent processes the query

**Then** the agent returns a monthly breakdown for the last 3-6 months with trend direction

---

**Given** the comparison period has zero applications (e.g., the system was just deployed)

**When** the agent calculates the comparison

**Then** the agent states "Insufficient data for [period]. [Other period] pull-through rate: X%." rather than dividing by zero

---

**Given** the CEO asks a comparative question

**When** the agent queries data

**Then** the agent uses the same data source as F12 dashboard metrics (Analytics Service) to ensure consistency between visual and conversational answers

---

**Notes:**
- Comparative queries help the CEO identify trends without switching between dashboard time range filters.
- The agent must handle edge cases where one period has data and the other does not (e.g., new deployment).
- Cross-reference: F12 (visual dashboard data), S-5-F12-01 (pull-through rate definition).

---

### S-5-F13-08: CEO asks about specific loan officer or application by name

**User Story:**
As a CEO,
I want to ask about a specific loan officer's performance or a specific application by borrower name,
so that I can drill into details conversationally.

**Acceptance Criteria:**

**Given** the CEO asks "How is James Torres performing?"

**When** the agent processes the query

**Then** the agent returns James's key metrics: active pipeline count, average turn time, pull-through rate, denial rate, and AI recommendation agreement rate

---

**Given** the CEO asks "What's the status of Sarah Mitchell's application?"

**When** the agent processes the query

**Then** the agent returns the application's current state, stage history with timestamps, assigned LO, and any outstanding conditions

**And** PII masking per REQ-CC-02 applies: CEO sees borrower names but SSN/DOB/account numbers are masked in the response

---

**Given** the CEO asks about a borrower or LO that doesn't exist in the system

**When** the agent processes the query

**Then** the agent responds "I couldn't find a [borrower/loan officer] named [name]. Would you like me to search by application ID instead?"

---

**Given** the CEO asks about an LO's HMDA-related performance (e.g., "Does James have disparate denial patterns?")

**When** the agent processes the query

**Then** the agent routes this to the fair lending analysis path (S-5-F13-09) rather than answering from the general analytics pipeline

---

**Notes:**
- This story enables drill-down from portfolio-level metrics to individual LO or application details.
- PII masking ensures the CEO sees names but not sensitive identifiers.
- Fair lending questions are routed to S-5-F13-09 to ensure proper HMDA pre-aggregation.
- Cross-reference: F12 (LO performance metrics), REQ-CC-02 (CEO PII masking), REQ-CC-07 (HMDA pre-aggregation).

---

### S-5-F13-09: CEO asks fair lending questions conversationally

**User Story:**
As a CEO,
I want to ask fair lending questions conversationally,
so that I can explore disparate impact concerns without navigating the dashboard's fair lending panel.

**Acceptance Criteria:**

**Given** the CEO asks "Are there any disparate impact concerns in our denial rates?"

**When** the agent processes the query

**Then** the agent queries the Compliance Service for the latest TrustyAI fairness metrics (SPD, DIR) and returns a natural language summary

**And** the response format is: "Current fairness analysis: Statistical Parity Difference (SPD) is [value] ([concern level]). Disparate Impact Ratio (DIR) is [value] ([concern level]). [If concerning:] The denial rate for [protected group] is [X%] compared to [Y%] for [reference group]. This warrants review."

---

**Given** the CEO asks "What percentage of applications are denied and what are the top reasons?"

**When** the agent processes the query

**Then** the agent returns overall denial rate and a ranked list of denial reasons from decision records

---

**Given** the agent queries fair lending metrics

**When** the Compliance Service returns HMDA data

**Then** HMDA data is presented ONLY in aggregate form per REQ-CC-07 (pre-aggregated, k-anonymity threshold of 5)

**And** individual HMDA records are never exposed, even to the CEO

---

**Given** the fairness metrics show no concerns (SPD within threshold, DIR within threshold)

**When** the agent summarizes the fairness analysis

**Then** the agent states "Current fairness metrics are within acceptable ranges. SPD: [value], DIR: [value]. No disparate impact concerns detected at this time."

---

**Given** the agent returns fair lending analysis

**When** the response is sent to the CEO

**Then** the regulatory disclaimer per REQ-CC-17 is included: "Note: Fairness metrics are calculated for demonstration purposes using simulated data."

---

**Given** the CEO asks a fair lending conversational query

**When** the query completes

**Then** the query is logged to the audit trail with event_type='compliance_check'

---

**Notes:**
- This story enables conversational exploration of fair lending metrics without navigating the F12 dashboard's fair lending panel.
- The conversational agent uses the same Compliance Service as the F12 visual dashboard, which enforces HMDA pre-aggregation (REQ-CC-07).
- The conversational agent never accesses raw HMDA data — only pre-aggregated metrics with k-anonymity threshold of 5.
- Cross-reference: F12 (visual dashboard data), F38 (TrustyAI fairness metrics), F25 (HMDA collection), REQ-CC-02 (CEO PII masking), REQ-CC-07 (HMDA pre-aggregation), REQ-CC-17 (regulatory disclaimer).

---

## Feature 15: Audit Trail -- Export Capability

F15 provides the ability to export audit trail data in CSV or JSON format for external analysis by regulators and auditors. This complements the conversational audit queries in F13 by enabling offline analysis in external tools.

### S-5-F15-07: Authorized user exports audit trail data

**User Story:**
As a CEO or Underwriter,
I want to export audit trail data for a given application or time range in CSV or JSON format,
so that regulators and auditors can analyze the data in their own tools.

**Acceptance Criteria:**

**Given** the CEO or Underwriter is authenticated and requests an audit export for a specific application ID

**When** the export is triggered

**Then** the system generates a file containing all audit events for that application in the requested format (CSV or JSON)

**And** the export includes: event_id, timestamp, event_type, user_id, user_role, application_id, event_data (structured), and prev_hash (for tamper evidence verification)

---

**Given** the user requests an audit export

**When** the export is generated

**Then** PII masking rules apply per the user's role: CEO exports have SSN/DOB/account masked (REQ-CC-02); Underwriter exports have full PII visible for their authorized applications

---

**Given** the user requests export for a time range (e.g., "last 30 days")

**When** the export is generated

**Then** the system exports all audit events within that range, regardless of application

---

**Given** the export would exceed a size threshold (e.g., 10,000 events)

**When** the user requests the export

**Then** the system paginates the export or prompts the user to narrow the query

---

**Given** a Loan Officer requests an audit export

**When** the request is received

**Then** the system denies the request (LOs do not have audit export permissions per REQ-CC-01 role matrix)

---

**Given** a Borrower requests an audit export

**When** the request is received

**Then** the system denies the request

---

**Given** a user successfully exports audit data

**When** the export completes

**Then** the export event itself is logged to the audit trail with event_type='data_access', including who requested the export, what scope, and when

---

**Given** the user selects CSV export format

**When** the export is generated

**Then** the system generates a CSV file with columns for each audit event field (event_id, timestamp, event_type, user_id, user_role, application_id, event_data, prev_hash)

**And** complex fields (event_data JSONB) are serialized to JSON strings within the CSV

---

**Given** the user selects JSON export format

**When** the export is generated

**Then** the system generates a JSON array of audit event objects, with each object containing all event fields in structured format

---

**Notes:**
- This story fulfills the product plan's F15 "export capability" requirement: "Audit data can be exported for external analysis. Regulators and auditors need to analyze data in their own tools."
- Export format options: CSV (for spreadsheet analysis) and JSON (for programmatic analysis). Default is CSV.
- The export includes `prev_hash` to enable tamper evidence verification — auditors can verify the hash chain integrity.
- Cross-reference: F15 (audit trail, chunk 2), REQ-CC-08 (audit completeness), REQ-CC-09 (tamper evidence), REQ-CC-01 (role-based access control), REQ-CC-02 (CEO PII masking).

---

## Feature 23: Container Platform Deployment

F23 provides Helm charts for deploying the full application stack on OpenShift or generic Kubernetes. The Helm charts translate the Compose services (F22) into Kubernetes manifests with environment-specific configuration via `values.yaml`.

### S-5-F23-01: Helm chart deploys API, UI, DB, Keycloak, LlamaStack, LangFuse

**User Story:**
As a platform operator,
I want to deploy the full application stack using a Helm chart,
so that I can run the application on OpenShift or Kubernetes without manually creating manifests.

**Acceptance Criteria:**

**Given** the operator has Helm installed and access to an OpenShift or Kubernetes cluster

**When** the operator runs `helm install summit-cap ./deploy/helm/summit-cap-financial`

**Then** the following Kubernetes resources are created:
- `Deployment` for the API service (FastAPI application)
- `Deployment` for the UI service (React frontend via nginx)
- `StatefulSet` for PostgreSQL with persistent volume
- `Deployment` for Keycloak
- `Deployment` for LlamaStack server
- `Deployment` for LangFuse web UI
- `Deployment` for LangFuse worker
- `StatefulSet` for Redis (LangFuse dependency)
- `StatefulSet` for ClickHouse (LangFuse dependency)
- `Service` resources for each deployment
- `Route` (OpenShift) or `Ingress` (Kubernetes) for external access to UI and API

**And** all services start in dependency order (PostgreSQL first, then Keycloak, then API, etc.)

**And** health checks and readiness probes ensure services are healthy before dependent services start

---

**Given** the Helm chart is installed

**When** the operator runs `kubectl get pods -n <namespace>`

**Then** all pods are in `Running` state and pass readiness checks

---

**Given** the Helm chart includes a `values.yaml` file with configurable parameters

**When** the operator inspects the default `values.yaml`

**Then** the file includes:
- Image tags for all services (API, UI, DB, Keycloak, LlamaStack, LangFuse components)
- Replica counts for each service (default: 1 for all services at PoC scale)
- Resource requests and limits for each service (CPU, memory)
- Environment-specific overrides (database URL, Keycloak URL, LlamaStack endpoint, object storage configuration)
- Ingress/Route configuration (hostnames, TLS settings)
- Storage class names for persistent volumes

---

**Given** the operator wants to override default values (e.g., use a different PostgreSQL instance)

**When** the operator creates a custom `values-production.yaml` file and runs `helm install summit-cap ./deploy/helm/summit-cap-financial -f values-production.yaml`

**Then** the Helm chart uses the values from `values-production.yaml` to override defaults

**And** the custom database URL, Keycloak URL, and other overrides are injected as environment variables into the API deployment

---

**Notes:**
- The Helm chart structure follows the standard Helm chart layout: `Chart.yaml`, `values.yaml`, `templates/` directory with manifest templates.
- Cross-reference: F22 (Single-command setup) defines the Compose service inventory. The Helm chart translates each Compose service into a Kubernetes deployment or stateful set.
- OpenShift-specific resources (e.g., `Route` instead of `Ingress`) are conditionally rendered based on a `platform` value in `values.yaml`.

---

### S-5-F23-02: Helm values.yaml supports environment-specific overrides

**User Story:**
As a platform operator,
I want the Helm chart to support environment-specific configuration via `values.yaml`,
so that I can deploy the same chart to dev, staging, and production with different configurations.

**Acceptance Criteria:**

**Given** the Helm chart includes a default `values.yaml` with PoC-appropriate defaults

**When** the operator creates an environment-specific override file (e.g., `values-dev.yaml`, `values-staging.yaml`, `values-production.yaml`)

**Then** the override file can customize:
- Database connection URL (external managed database vs. in-cluster PostgreSQL)
- Keycloak URL (external enterprise IdP vs. in-cluster Keycloak)
- LlamaStack endpoint (local inference vs. OpenShift AI InferenceService)
- Object storage backend (local PVC vs. S3-compatible endpoint)
- Ingress/Route hostnames (e.g., `summit-cap-dev.apps.example.com`, `summit-cap-prod.apps.example.com`)
- TLS certificate source (self-signed vs. cert-manager vs. platform default)
- Replica counts (1 for dev, 3 for production)
- Resource limits (smaller for dev, larger for production)

**And** the operator installs the chart with the override file: `helm install summit-cap ./deploy/helm/summit-cap-financial -f values-production.yaml`

**And** the chart applies the overrides to all relevant Kubernetes resources

---

**Given** the operator wants to use an external managed PostgreSQL instance in production

**When** the operator sets `postgresql.enabled: false` and `database.url: "postgresql://external-db.example.com/summit_cap"` in `values-production.yaml`

**Then** the Helm chart does not create a PostgreSQL `StatefulSet`

**And** the API `Deployment` uses the external database URL from environment variables

---

**Given** the operator wants to deploy to OpenShift and use OpenShift AI model serving

**When** the operator sets `llamastack.endpoint: "https://openshift-ai-inference.example.com"` in `values.yaml`

**Then** the Helm chart configures the LlamaStack server to point to the OpenShift AI InferenceService endpoint

**And** no local model serving containers are deployed

---

**Notes:**
- The `values.yaml` pattern is the standard Helm mechanism for environment-specific configuration.
- The Helm chart should include commented examples of common overrides in the default `values.yaml` to guide operators.
- Cross-reference: Architecture Section 7.1 (Deployment Modes) describes the differences between local development and OpenShift production configurations.

---

### S-5-F23-03: DB migration runs as init container

**User Story:**
As a platform operator,
I want database migrations to run automatically as an init container,
so that the database schema is up-to-date before the API service starts.

**Acceptance Criteria:**

**Given** the Helm chart includes an API `Deployment`

**When** the API pod is created

**Then** the pod includes an `initContainer` that runs the database migration command (`alembic upgrade head`)

**And** the init container uses the same database connection URL as the API service (from environment variables)

**And** the init container must complete successfully before the main API container starts

---

**Given** the database is not yet initialized (no tables exist)

**When** the init container runs migrations

**Then** the migration command creates all required tables and indexes

**And** the migration command exits with code 0 on success

**And** the API pod proceeds to start the main container

---

**Given** the database schema is already at the latest version (migrations are up-to-date)

**When** the init container runs migrations

**Then** the migration command detects that no migrations are needed

**And** the migration command exits with code 0 (no-op success)

**And** the API pod proceeds to start the main container

---

**Given** the database is unreachable when the init container runs

**When** the init container attempts to connect

**Then** the init container retries connection with exponential backoff (up to 5 retries over 30 seconds)

**And** if the database remains unreachable after retries, the init container exits with a non-zero code

**And** the API pod enters `Init:Error` state and does not start the main container

**And** Kubernetes restarts the pod according to the restart policy

---

**Notes:**
- The init container approach ensures that migrations run exactly once per deployment, before the API service handles requests.
- The migration init container should use the same Docker image as the API service to ensure consistency.
- Cross-reference: F22 (Single-command setup) uses Compose health checks to order service startup. The Helm chart uses init containers for the same purpose.

---

### S-5-F23-04: LlamaStack configured to use OpenShift AI InferenceService endpoints

**User Story:**
As a platform operator,
I want to configure LlamaStack to use OpenShift AI InferenceService endpoints,
so that the application uses platform-managed model serving instead of deploying local inference containers.

**Acceptance Criteria:**

**Given** the operator is deploying to an OpenShift cluster with OpenShift AI installed

**When** the operator sets `llamastack.inferenceService.enabled: true` and `llamastack.inferenceService.endpoint: "https://inference.openshift-ai.svc.cluster.local"` in `values.yaml`

**Then** the Helm chart configures the LlamaStack server to point to the OpenShift AI InferenceService endpoint

**And** the LlamaStack server's `run.yaml` configuration is updated to use the InferenceService endpoint as the model provider

**And** no local model serving containers (Ollama, vLLM) are deployed

---

**Given** the OpenShift AI InferenceService exposes multiple model endpoints (e.g., small-model, large-model)

**When** the operator configures multiple endpoints in `values.yaml` (e.g., `llamastack.inferenceService.smallModelEndpoint`, `llamastack.inferenceService.largeModelEndpoint`)

**Then** the LlamaStack server configuration includes both endpoints

**And** the model routing logic (F21) selects the appropriate endpoint based on query complexity

---

**Given** the OpenShift AI InferenceService requires authentication (e.g., service account token)

**When** the operator sets `llamastack.inferenceService.authToken: <secret-name>` in `values.yaml`

**Then** the Helm chart mounts the secret as an environment variable in the LlamaStack pod

**And** the LlamaStack server includes the auth token in requests to the InferenceService

---

**Given** the operator wants to test the LlamaStack configuration before deploying the full application

**When** the operator runs `kubectl exec -it <llamastack-pod> -- curl <inference-endpoint>/health`

**Then** the InferenceService responds with a 200 OK health check

**And** the operator confirms that the LlamaStack pod can reach the InferenceService

---

**Notes:**
- This story demonstrates the "natural integration" between the application and OpenShift AI model serving (Architecture Section 7.4).
- The LlamaStack server's configuration (`run.yaml`) is generated from the Helm chart's `values.yaml` using a ConfigMap template.
- Cross-reference: ADR-0004 (LlamaStack Abstraction Layer) explains why LlamaStack is the model serving abstraction.

---

### S-5-F23-05: Object storage configured to use S3-compatible backend (ODF/MinIO)

**User Story:**
As a platform operator,
I want to configure the application to use an S3-compatible object storage backend,
so that document files are stored in a scalable, production-appropriate storage system instead of local filesystem.

**Acceptance Criteria:**

**Given** the operator is deploying to a cluster with OpenShift Data Foundation (ODF) or MinIO installed

**When** the operator sets the following in `values.yaml`:
```yaml
objectStorage:
  type: s3
  endpoint: "https://s3.openshift-storage.svc.cluster.local"
  bucket: "summit-cap-documents"
  accessKey: "<secret-name>"
  secretKey: "<secret-name>"
```

**Then** the Helm chart configures the API service to use the S3-compatible backend for document storage

**And** the API service's environment variables include:
- `OBJECT_STORAGE_TYPE=s3`
- `S3_ENDPOINT=https://s3.openshift-storage.svc.cluster.local`
- `S3_BUCKET=summit-cap-documents`
- `S3_ACCESS_KEY` and `S3_SECRET_KEY` (mounted from Kubernetes secrets)

---

**Given** the application writes a document to object storage

**When** the Document Service calls the storage abstraction layer

**Then** the storage layer uses the configured S3 client to upload the document to the S3 bucket

**And** the document metadata record in PostgreSQL includes the S3 object key (not a filesystem path)

---

**Given** the operator wants to use local filesystem storage in a dev environment

**When** the operator sets `objectStorage.type: filesystem` in `values.yaml`

**Then** the Helm chart configures the API service to use a persistent volume for document storage

**And** the API pod mounts a PVC at `/data/documents`

**And** the application stores documents to the filesystem path

---

**Given** the S3 backend is unreachable when the application attempts to upload a document

**When** the upload request fails

**Then** the Document Service logs the error with full context (document ID, S3 endpoint, error message)

**And** the application returns a 503 Service Unavailable error to the user

**And** the document metadata record is updated with status "upload_failed"

---

**Notes:**
- The storage abstraction layer isolates the Document Service from the storage backend implementation. Switching from filesystem to S3 requires only configuration changes, not code changes.
- The S3 client should support both AWS S3 and S3-compatible APIs (ODF, MinIO, Ceph).
- Cross-reference: Architecture Section 7.1 (Deployment Modes) describes the difference between local filesystem (dev) and S3-compatible (production) storage.

---

## Feature 39: Model Monitoring Overlay

F39 provides a lightweight monitoring overlay that displays inference health metrics (latency, token usage, error rates, model routing distribution) on the CEO dashboard and observability dashboard. These metrics are sourced from LangFuse, which already collects them via callbacks attached to every agent invocation. No additional monitoring infrastructure, agents, or containers are required.

### S-5-F39-01: CEO dashboard displays model latency percentiles

**User Story:**
As a CEO,
I want to view model latency percentiles on the executive dashboard,
so that I can monitor inference performance and identify slowdowns.

**Acceptance Criteria:**

**Given** the CEO is authenticated and viewing the executive dashboard

**When** the CEO navigates to the model monitoring panel

**Then** the panel displays model latency metrics:
- P50 (median) latency in milliseconds
- P95 latency in milliseconds
- P99 latency in milliseconds
- Latency trend over time (line chart, hourly granularity for 24-hour view, daily granularity for 7-day view)

**And** latency metrics are calculated per model endpoint (small-model, large-model) if multiple models are configured

**And** latency includes only LLM inference time, not total agent execution time (i.e., time from LLM request to LLM response, excluding tool call time)

---

**Given** the CEO filters latency metrics by model endpoint (small-model vs. large-model)

**When** the panel recalculates latency

**Then** the displayed percentiles and trend chart are filtered to the selected model endpoint

**And** the filter selection is displayed above the latency panel

---

**Given** there are no LLM calls in the selected time period (e.g., no agent activity in the last 24 hours)

**When** the CEO views the latency panel

**Then** the panel displays a message: "No LLM calls in this time period"

**And** the percentile values are not displayed

---

**Given** latency exceeds a configurable threshold (e.g., P95 > 5000ms)

**When** the CEO views the latency panel

**Then** the latency value is highlighted in yellow or red to indicate a performance concern

**And** a tooltip states: "Latency exceeds typical range. Investigate model serving health."

---

**Notes:**
- Latency percentiles are computed from LangFuse trace data. The LangFuse callback handler captures LLM call start/end timestamps.
- The FastAPI backend queries model monitoring metrics from the LangFuse observability backend to fetch latency statistics.
- Cross-reference: F18 (LangFuse observability integration) establishes the callback handler that collects latency data.

---

### S-5-F39-02: CEO dashboard displays token usage

**User Story:**
As a CEO,
I want to view token usage metrics on the executive dashboard,
so that I can monitor inference costs and model efficiency.

**Acceptance Criteria:**

**Given** the CEO is authenticated and viewing the model monitoring panel

**When** the CEO views the token usage section

**Then** the panel displays:
- Total tokens consumed in the selected time period (sum of input tokens + output tokens)
- Input token count
- Output token count
- Token usage trend over time (line chart, hourly granularity for 24-hour view, daily for 7-day view)
- Token usage by model endpoint (if multiple models are configured)

**And** token counts are sourced from LangFuse trace data, which captures token usage per LLM call

---

**Given** the CEO filters token usage by model endpoint

**When** the panel recalculates token usage

**Then** the displayed token counts and trend chart are filtered to the selected model endpoint

---

**Given** there are no LLM calls in the selected time period

**When** the CEO views the token usage panel

**Then** the panel displays "No token usage in this time period"

**And** token counts are not displayed

---

**Given** token usage exceeds a configurable daily budget (e.g., 1,000,000 tokens/day)

**When** the CEO views the token usage panel

**Then** the token count is highlighted in yellow or red to indicate budget concern

**And** a tooltip states: "Token usage exceeds daily budget. Review query complexity or model routing."

---

**Notes:**
- Token usage is a proxy for inference cost when using hosted model APIs.
- The token usage panel supports cost monitoring without exposing raw dollar amounts (which depend on provider pricing).
- Cross-reference: F21 (Model routing) affects token usage — routing simple queries to small models reduces token consumption.

---

### S-5-F39-03: CEO dashboard displays error rates

**User Story:**
As a CEO,
I want to view model error rates on the executive dashboard,
so that I can monitor inference reliability and detect failures.

**Acceptance Criteria:**

**Given** the CEO is authenticated and viewing the model monitoring panel

**When** the CEO views the error rate section

**Then** the panel displays:
- Total LLM call count in the selected time period
- Error count (LLM calls that resulted in an error)
- Error rate (percentage of LLM calls that failed)
- Error rate trend over time (line chart, hourly granularity for 24-hour view)
- Top error types with counts (e.g., "timeout", "model unavailable", "rate limit exceeded")

**And** error data is sourced from LangFuse trace data, which captures LLM call exceptions

---

**Given** the CEO filters error rate by model endpoint

**When** the panel recalculates error rate

**Then** the displayed error count, rate, and top error types are filtered to the selected model endpoint

---

**Given** there are no errors in the selected time period

**When** the CEO views the error rate panel

**Then** the panel displays "Error rate: 0%" with a message "No errors in this time period"

**And** the top error types chart is not displayed

---

**Given** the error rate exceeds a threshold (e.g., error rate > 5%)

**When** the CEO views the error rate panel

**Then** the error rate is highlighted in red

**And** a warning message states: "Error rate exceeds acceptable threshold. Investigate model serving health or network connectivity."

---

**Notes:**
- Error types are classified based on the exception type captured in LangFuse traces (e.g., `TimeoutError`, `ConnectionError`, `HTTPError 503`).
- High error rates indicate model serving issues, network problems, or rate limiting.

---

### S-5-F39-04: CEO dashboard displays model routing distribution

**User Story:**
As a CEO,
I want to view model routing distribution on the executive dashboard,
so that I can verify that simple queries are routed to fast models and complex queries to capable models.

**Acceptance Criteria:**

**Given** the CEO is authenticated and viewing the model monitoring panel

**When** the CEO views the model routing section

**Then** the panel displays:
- Total LLM call count in the selected time period
- Calls routed to small-model (count and percentage)
- Calls routed to large-model (count and percentage)
- Routing distribution as a pie chart or bar chart

**And** routing distribution is sourced from LangFuse trace data, which includes the model name for each LLM call

---

**Given** the application uses model routing (F21)

**When** the CEO views the routing distribution

**Then** the distribution reflects the routing logic: simple queries routed to small-model, complex queries routed to large-model

**And** if routing is heavily skewed (e.g., 95% of queries routed to large-model), a note states: "Most queries are routed to the large model. Consider tuning the routing classifier."

---

**Given** the application does not use model routing (only one model is configured)

**When** the CEO views the routing distribution

**Then** the panel displays "Routing disabled: all queries use the same model"

**And** the routing distribution chart is not displayed

---

**Given** the CEO drills down into routing distribution (e.g., clicks on "small-model" segment of the pie chart)

**When** the drill-down view is displayed

**Then** the view shows a sample of queries routed to that model, including:
- Query text (truncated to 100 characters)
- Timestamp
- Latency
- Token usage

---

**Notes:**
- Model routing distribution verifies that the routing logic (F21) is working as expected.
- A balanced distribution (e.g., 60% small-model, 40% large-model) indicates effective routing that optimizes cost and latency.
- Cross-reference: F21 (Model routing) defines the routing strategy and classifier.

---

### S-5-F39-05: Metrics sourced from LangFuse via API proxy

**User Story:**
As a platform operator,
I want model monitoring metrics to be sourced from LangFuse without deploying additional monitoring infrastructure,
so that the monitoring overlay is lightweight and reuses existing observability data.

**Acceptance Criteria:**

**Given** the application has LangFuse observability integration enabled (F18)

**When** the CEO dashboard requests model monitoring metrics

**Then** the FastAPI backend queries model monitoring metrics from the LangFuse observability backend

**And** the backend acts as a proxy, translating LangFuse API responses into the format expected by the frontend

**And** no additional monitoring containers, agents, or services are deployed

---

**Given** the LangFuse API is unreachable when the dashboard requests metrics

**When** the backend attempts to proxy the request

**Then** the backend returns a 503 Service Unavailable error to the frontend

**And** the dashboard displays a message: "Monitoring metrics temporarily unavailable"

**And** the error is logged with full context (LangFuse endpoint, error message)

---

**Given** the dashboard requests metrics for a time range that is too large (e.g., 12 months)

**When** the backend queries LangFuse

**Then** the backend applies a maximum time range limit (e.g., 90 days) and returns results for the limited range

**And** the dashboard displays a note: "Metrics limited to last 90 days. For longer historical analysis, access LangFuse directly."

---

**Given** the operator wants to customize the monitoring overlay (e.g., add a custom metric, change thresholds)

**When** the operator modifies the backend proxy logic

**Then** the operator can add new LangFuse queries or transform existing metrics without changing the LangFuse integration

**And** the monitoring overlay remains decoupled from the LangFuse schema

---

**Notes:**
- The FastAPI backend acts as a proxy to isolate the frontend from LangFuse API changes and to apply authorization (only CEO and admin roles can access monitoring metrics).
- The monitoring overlay is "lightweight" because it reuses data already collected by LangFuse callbacks — no new data collection infrastructure is required.
- Cross-reference: F18 (LangFuse observability integration) establishes the callback handler that populates the data used by the monitoring overlay.

---

## Open Questions for Chunk 5

| ID | Question | Impact | Notes |
|----|----------|--------|-------|
| REQ-C5-OQ-01 | What is the CEO dashboard refresh rate for real-time metrics (pipeline volume, denial rate)? | Low | Suggested: 30-second auto-refresh for real-time panels, manual refresh button for heavy queries (fair lending metrics, audit trail). |
| REQ-C5-OQ-02 | What are the exact SPD/DIR thresholds for yellow/red concern indicators on the fair lending panel? | Medium | Suggested: SPD > 0.1 = yellow, SPD > 0.2 = red; DIR < 0.8 = red, DIR < 0.9 = yellow. Confirm with stakeholder or domain expert. |
| REQ-C5-OQ-03 | What is the default time range for CEO dashboard metrics (last 30/60/90 days)? | Low | Suggested: 90 days for pipeline/denial/fairness metrics, 24 hours for model monitoring metrics (latency, token usage). |
| REQ-C5-OQ-04 | Should the CEO conversational agent have access to the LO performance comparison tool (F12 LO metrics) or only aggregate portfolio metrics? | Low | Suggested: CEO agent can query LO performance metrics conversationally, same data as the visual dashboard. |
| REQ-C5-OQ-05 | What is the maximum audit trail query result size (to prevent unbounded result sets)? | Medium | Suggested: 1000 events max per query, with pagination or a prompt to narrow the query if result size exceeds limit. |

## Assumptions for Chunk 5

| ID | Assumption | Risk If Wrong | Mitigation |
|----|-----------|--------------|------------|
| REQ-C5-A-01 | The Analytics Service can compute aggregates across 5-10 active applications and 15-25 historical loans in under 2 seconds (acceptable dashboard load time) | Low — PoC scale is intentionally small | If aggregate queries are slow, add database indexes on timestamp and stage columns; consider materialized views for production. |
| REQ-C5-A-02 | LangFuse exposes an API or SQL access to ClickHouse for querying trace metrics (latency, token usage, error rates) | High — F39 depends on this | Verify LangFuse API documentation during Phase 1. If API is insufficient, query ClickHouse directly (LangFuse stores traces in ClickHouse). |
| REQ-C5-A-03 | Helm chart deployment completes in under 10 minutes on a standard OpenShift cluster with pre-pulled images | Low — similar to F22 assumption | Document timing expectations; exclude persistent volume provisioning time from target if storage class is slow. |
| REQ-C5-A-04 | OpenShift AI InferenceService endpoints are compatible with LlamaStack's model provider abstraction | Medium — F23 depends on this | Verify LlamaStack can connect to KServe endpoints during Phase 4b. If incompatible, add an adapter layer. |
| REQ-C5-A-05 | CEO dashboard charting library supports the required chart types (line charts, bar charts, pie charts, funnel visualization) | Low — many charting libraries meet this requirement | Select a well-documented React charting library (e.g., Recharts, Chart.js, Nivo) during Phase 4a. |

---

*Generated during SDD Phase 7 (Requirements). This is Pass 2 Chunk 5 (Executive Experience and Deployment).*
