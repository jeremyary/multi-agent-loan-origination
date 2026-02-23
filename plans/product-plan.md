# FSI AI Quickstart

## Application Personas

### Prospect (Public Website Visitor)
- **Role:** Anonymous visitor to Summit Cap Financial's public website
- **Goals:** Browse mortgage products; get answers to general mortgage questions; use affordability and payment estimation tools; explore pre-qualification
- **Pain Points:** Overwhelmed by mortgage jargon; unsure if they qualify; has questions about the mortgage process

### Sarah Mitchell (Borrower)
- **Role:** Authenticated customer applying for or managing a mortgage loan
- **Goals:** Apply for a mortgage; track application status and underwriting conditions; upload documents; ask questions about loan terms and timeline
- **Pain Points:** Process is opaque and stressful; doesn't know what stage her application is in; unsure what documents are still needed or why they were rejected

### James Torres (Loan Officer)
- **Role:** Employee who originates and manages mortgage applications
- **Goals:** Manage pipeline of active applications; prepare files for underwriting; clear conditions; communicate with borrowers; track deadlines
- **Pain Points:** Juggling multiple applications at different stages; manually checking document completeness; conditions clearing is the most time-consuming post-submission activity

### Maria Chen (Underwriter)
- **Role:** Employee who evaluates mortgage applications for approval
- **Goals:** Review applications and assess risk; verify regulatory and guideline compliance; make approval/conditional/denial decisions; issue and track conditions
- **Pain Points:** Must cross-reference multiple data sources; needs to document rationale for every decision for audit purposes; conditions loop is time-consuming

### David Park (CEO)
- **Role:** Chief Executive Officer of Summit Cap Financial
- **Goals:** Monitor pipeline health, pull-through rate, turn times, and loan officer performance; review fair lending compliance metrics
- **Pain Points:** Data is scattered across systems; getting answers requires waiting for reports or asking analysts

### Persona Gap: Loan Processor (Intentionally left off for post-quickstart exercise)

The Loan Processor role is absorbed into the Loan Officer for PoC simplicity. This is an intentional expansion path for Quickstart users.

## Proposed Solution

Build a full-stack web application that demonstrates agentic AI applied to the mortgage lending lifecycle. Summit Cap Financial is a fictional mortgage lender headquartered in Denver, Colorado, licensed to originate loans in Colorado, operating under both federal regulations and Colorado Division of Real Estate oversight. The application covers the process from initial prospect inquiry through pre-qualification, application, underwriting (including iterative conditions clearing), and approval.

Five distinct user experiences share a common backend but demonstrate different AI capabilities, guardrails, and access levels:

- **Public-facing virtual assistant** with tight guardrails scoped to Summit Cap Financial's mortgage products, including pre-qualification guidance
- **Borrower portal** with a personal AI assistant that accesses the borrower's own data and documents, guiding borrowers through the full application process via conversational AI
- **Loan Officer workspace** with an AI assistant for pipeline management, application preparation, conditions clearing, and borrower communications
- **Underwriter workspace** with a compliance-aware AI assistant backed by a three-tier knowledge base (federal regulations, agency/investor guidelines, and internal policies) that supports iterative review with conditions
- **Executive dashboard** with a conversational AI assistant for business intelligence, drill-down analysis, and fair lending compliance monitoring

The application supports pre-seeded demo data that simulates an active lending operation: borrowers at various stages, document packages in various states of completeness, historical loan data, rate locks, closing dates, conditions at various stages of resolution, and realistic (but fictional) financial figures. Demo data is seeded by default for the Quickstart experience, but seeding is optional at deployment time -- the application can start with an empty pipeline for developers adapting the Quickstart to their own domain (see F20, F22).

Every AI action, data access, recommendation, and decision is logged to a comprehensive audit trail with decision-centric traceability, override tracking, and data provenance. The system demonstrates regulatory awareness by referencing relevant regulations (using correct post-TRID terminology), enforcing fair lending guardrails while simultaneously collecting HMDA-required demographic data, generating required disclosure documents, and maintaining compliance documentation. All regulatory content is clearly labeled as simulated for demonstration purposes.

## Success Metrics

| Metric | Current Baseline | Target | Measurement Method | Audience |
|--------|-----------------|--------|-------------------|----------|
| Summit demo readiness | No application exists | Fully functional demo covering all 5 personas by mid-May 2025 | Successful end-to-end walkthrough of all persona flows | Demo |
| Local setup time | N/A | Developer can run the full app locally with a single command in under 10 minutes | Timed test by a developer unfamiliar with the project | Quickstart |
| Persona coverage | 0 personas | 5 distinct persona experiences with visible RBAC differences | Manual verification of access boundaries per persona | Both |
| Compliance demonstration | No compliance features | Audit trail covers all AI actions with decision traceability; HMDA collection + fair lending refusal coexist; adverse action notices generated; regulatory references use correct terminology | Review of audit log completeness, HMDA flow testing, guardrail trigger testing | Both |
| Domain credibility | N/A | No confidently incorrect regulatory statements; correct use of industry terminology (TRID, 1003/URLA, ATR/QM) | Domain expert review of compliance content before Summit demo | Both |
| Conditions workflow | No capability | Underwriter can issue conditions; LO can respond; file can loop back through underwriting | End-to-end test of conditional approval through conditions clearing | Both |

## Feature Scope

### Must Have (P0)

- [ ] **F1: Public Virtual Assistant with Guardrails** -- A chat interface on the public website where anonymous visitors can ask questions about Summit Cap Financial's mortgage products. Summit Cap Financial offers six mortgage products: 30-year fixed-rate, 15-year fixed-rate, adjustable-rate (ARM), jumbo loans, FHA loans, and VA loans. The assistant is tightly guardrailed to discuss only these products and general mortgage education. It refuses to discuss competitors, provide investment advice, or engage in off-topic conversation. Demonstrates the guardrails pattern.

- [ ] **F2: Prospect Affordability and Pre-Qualification** -- The public virtual assistant can answer "Can I afford this?" questions using agentic tool calls. When a prospect asks about affordability (e.g., "Can I afford a $450,000 home on $80,000/year?"), the AI uses calculation tools to estimate monthly payments, required down payment, debt-to-income ratios, and provides a preliminary assessment. The assistant can also guide prospects through a basic pre-qualification conversation, collecting high-level financial information (income, debts, credit score range, target price) and providing a preliminary assessment of which Summit Cap Financial products they may qualify for. Pre-qualification is non-binding and clearly labeled as such. All calculations are performed via tool calls, not hardcoded responses.

- [ ] **F3: Borrower Authentication and Personal Assistant** -- Authenticated borrowers access a personal AI assistant that knows their identity and can access their application data, loan details, document status, conditions, and rate lock information. The assistant is scoped to the borrower's own data only -- it cannot access any other customer's information. For applications with co-borrowers, both co-borrowers can access the shared application data. Demonstrates per-user RBAC.

- [ ] **F4: Mortgage Application Workflow** -- Borrowers initiate and progress through a mortgage application (modeled on the Uniform Residential Loan Application / 1003 / URLA) via a conversational path where the AI assistant guides the borrower through the process step by step, asking questions, explaining what is needed and why, and collecting information through dialogue. The application collects: personal/financial details (supporting co-borrower entry), property information, employment and income data, assets and liabilities, and consent/disclosure acknowledgment. The conversational path allows borrowers to correct previously provided information without restarting. This is the core agentic AI differentiator -- the AI assistant handles the full application workflow through natural dialogue. **Fallback contingency:** If conversational-only data collection proves too brittle during implementation (unreliable field capture, poor correction handling), a structured form fallback may be introduced for specific application sections while preserving conversational guidance. The conversational path remains the primary and preferred experience.

- [ ] **F5: Document Upload and Analysis** -- Borrowers (and loan officers on their behalf) can upload required documents typical to the mortgage industry. The system processes uploaded documents to extract relevant information (income figures, asset values, identity verification data points, property valuations). Document analysis must never extract demographic data (race, ethnicity, sex); if demographic data is detected in an uploaded document, it is flagged, excluded from extraction, and the exclusion is logged in the audit trail. The system also performs document quality assessment: flagging blurry or unreadable images, incorrect time periods, missing pages, unsigned documents, and other obvious anomalies. Extracted data is associated with the borrower's application. What documents are required is contextual -- it depends on loan type (FHA requires different documents than conventional), employment type (self-employed vs. W-2), and transaction type (purchase vs. refinance). The AI assistant can answer questions about document status ("What documents do I still need to submit?"), explain why each document is needed, and flag potential issues. Document freshness is tracked -- bank statements and pay stubs expire and must be refreshed if they age beyond standard windows. The audit trail logs document upload, processing, extraction results, and any human corrections to extracted values. All audit entries maintain provenance: when the AI cites an extracted value (e.g., "credit score is 720"), the audit trail records the source document. Document version history is maintained when borrowers resubmit.

- [ ] **F6: Application Status and Timeline Tracking** -- Borrowers can see the current status of their application at any time, including pending conditions from underwriting and their rate lock status. The AI assistant can explain what stage the application is in, what is happening at that stage, what the borrower should expect next, estimated timelines, and any outstanding conditions that require their action. The assistant demonstrates awareness of regulatory timing requirements.

- [ ] **F7: Loan Officer Pipeline Management** -- Loan officers see a workspace showing only their assigned applications with multiple view options: by stage, by closing date, by urgency, and stalled files. Urgency factors include: rate lock expirations, approaching closing dates, overdue document requests, outstanding conditions awaiting response, and applications that have stalled without activity. The AI assistant helps with: reviewing application completeness, identifying missing documents or information, summarizing borrower profiles, prioritizing which applications need immediate attention based on deadlines, and conditions management. The loan officer sees only their own pipeline -- not other loan officers' work.

- [ ] **F8: Loan Officer Workflow Actions** -- Loan officers can perform workflow actions on applications in their pipeline: mark documents as reviewed, request additional information from borrowers, add notes and observations, respond to underwriting conditions (uploading supporting documents or explanations), and submit applications to underwriting. The AI assistant can recommend actions ("This application appears complete and ready for underwriting submission") but all state-changing actions require explicit human confirmation via the UI. When submitting to underwriting, the LO can include a cover note and flag any items for the underwriter's attention.

- [ ] **F9: Underwriter Review Workspace** -- Underwriters see all applications in the underwriting pipeline plus read-only visibility into the broader application pipeline. The AI assistant helps with: risk assessment summaries, compliance flag identification, credit analysis, income and asset verification review, property valuation assessment, fraud indicator flagging, and identification of compensating factors when a borrower does not meet a standard guideline. The underwriter has broader data access than loan officers, reflecting the role's need to see the full picture.

- [ ] **F10: Compliance Knowledge Base** -- The underwriter's (and loan officer's) AI assistant has access to a searchable knowledge base containing three document collections organized in a tiered hierarchy:
    1. **Federal and state regulations** -- excerpts from TRID (TILA-RESPA Integrated Disclosure rule), ECOA/Reg B (Equal Credit Opportunity Act), HMDA (Home Mortgage Disclosure Act), Dodd-Frank ATR/QM (Ability to Repay / Qualified Mortgage), FCRA (Fair Credit Reporting Act), BSA/AML awareness, CFPB examination guidelines, and relevant Colorado state lending regulations.
    2. **Agency and investor guidelines** -- fictional but realistic excerpts modeled on Fannie Mae Selling Guide, FHA Handbook 4000.1, and VA Lender's Handbook structures. These are the most frequently referenced documents in daily underwriting.
    3. **Internal Summit Cap Financial overlays** -- internal lending policies, risk thresholds, approval criteria, documentation requirements, exception handling procedures, and compensating factor guidelines. Internal overlays layer on top of agency guidelines.

    The assistant can answer compliance questions, cite specific regulations or guidelines by name, explain the hierarchy (federal regulation overrides investor guideline overrides internal overlay), and flag potential compliance issues in applications. Content must be reviewed by a domain-knowledgeable reviewer before being coded -- incorrect regulatory statements are the highest credibility risk.

- [ ] **F11: Underwriter Decision and Conditions Workflow** -- Underwriters can render four decision types on applications: (1) **Approve** -- clean approval with no additional requirements; (2) **Conditional Approval** -- approved subject to specific conditions that must be satisfied before closing (the most common outcome); (3) **Suspend** -- insufficient information to make a decision, specific items needed before the file can be reconsidered; (4) **Deny** -- application does not meet lending criteria. For conditional approvals and suspensions, the underwriter specifies conditions (with AI assistance in drafting conditions that reference applicable guidelines). Conditions are tracked as individual items with status (issued, responded, under review, cleared, waived). The file returns to the loan officer for conditions clearing and can loop back to the underwriter for re-review -- this iterative loop is the most common and time-consuming part of the workflow. For denials, the AI assistant drafts an Adverse Action Notice as required by ECOA Reg B and FCRA, specifying the specific reasons for denial. The borrower must receive the adverse action notice. All decisions, conditions, and rationale are captured in the audit trail with full decision traceability.

- [ ] **F12: CEO Executive Dashboard** -- The CEO sees an aggregate dashboard showing key business metrics: total pipeline volume and value, applications by stage, pull-through rate (applications started vs. closed), turn times broken down by stage (not just overall average), denial rate with top denial reasons, product mix distribution across the six mortgage products, loan officer workload and performance comparison, rate lock pipeline and approaching expirations, and risk distribution summaries. Fair lending metrics are included: approval/denial rates broken down by HMDA demographic segments for disparate impact monitoring. This is a visual dashboard, not just a chat interface.

- [ ] **F13: CEO Conversational Analytics** -- The CEO has an AI assistant that can answer drill-down questions about the business data shown on the dashboard. Examples: "How many loans does James have in underwriting?", "What is our pull-through rate this quarter vs. last?", "Show me turn times for the conditions clearing stage", "What percentage of applications are denied and what are the top reasons?", "Are there any disparate impact concerns in our denial rates?", "Show me our product mix -- are we heavy on any one product type?" The assistant can access the same data that powers the dashboard to provide specific answers.

- [ ] **F14: Role-Based Access Control** -- Users authenticate against a real identity provider that manages user identities, roles, and sessions. Each persona has a distinct access boundary enforced by the system. The same underlying data exists, but each role sees only what they are authorized to see:
    - **Prospect:** No customer data. Public mortgage product information only.
    - **Borrower:** Own application data, own documents, own conditions, own conversation history, own rate lock status only. Co-borrowers share access to the same application.
    - **Loan Officer:** Own pipeline of assigned applications only. No access to other loan officers' pipelines. No audit trail access. Full document access for applications in their pipeline.
    - **Underwriter:** Full application pipeline (read-write for underwriting queue, read-only for origination pipeline). Access to the in-app audit trail. Full PII visibility for applications under review. Full document access.
    - **CEO:** Aggregate data with drill-down to individual deals. Partial PII (borrower names visible; sensitive fields such as SSN, full account numbers, and date of birth are masked). Document metadata only (document type, upload date, status, quality flags) -- the CEO cannot view or download raw document content. Access to the in-app audit trail (with same partial PII masking applied to audit entries). Access to fair lending / disparate impact metrics.

    RBAC is enforced both at the application level (API/data layer) and at the agent level (the AI assistant's available tools and data access are scoped to the user's role). Agent security includes: input validation on agent queries to detect and reject adversarial prompts, tool access re-verification at execution time before any tool invocation (not just at session start), and output filtering to prevent out-of-scope data from appearing in agent responses. HMDA demographic data collected during the application process is accessible only to compliance reporting functions -- it is not available to the AI assistants used in lending decisions (see F25). HMDA demographic data isolation applies at every stage: collection, document extraction (see F5), storage, and retrieval. Cross-session memory is isolated per user -- memory storage includes a user identifier as a mandatory isolation key, memory retrieval verifies the requesting user matches the memory owner before returning any data, and memory is never retrieved across user boundaries, even for admin or executive roles (see F19).

- [ ] **F15: Comprehensive Audit Trail** -- Every AI action is logged: queries made, data accessed, tools called, recommendations generated, decisions supported. The audit trail is append-only -- no modification or deletion of entries is permitted. Audit entries include sequential IDs or timestamps with integrity guarantees. Attempted tampering (if detected) is itself logged. The audit trail captures who, what, when, and the full context of each AI interaction. Key capabilities:
    - **Decision traceability:** From any lending decision (approval, conditional approval, suspension, denial), trace backward through every contributing factor: which data points were accessed, which compliance checks were run, which knowledge base entries were cited, what the AI recommended, and what the human decided.
    - **Override tracking:** When a human makes a decision that differs from the AI's recommendation, the divergence is explicitly recorded along with the human's stated reason. These AI-human divergence events are a first-class audit concern.
    - **Data provenance:** When the AI cites a data point (e.g., "credit score is 720"), the audit trail records the source: which document it was extracted from, when it was extracted, and whether a human corrected the extracted value.
    - **Consent and disclosure logging:** When a borrower acknowledges disclosures (Loan Estimate, privacy notice, HMDA notice, equal opportunity notice), the audit trail records the timestamp and the specific disclosures presented.
    - **Export capability:** Audit data can be exported for external analysis. Regulators and auditors need to analyze data in their own tools.

    The audit trail is accessible through a dedicated in-app compliance UI (not only through the developer observability dashboard) where users with appropriate access (CEO and Underwriter roles) can search using three query patterns: (1) **Application-centric** -- all events for a specific application; (2) **Decision-centric** -- all factors contributing to a specific lending decision; (3) **Pattern-centric** -- aggregate queries such as "all denials in past 90 days with AI recommendation for each." Loan Officers, Borrowers, and Prospects do not have audit trail access. Fair lending guardrail violations are flagged and prominently visible. This is critical for demonstrating that agentic AI in regulated industries can be fully accountable and traceable.

- [ ] **F16: Fair Lending Guardrails and Proxy Discrimination Awareness** -- The AI system actively refuses to consider protected characteristics (race, color, religion, national origin, sex, familial status, disability, age, receipt of public assistance) in any lending recommendation or risk assessment. If a user (including employees) asks the AI to factor in protected characteristics, the system refuses and logs the attempt. Beyond explicit bias refusal, the system demonstrates awareness of proxy discrimination: when queries involve facially neutral factors that commonly correlate with protected characteristics (such as geographic filtering by ZIP code or neighborhood), the AI flags the potential fair lending concern and notes that such criteria should be reviewed for disparate impact. This is the hard part of fair lending -- not the explicit refusal (which is straightforward), but the awareness that neutral-seeming criteria can have discriminatory effects. Adversarial testing applies to both fair lending guardrails and RBAC boundaries -- the system must be tested against prompts designed to bypass access controls or extract protected data. Demonstrates responsible AI in a regulated context.

- [ ] **F17: Regulatory Awareness and TRID Disclosures** -- The AI system demonstrates awareness of mortgage lending regulations using correct post-TRID terminology (Loan Estimate, not Good Faith Estimate; Closing Disclosure, not HUD-1). When relevant, it references specific regulatory requirements: TRID disclosure timing (Loan Estimate within 3 business days of application), ECOA/Reg B adverse action timing (within 30 days), ATR/QM requirements for underwriting, HMDA data collection requirements. The system generates Loan Estimate documents at appropriate points in the application process. The Closing Disclosure is generated as a document even though the closing workflow itself is not interactive. Regulatory references do not need to be legally accurate for the PoC, but they must use correct regulation names, correct document names, and correctly attribute which regulation covers which requirement. All regulatory content carries a visible "simulated for demonstration purposes" disclaimer.

- [ ] **F18: AI Observability Dashboard** -- A self-hosted, containerized observability interface that shows traces of all agent interactions. Developers and operators can see: which model handled each query, what tools were invoked, execution timing, token usage, and the full chain of agent reasoning. This is a developer/operator-facing feature, not a customer-facing one.

- [ ] **F19: Cross-Session Conversation Memory** -- Conversations persist across browser sessions on a per-user basis. A borrower can start a conversation, close their browser, return later, and the AI assistant remembers the prior context. The CEO can reference previous analytical discussions. Memory is scoped per-user -- one user's conversation history is never accessible to another user. Memory storage includes a user identifier as a mandatory isolation key. Memory retrieval verifies the requesting user matches the memory owner before returning any data. Memory is never retrieved across user boundaries, even for admin or executive roles. The CEO can see aggregate business data but not individual conversation transcripts from other users. At PoC maturity, cross-session memory is simple per-user conversation persistence; the architecture should note the upgrade path to summarized or semantic memory for production.

- [ ] **F20: Pre-Seeded Demo Data** -- The application includes a demo data set with realistic, pre-populated data that simulates an active lending operation based in Denver, Colorado. Demo data seeding is optional at deployment time: the setup process (F22) supports a configuration flag to deploy with or without pre-seeded data. When deployed with demo data (the default for the Quickstart experience), the application starts with the full seeded data set described below. When deployed without demo data, the application starts with an empty pipeline and clean database -- all features remain functional, but there is no pre-existing data. The application must function correctly in both states: seeded and empty. Recommended seeded volume: 2-3 loan officers (including James Torres), 1-2 underwriters (including Maria Chen), 5-10 active borrower profiles at various application stages (including at least one co-borrower application), and 15-25 historical closed loans for CEO analytics and trend data. When demo data is seeded, this includes: document packages in various states of completeness and quality, loan officer assignments and pipeline distributions across all active borrowers, conditions at various stages (issued, responded, cleared), rate locks with various expiration dates, expected closing dates, historical loan data spanning at least 6 months for meaningful trend analysis, underwriting decisions with rationale (including conditional approvals with conditions and at least 2 denials with adverse action notices), and sample conversation histories. All six mortgage products (30-year fixed, 15-year fixed, ARM, jumbo, FHA, VA) should be represented in both active and historical data. Include realistic interest rates, property values, credit scores, income figures, loan-to-value ratios, and debt-to-income ratios. HMDA demographic data should be included for historical loans to support fair lending / disparate impact analysis on the CEO dashboard. When demo data is seeded, it must be extensive enough to support a thorough demo of all features and appear realistic to someone familiar with the mortgage industry.

- [ ] **F21: Model Routing** -- The system routes queries to different models based on complexity. Simple, factual queries are handled by smaller, faster models. Queries that require tool use, complex reasoning, or multi-step agent workflows are routed to more capable models. This routing is transparent in the observability dashboard but invisible to end users. The routing architecture supports configurable model endpoints.

- [ ] **F22: Single-Command Local Setup** -- A developer can clone the repository and start the full application locally with a single command. The setup process handles all dependencies, starts all required services, and by default seeds the demo data (F20). The setup command supports a flag or configuration option to skip demo data seeding, starting the application with an empty pipeline instead. The application works with any provider that exposes an API compatible with common inference server interfaces. The setup supports both local inference and remote inference endpoints, without defaulting to one over the other. Resource requirements for each configuration must be documented.

- [ ] **F23: Container Platform Deployment** -- The application includes deployment manifests and documentation for running on enterprise container platforms. This includes instructions for connecting to enterprise model serving infrastructure.

- [ ] **F24: Loan Officer Communication Drafting** -- The loan officer's AI assistant can draft communications to borrowers: initial document request checklists, condition explanations (translating underwriting jargon into borrower-friendly language), status updates, missing information notifications, and document resubmission requests. The loan officer reviews and sends -- the AI drafts, the human approves. This is one of the highest-value AI capabilities for the LO persona, saving significant time per application on routine communications.

- [ ] **F25: HMDA Demographic Data Collection** -- During the mortgage application process, the system collects demographic information (race, ethnicity, sex) as required by the Home Mortgage Disclosure Act. This creates the central compliance tension of the application: the system must collect this data for regulatory reporting while simultaneously ensuring it is never used in any lending decision, risk assessment, or AI recommendation. The HMDA data collection step is clearly presented to the borrower with an explanation of why the data is collected, how it will be used (aggregate reporting only), and how it will be protected from lending decisions. HMDA data is stored separately from the lending decision data path and is not accessible to the AI assistants used by loan officers or underwriters for lending analysis. It IS accessible to compliance reporting functions (CEO fair lending dashboard metrics). The coexistence of HMDA collection and fair lending refusal in the same application is one of the most compelling and differentiated aspects of this demo.

- [ ] **F26: Adverse Action Notices** -- When an application is denied, the system generates an Adverse Action Notice as required by ECOA Reg B and FCRA. The AI assistant drafts the notice specifying the specific reasons for denial, referencing applicable guidelines and the data points that contributed to the decision. The underwriter reviews, edits if necessary, and issues the notice. The notice is delivered to the borrower through the application (and in production would be mailed). The adverse action notice, the underlying rationale, and the connection to the AI's analysis are all captured in the audit trail with full decision traceability. This feature demonstrates that AI-assisted lending can maintain the same regulatory notification requirements as traditional lending.

- [ ] **F27: Rate Lock and Closing Date Tracking** -- Rate locks and expected closing dates are first-class data elements throughout the application, not metadata. Each application tracks: whether a rate is locked, the lock date, the lock expiration date, the locked rate and terms, and the expected closing date. These dates drive urgency calculations in the loan officer pipeline (F7) and are visible on the CEO dashboard (F12). The AI assistant can answer questions about rate lock status ("When does Sarah Mitchell's lock expire?", "Which applications have locks expiring this week?") and the system flags approaching expirations as urgent pipeline items.

- [ ] **F28: Document Contextual Completeness** -- What documents are required for a given application is not static -- it depends on loan type (FHA requires upfront mortgage insurance documentation; VA requires Certificate of Eligibility; jumbo loans may require additional asset verification), employment type (self-employed borrowers require 2 years of tax returns and profit/loss statements; W-2 employees require recent pay stubs and W-2s), and transaction type (purchase requires purchase contract and earnest money documentation; refinance requires current mortgage statement and payoff letter). The AI assistant generates a contextual document checklist based on the specific application's characteristics and tracks completeness against that checklist, not a generic list.

- [ ] **F38: TrustyAI Fair Lending Metrics** -- The Compliance Service uses the `trustyai` Python library to compute Statistical Parity Difference (SPD) and Disparate Impact Ratio (DIR) fairness metrics on HMDA-correlated lending outcomes. These metrics power the CEO dashboard's fair lending / disparate impact analysis (F12) and provide quantitative evidence for compliance monitoring beyond simple approval/denial rate comparisons. The library is used as a dependency within the Compliance Service -- no additional containers or infrastructure are required. TrustyAI metrics are computed on aggregate data only, consistent with the HMDA isolation architecture. This demonstrates OpenShift AI ecosystem integration at the algorithmic level.

- [ ] **F39: Model Monitoring Overlay** -- A lightweight monitoring view accessible from the observability dashboard (F18) or CEO dashboard (F12) showing model inference health: latency percentiles per model endpoint, token usage per request, error rates, and model routing distribution. This uses metrics already collected by LangFuse callbacks -- no additional monitoring infrastructure is required. The overlay provides operational visibility into AI system health without the complexity of a full model monitoring platform. At PoC maturity, this is a read-only dashboard panel, not an alerting system.

### Should Have (P1)

- [ ] **F29: Borrower Document Status Dashboard** -- Beyond the AI assistant's ability to answer document questions, provide a visual status view showing which documents have been submitted, which are pending review, which have been accepted, which have quality issues flagged, which need resubmission, and which have expired and need refreshing. A structured UI complement to the conversational interface.

- [ ] **F30: Underwriter Compliance Checklist** -- A structured checklist view that shows which compliance requirements have been satisfied for a given application and which remain outstanding. Each checklist item is linked to the specific regulatory citation or internal policy reference that requires it (e.g., "Loan Estimate delivered within 3 business days -- TRID 12 CFR 1026.19(e)"). Complements the AI assistant's conversational compliance capabilities with a visual, scannable format.

- [ ] **F31: CEO Trend Analysis** -- The CEO's AI assistant can identify and explain trends in the data over time: "Application volume is up 15% month-over-month", "Pull-through rate has declined from 72% to 65% this quarter", "Average turn time in conditions clearing has increased by 3 days", "Time-to-close has improved since last month." Requires sufficient pre-seeded historical data to demonstrate trends.

- [ ] **F32: Application Comparison for Underwriters** -- The underwriter's AI assistant can compare two or more applications side-by-side, highlighting differences in risk profiles, income levels, property values, and compliance status. Useful for calibrating decisions and identifying outlier applications.

- [ ] **F33: Fraud and Anomaly Indicators** -- The underwriter's AI assistant flags potential fraud indicators and suspicious anomalies in application data and documents: income figures that do not match across documents, property values that seem inconsistent with comparable properties, employment that cannot be verified, documents with metadata anomalies, and other red flags that experienced underwriters look for. The AI provides the flag and the evidence -- the underwriter investigates. All flags are logged in the audit trail. This is an advisory capability, not a determination.

### Could Have (P2)

- [ ] **F34: Borrower Notification Preferences** -- Borrowers can configure how they want to be notified of status changes and document requests (email, SMS, in-app). For the PoC, this could be simulated rather than actually sending notifications.

- [ ] **F35: Rate Lock Management** -- The AI assistant can explain rate lock concepts, answer "should I lock?" questions with market context from pre-seeded rate data, and simulate locking a rate for a borrower's application, showing how rate changes would affect their payment and total loan cost. LO and borrower perspectives are both supported.

- [ ] **F36: Property Valuation Insights** -- The AI assistant can provide context about property values in a given area based on pre-seeded market data, helping both borrowers understand their property's position and underwriters assess collateral adequacy.

- [ ] **F37: Multi-Language Support** -- The public virtual assistant can interact in multiple languages, demonstrating the AI's multilingual capabilities. Not a core requirement but a compelling addition for the financial services audience.

### Won't Have (This Phase)

- **Real external system integrations** -- No connections to actual credit bureaus, MLS systems, AUS (automated underwriting systems like Desktop Underwriter or Loan Product Advisor), government databases, or notification services. All data is self-contained and pre-seeded or simulated. In production, applications would run through AUS before human underwriting review; this step is simulated via pre-seeded AUS-style findings in the demo data.
- **Real payment processing** -- No actual financial transactions.
- **BSA/AML/KYC** -- BSA (Bank Secrecy Act), AML (Anti-Money Laundering), and KYC (Know Your Customer) requirements are acknowledged in the compliance knowledge base as applicable regulations, but the system does not implement identity verification, suspicious activity reporting, or customer due diligence workflows. These are critical in production but require external system integrations (FinCEN, identity verification services) that are out of scope for a self-contained Quickstart.
- **Loan Processor persona** -- Processor duties are absorbed into the Loan Officer role. See Persona Gap section above.
- **Closing and servicing workflows** -- The mortgage lifecycle data includes "closing" and "servicing" stages for pipeline completeness (visible in the CEO dashboard and status tracking). The Closing Disclosure document is generated (F17) but there are no interactive workflows for closing signing, funding, payment processing, escrow management, or loan servicing operations. These stages exist as data states, not as featured experiences.
- **Mobile-native applications** -- Web-only. Responsive design is acceptable but native mobile apps are out of scope.
- **Multi-tenant / multi-institution** -- The Quickstart represents a single fictional bank. Multi-tenancy is not needed.
- **Production security hardening** -- This is a PoC. Secrets are not production-managed, and network security is minimal. While the application uses real authentication via an identity provider, the overall security posture is not production-hardened.
- **Automated underwriting decisions** -- All decisions require human confirmation. The AI advises, the human decides. AUS integration would be the first external system to add in a production path.
- **Real regulatory compliance** -- Disclosures and regulatory references are realistic but not legally accurate. This is a demonstration, not a compliance-certified system. All regulatory content carries a "simulated for demonstration purposes" disclaimer.
- **Location-aware personalization** -- Contextual enrichment based on user location (weather, local market data) is not designed for but could be added later as a tool call.
- **Third-party service ordering** -- In production, title searches and property appraisals are ordered from third-party vendors (title companies, AMCs) through integrations. In the Quickstart, these are simulated as pre-seeded data (appraisal report already exists in the document package).
- **Investor/secondary market operations** -- Loan sale to investors, servicing-released vs. servicing-retained decisions, warehouse line management, and investor relationship management are not in scope. The CEO dashboard references pipeline value and product mix but does not include margin per loan, warehouse line utilization, or investor delivery tracking.
- **Loan program eligibility engine** -- Complex eligibility rules (VA COE requirements, FHA county loan limits, jumbo minimum thresholds) are referenced in the compliance knowledge base and the AI can discuss them conversationally, but there is no deterministic eligibility engine that automatically validates a borrower against every program rule.
- **Realtor and third-party coordination** -- Communication with realtors, title companies, appraisers, and other third parties is a significant part of the LO's work but is out of scope for this PoC.
- **Document retention policies and automated purging** -- Documents persist for the lifetime of the demo environment. Production retention policies, automated purging, and borrower data deletion workflows are out of scope for the PoC.

## User Flows

### Flow 1: Prospect Explores Mortgage Options and Pre-Qualifies (Public Website)

1. Visitor arrives at the Summit Cap Financial public website
2. A chat widget is visible -- visitor opens it and sees a welcome message introducing the virtual assistant
3. Visitor asks: "What kinds of mortgages do you offer?"
4. Assistant responds with Summit Cap Financial's six mortgage products (30-year fixed-rate, 15-year fixed-rate, adjustable-rate, jumbo, FHA, and VA loans) using only approved product information, with brief descriptions of who each product is best suited for
5. Visitor asks: "Can I afford a $450,000 home if I make $80,000 a year?"
6. Assistant invokes an affordability calculation tool, estimates monthly payment (including taxes, insurance, PMI), calculates debt-to-income ratio, and provides a preliminary assessment with caveats
7. Visitor asks: "Could I pre-qualify?"
8. Assistant explains that pre-qualification is a non-binding preliminary assessment and asks a series of questions: approximate credit score range, annual income, monthly debts, target home price, and desired down payment
9. Based on the responses, the assistant provides a preliminary product recommendation and estimated qualification range: "Based on what you have shared, you may qualify for a conventional 30-year fixed-rate mortgage in the $380,000-$430,000 range. This is a preliminary assessment only -- a full application with documentation would be needed to confirm."
10. Visitor asks: "What about Bitcoin -- is that a good investment?"
11. Assistant politely declines: "I can only help with Summit Cap Financial's mortgage products. For investment advice, please consult a licensed financial advisor."
12. Visitor asks: "How do I apply?"
13. Assistant explains the application process and provides a link to create an account

### Flow 2: Borrower Applies via Conversational AI (Authenticated)

1. Sarah Mitchell logs into her Summit Cap Financial account
2. She sees her personal dashboard and opens the AI assistant to start a new application.
3. She tells the assistant: "I want to apply for a mortgage"
4. Assistant begins the guided application process, asking for property information, financial details, and employment history -- conversationally, not as a rigid form. The assistant notes this is a sole-borrower application (or asks if there is a co-borrower).
5. At each step, the assistant explains why the information is needed and what will happen next
6. Sarah realizes she entered her income incorrectly three questions back. She says "Actually, my salary is $85,000, not $82,000." The assistant corrects the previously captured value and confirms the change.
7. Assistant reaches the HMDA data collection step. It explains: "Federal law (HMDA) requires us to collect demographic information including race, ethnicity, and sex for aggregate reporting purposes. This information is not used in any lending decision and will not be shared with anyone evaluating your application. You may decline to provide this information."
8. Assistant reaches the disclosure/consent step and presents required disclosures individually (Loan Estimate, privacy notice, equal opportunity notice, HMDA notice), each requiring separate acknowledgment. Timestamps of each acknowledgment are logged.
9. Sarah confirms and the application is created in the system
10. Assistant tells Sarah what documents she needs to upload based on her specific application (loan type, employment type, transaction type) and why each is required
11. Sarah uploads her pay stubs and tax returns
12. System processes the documents, extracts income information, and associates it with her application
13. Assistant confirms: "I have received your 2023 W-2 showing gross income of $85,000. Your last two pay stubs have also been processed. You still need to upload bank statements for the past 2 months."

### Flow 3: Borrower Checks Application Status and Responds to Conditions (Returning Session)

1. Sarah returns to Summit Cap Financial several days later and logs in
2. She opens the AI assistant and asks: "What is the status of my application?"
3. Assistant recalls the prior conversation context (cross-session memory) and responds: "Welcome back, Sarah. Your application has been conditionally approved -- congratulations! There are 3 conditions that need to be satisfied before closing. Two require documents from you: an updated bank statement (your previous one is now more than 60 days old) and a letter explaining a large deposit in your checking account. The third condition is for your loan officer to verify your employment. Would you like me to explain any of these conditions?"
4. Sarah asks: "What do they mean by 'explain the large deposit'?"
5. Assistant explains in plain language: "The underwriter noticed a deposit of $15,000 in your bank statement that is larger than your normal deposits. They need to understand where this money came from -- for example, a gift from a family member, sale of property, or bonus from your employer. This is a standard anti-fraud and source-of-funds verification requirement. You will need to provide a brief written explanation and, depending on the source, a supporting document like a gift letter."
6. Sarah uploads a new bank statement and a gift letter
7. Assistant confirms receipt and processing: "Your updated bank statement and gift letter have been received and processed. These have been sent to your loan officer for review. Once the employment verification is complete, your file will go back to the underwriter for final review."

### Flow 4: Loan Officer Manages Pipeline and Clears Conditions

1. James Torres logs into the employee portal
2. He sees his pipeline dashboard showing his assigned applications with urgency indicators: 2 rate locks expiring within 5 days, 1 application with a closing date in 10 days that still has outstanding conditions, 3 applications waiting on borrower documents
3. He asks his AI assistant: "What needs my attention today?"
4. Assistant reviews his pipeline and responds with urgency-prioritized items: "Urgent: Michael Chen's rate lock expires in 3 days and his file still has 2 outstanding conditions -- I recommend prioritizing his conditions response. Sarah Mitchell's conditions have been responded to by the borrower -- her updated bank statement and gift letter are ready for your review. Two other applications are waiting on borrower documents -- I can draft reminder notices for those borrowers."
5. James reviews Sarah's conditions response. The assistant summarizes: "Sarah uploaded a new bank statement dated January 15 and a gift letter from her mother for the $15,000 deposit. The gift letter appears complete -- donor name, amount, relationship, and statement that no repayment is expected. Shall I prepare the conditions response for underwriting re-review?"
6. James confirms, reviews the AI's prepared response, and submits it. The system presents a confirmation dialog: "Submit conditions response for Sarah Mitchell's application #2024-0847 back to underwriting? This action will be logged." James clicks confirm.
7. James asks the assistant to draft a reminder to the two borrowers with outstanding documents. The assistant drafts personalized notices explaining what is needed and why, translating any underwriting jargon into borrower-friendly language. James reviews, edits one slightly, and sends both.

### Flow 5: Underwriter Reviews Application and Issues Conditions

1. Maria Chen logs into the underwriter portal
2. She sees the underwriting queue with applications awaiting initial review and conditions re-review, plus a read-only view of the broader pipeline
3. She opens a new application and asks her AI assistant: "Give me a risk assessment summary for this application"
4. Assistant analyzes the application data and responds with: credit score assessment, debt-to-income ratio analysis, loan-to-value calculation, employment stability evaluation, ATR/QM compliance check, and an overall risk tier classification. Each factor cites relevant agency guidelines and internal policy thresholds. The assistant notes one potential fraud indicator: "Employment start date on application is 3 years ago, but the employment verification letter references a start date of 18 months ago -- this discrepancy should be investigated."
5. Maria asks: "Are there any compliance concerns?"
6. Assistant queries the compliance knowledge base and responds: "No fair lending flags. TRID Loan Estimate was delivered within 3 business days of application -- timing requirement met. HMDA data was collected. One item: the borrower's DTI ratio is 43%, which exceeds the standard QM threshold of 43%. Under our internal overlay, DTI between 43-45% is allowed with two compensating factors. The borrower has significant cash reserves (6 months PITI) and a long employment history (8 years same employer) -- these may serve as compensating factors."
7. Maria asks: "What does the Fannie Mae Selling Guide say about compensating factors for high DTI?"
8. Assistant searches the agency guidelines tier of the knowledge base and responds with the relevant guideline language
9. Maria decides on a conditional approval. She selects "Conditional Approval" and the assistant helps draft conditions: (1) resolve the employment date discrepancy, (2) provide updated pay stub dated within 30 days of closing, (3) provide evidence of homeowner's insurance. Maria reviews, edits, and confirms. The conditions, rationale, and cited guidelines are stored in the audit trail.

### Flow 5b: Underwriter Denies Application and Generates Adverse Action Notice

1. Maria reviews a different application where the borrower has a credit score of 580, DTI of 52%, and insufficient documentation
2. She asks the AI assistant: "What are the grounds for denial here?"
3. Assistant summarizes: "This application does not meet minimum requirements on multiple criteria: credit score below 620 minimum per internal overlay (580 actual), DTI exceeds maximum allowable ratio even with compensating factors (52% actual, 45% maximum with exceptions), and income documentation is incomplete. Under ECOA Reg B, the specific reasons must be communicated to the applicant."
4. Maria selects "Deny" and the assistant drafts an Adverse Action Notice listing the specific reasons: (1) credit score does not meet minimum requirements, (2) excessive debt-to-income ratio, (3) incomplete income verification. The notice includes required disclosures about the applicant's rights under FCRA and ECOA.
5. Maria reviews, confirms, and the denial decision, adverse action notice, and full rationale are recorded in the audit trail with complete decision traceability.

### Flow 6: CEO Reviews Business Health and Fair Lending Compliance

1. David Park logs into the executive portal
2. He sees the executive dashboard: pipeline volume ($42M across 67 active applications), applications by stage (18 in origination, 23 in underwriting, 15 in closing, 11 in servicing), pull-through rate (68% this quarter), turn times by stage (origination: 5 days avg, underwriting initial review: 3 days, conditions clearing: 8 days, closing: 4 days), denial rate (12% with top reasons), product mix chart, loan officer workload bars, and a fair lending summary widget
3. He asks his AI assistant: "How is James Torres performing this quarter?"
4. Assistant responds: "James Torres has 12 active applications totaling $4.2M in his pipeline. He has closed 8 loans this quarter with an average processing time of 31 days, which is 3 days faster than the team average. His denial rate is 8%, below the company average of 12%. His conditions clearing turn time is 6 days, 2 days faster than the team average."
5. David asks: "What is our pull-through rate and how does it compare to last quarter?"
6. Assistant responds with current pull-through figures, quarter-over-quarter comparison, and identifies the stage where most fallout occurs
7. David asks: "Are there any fair lending concerns I should know about?"
8. Assistant queries the HMDA reporting data and responds: "Looking at denial rates by demographic segment for the past 6 months: overall denial rate is 12%. I am flagging one area for review -- denial rates for Hispanic applicants are 18% compared to 10% for non-Hispanic white applicants. The sample size is small (11 Hispanic applicants), so this may not be statistically significant, but it warrants monitoring. The most common denial reason across all groups is excessive DTI."
9. David asks: "Show me our top 5 largest pending applications"
10. Assistant provides a summary table of the five largest applications by loan amount, including borrower name, stage, loan officer, risk assessment, and rate lock status. Sensitive borrower fields (SSN, account numbers) are not shown -- the CEO sees operational detail (names, amounts, stages) without sensitive PII.

### Flow 7: Audit Trail Review (CEO or Underwriter)

1. David Park (CEO) or Maria Chen (Underwriter) navigates to the in-app audit trail from their portal -- Loan Officers, Borrowers, and Prospects do not have access to this view
2. They select an audit query type: application-centric, decision-centric, or pattern-centric
3. **Application-centric example:** Maria searches for application #2024-0847 and sees a complete timeline: every AI query, every data access, every document upload and extraction, every recommendation, every condition issued and cleared, every decision, who made it, and when. She can see where the AI flagged the employment date discrepancy, the conditions she issued, and the LO's response.
4. **Decision-centric example:** Maria selects the denial decision on application #2024-0901 and traces backward through every contributing factor: the credit score (extracted from credit report, not corrected by human), the DTI calculation (based on income from W-2 extraction and debts from credit report), the AI's recommendation (deny), and the human's decision (concurred with AI). No override occurred.
5. **Pattern-centric example:** David queries "all denials in past 90 days with AI recommendation." He sees a table showing each denial, whether the AI recommended denial (and the human concurred) or whether the AI recommended a different outcome (override). He can filter by demographic segment for fair lending analysis.
6. Each audit entry includes the full context: the user's question, the AI's response, which tools were invoked, what data was accessed, which model handled the query, and the provenance of any cited data points
7. Fair lending guardrail violations (attempted use of protected characteristics) are flagged and prominently visible
8. The CEO's view of audit entries respects the same partial PII rules as the CEO dashboard -- borrower names visible, sensitive fields masked
9. Audit data can be exported for external analysis

### Flow 8: HMDA Collection and Fair Lending Tension

1. During the conversational application process (Flow 2 step 7), the borrower encounters the HMDA demographic data collection
2. The system presents a clear explanation: "Federal law requires mortgage lenders to collect information about your race, ethnicity, and sex. This information is used only for aggregate reporting to regulators to monitor fair lending practices. It is NOT used in evaluating your application or making any lending decision. You may choose not to provide this information."
3. The borrower provides (or declines to provide) the demographic data
4. Later, when the underwriter (Maria) reviews this application, she asks her AI assistant about risk factors. The AI provides credit, income, employment, and property analysis -- but NEVER references the borrower's demographic data, even though it exists in the system
5. If Maria asks "What is the applicant's race?" the AI refuses: "Demographic information collected under HMDA is not available for lending decisions. It is used only for aggregate fair lending compliance reporting."
6. Meanwhile, on the CEO dashboard (Flow 6), David can see aggregate HMDA statistics for fair lending monitoring -- but only in aggregate, never tied to individual lending decisions
7. This flow demonstrates the core tension: the same system that collects demographic data actively prevents its use in the very decisions that data is meant to monitor

## Open Questions

All previously identified open questions have been resolved with the stakeholder.

| ID | Question | Resolution | Status |
|----|----------|------------|--------|
| OQ-1 | What specific mortgage products should Summit Cap Financial offer? | Six products: 30-year fixed-rate, 15-year fixed-rate, adjustable-rate (ARM), jumbo loans, FHA loans, and VA loans. Incorporated into F1 and F20. | Resolved |
| OQ-2 | Should the CEO be able to see individual borrower PII, or only anonymized/aggregated data? | Partial PII: borrower names are visible for operational context, but sensitive fields (SSN, full account numbers, date of birth) are masked. Incorporated into CEO persona description and F14. | Resolved |
| OQ-3 | How many loan officers, underwriters, and borrowers should the pre-seeded data include? | Enough for a meaningful CEO dashboard but not overwhelming: 2-3 loan officers, 1-2 underwriters, 5-10 active borrowers, 15-25 historical closed loans. Reduced from original 25-30/50-60 to keep demo data crafting feasible within PoC timeline. Incorporated into F20. | Resolved |
| OQ-4 | Should the audit trail be accessible through its own UI within the application, or only through the observability dashboard? | Dedicated in-app compliance UI for the audit trail. Incorporated into F15. | Resolved |
| OQ-5 | What document types beyond the basics should the system recognize? | All document types typically encountered in the mortgage industry: pay stubs, W-2s, tax returns, bank statements, property appraisals, title documents, insurance certificates, gift letters, government ID, employment verification letters, etc. Incorporated into F5. | Resolved |
| OQ-6 | Should the borrower experience include a structured form-based application path in addition to the conversational AI path? | Originally resolved as dual-path. Subsequently revised by stakeholder: conversational-only. The agentic conversational capability is the core differentiator. Form-based path removed from F4. **Updated:** A form fallback contingency is accepted -- if conversational-only proves too brittle during implementation, structured forms may supplement specific application sections. Conversational remains the primary path. | Resolved |

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scope exceeds 3-month delivery window | High | High | Strict MoSCoW enforcement. P0 features deliver first. P1 and P2 features are cut before the deadline slips. Phasing plan below defines clear capability milestones. Phase 4 split into 4a (personas) and 4b (deployment) to reduce single-phase overload. Demo data reduced to 5-10 active borrowers to keep data crafting feasible. F4 has a form fallback contingency. |
| Confidently incorrect regulatory statements | High | High | This is the single highest credibility risk (flagged by 4 of 5 panelists). All compliance knowledge base content must be reviewed by a domain-knowledgeable reviewer BEFORE it is coded, not after. Use correct post-TRID terminology throughout. All regulatory content carries a "simulated for demonstration purposes" disclaimer. Schedule content review as a parallel workstream starting in Phase 1. |
| Document analysis quality is unreliable | Medium | Medium | Use pre-seeded documents with known, predictable content for the demo path. Actual upload/analysis can have lower accuracy expectations as a PoC -- the pattern matters more than perfection. Document quality flags (blurry, wrong period, missing pages) add credibility even when extraction is imperfect. |
| Model routing adds complexity without visible value | Medium | Low | Model routing exists in the architecture and is visible in the observability dashboard, but does not need to be demonstrated to end users. It can be a "behind the scenes" feature that Quickstart users explore. |
| Demo data does not feel realistic to financial services practitioners | Medium | High | Set Summit Cap Financial in Denver, Colorado (US metro, compatible with all 6 loan products). Use realistic names, amounts, timelines, ratios, interest rates, credit scores, and LTV/DTI figures. Include realistic conditions, rate locks, and closing dates. Include HMDA demographic data for historical loans. |
| Cross-session memory leaks data between users | Low | High | Per-user memory scoping is a hard requirement. Memory storage includes a user identifier as a mandatory isolation key. Memory retrieval verifies the requesting user matches the memory owner. Memory isolation must be verified as part of the RBAC demonstration. |
| Single-command setup fails on different environments | Medium | Medium | Support both local inference and remote inference endpoints. Document resource requirements for each configuration. Test on multiple environments. Provide clear prerequisites documentation. Use containerized services to minimize host dependency. |
| Fair lending guardrails are only skin-deep | Medium | High | Go beyond explicit bias refusal to include proxy discrimination awareness (F16). Demonstrate the HMDA collection + fair lending refusal tension (F25). Include disparate impact metrics on CEO dashboard (F12). Test guardrails extensively with adversarial prompts before demo. |
| Conditions workflow adds complexity beyond a simple review-and-decide model | Medium | Medium | The iterative conditions loop (F11) is the most realistic and time-consuming part of the actual workflow. It is also where AI assistance provides the most value (translating conditions, tracking status, drafting responses). Pre-seeded data includes conditions at various stages to demonstrate the loop without requiring live iteration. |
| HMDA data leaks into lending decision path | Medium | High | HMDA demographic data is architecturally separated from the lending decision data path. The AI assistants used by LOs and underwriters cannot access it. Compliance reporting functions (CEO dashboard) access it only in aggregate. HMDA data isolation applies at every stage: collection, document extraction, storage, and retrieval. This separation must be verified as part of RBAC testing. |
| HMDA data leaks into lending decision path via document extraction | Medium | High | Document analysis pipeline must never extract demographic data. If demographic data is detected in an uploaded document, it is flagged, excluded from extraction, and the exclusion is logged in the audit trail. Demographic data filtering in the extraction pipeline must be verified. |
| Adverse action notices contain incorrect regulatory citations | Medium | High | Draft adverse action notice templates with domain reviewer input. The AI drafts based on actual denial factors, but the template structure and regulatory citations must be pre-reviewed. Underwriter always reviews before issuing. |
| Conversational-only application workflow depends on AI quality for data collection | Medium | Medium | The AI must reliably collect all required application fields through dialogue. Pre-seeded demo data provides a reliable demo path. Thorough testing of the conversational flow is essential to ensure all 1003/URLA fields are captured. **Fallback accepted:** If conversational-only proves too brittle, structured forms may supplement specific application sections while preserving conversational guidance as the primary experience. |
| Broad document type coverage increases document analysis complexity | Medium | Medium | Start with the most common types (pay stubs, W-2s, tax returns, bank statements) and add additional types incrementally. Pre-seeded documents for less common types (gift letters, title documents) provide a reliable demo path even if real-time analysis for those types is not yet refined. |
| AI observability tooling adds operational complexity to local setup | Medium | Low | The observability dashboard runs as a container alongside the application. It is included in the single-command setup. |
| Agent prompt injection bypasses RBAC or leaks HMDA data | High | High | Multi-layer defense: input validation on agent queries to detect adversarial prompts, tool-level authorization checks re-verified at execution time before every invocation, output filtering to prevent out-of-scope data in responses, and adversarial testing of both guardrails and RBAC boundaries. |
| CEO bypasses PII masking via raw document access | Medium | High | Document access controls enforced per role: CEO restricted to document metadata (type, upload date, status, quality flags) and masked extracted data only -- cannot view or download raw document content. Underwriter and LO have full document access scoped to their pipeline. |

## Stakeholder-Mandated Constraints

The following technology and platform requirements were explicitly stated by the stakeholder. They are recorded here and passed to the Architect -- they are NOT product decisions.

| Constraint | Source | Notes |
|------------|--------|-------|
| Python 3.11+ | Stakeholder | Language choice for the backend |
| LangGraph | Stakeholder | Agent orchestration framework |
| LangFuse (self-hosted, containerized) | Stakeholder | AI observability -- must run from a container, NOT their cloud service |
| LlamaStack | Stakeholder | Model serving / inference interface |
| FastAPI | Stakeholder | API framework |
| Pydantic 2.x | Stakeholder | Data validation |
| uv | Stakeholder | Python package management |
| Ruff | Stakeholder | Python linting |
| pytest | Stakeholder | Testing framework |
| OpenShift AI for model hosting (production) | Stakeholder | Production model serving infrastructure |
| OpenAI API-compatible endpoints (development) | Stakeholder | Local dev must work with any compatible provider (Ollama, vLLM, etc.) |
| OpenShift / Kubernetes | Stakeholder | Target deployment platform |
| TrustyAI (Python library) | Stakeholder | Fairness metrics (SPD, DIR) for HMDA fair lending analysis in Compliance Service |
| PoC maturity, architected for production growth | Stakeholder | Quality bar: PoC implementation patterns, but structure that supports future hardening |

## Non-Functional Requirements

These are user-facing quality expectations. Implementation-level targets (cache latency, throughput numbers, connection pool sizes) belong in the Architecture.

| NFR | User-Facing Expectation |
|-----|------------------------|
| **Responsiveness** | Chat responses begin appearing quickly enough to feel conversational -- users should not wonder if the system is frozen. Long-running operations (document analysis, complex analytics) should show progress indication. |
| **Setup speed** | A developer unfamiliar with the project can run the full application locally within 10 minutes of cloning the repository, assuming prerequisites are installed. |
| **Demo stability** | The application runs reliably through a complete demo walkthrough of all 5 personas without crashes, errors visible to the user, or data inconsistencies. Pre-seeded demo documents produce consistent, correct extraction results. |
| **Data isolation** | A user never sees another user's data, conversations, or application details unless their role explicitly grants that access. RBAC violations are never visible in the demo. HMDA demographic data is never accessible to lending decision AI assistants. |
| **Audit completeness** | Every AI interaction is traceable in the audit trail. There are no "gaps" where an AI action occurred but was not logged. Decisions are traceable backward through every contributing factor. Audit entries are append-only and tamper-evident. |
| **Observability clarity** | A developer viewing the observability dashboard can understand which model handled a query, what tools were called, and how long each step took -- without needing to read source code. |
| **Document processing feedback** | When a user uploads a document, they receive clear feedback about whether it was accepted, what was extracted, whether quality issues were detected (blurry, wrong period, missing pages), and whether anything needs attention -- within a timeframe that does not disrupt their workflow. |
| **Memory coherence** | When a user returns to a previous conversation, the AI's recall of prior context is accurate and relevant -- not confusing or contradictory. |
| **Regulatory accuracy** | Regulation names, document names, and regulatory attributions are factually correct (TRID not "RESPA disclosure"; Loan Estimate not GFE; correct regulation cited for each requirement). Content quality is the domain -- not legal compliance, but getting the names and attributions right. |
| **Extensibility clarity** | A Quickstart user can understand from the documentation how to add a new persona, add a new document type, update the compliance knowledge base, or swap a model endpoint -- without reading all the source code. |

## Downstream Notes for Architecture and Implementation

The following items were raised during the panel review and are relevant to the Architect, Tech Lead, or other downstream agents -- they are NOT product scope decisions, but they should inform the architecture and technical design.

### Architecture-Critical

These items must influence the architecture design and should be addressed in ADRs or the architecture document.

| Note | Source | Relevant To |
|------|--------|-------------|
| RBAC must be enforced at the API layer, not just the frontend. Frontend-only RBAC is a critical credibility failure. | Angela Torres (Panelist 3) | Architect, Security |
| HMDA data separation must be a first-class architectural boundary -- two fundamentally different data access paths, not just access control rules. | Patricia Reeves (Panelist 1), Security Review | Architect, Security |
| LlamaStack has a smaller ecosystem and is less battle-tested. Abstractions must not leak into business logic. Isolate behind interfaces. | Angela Torres (Panelist 3) | Architect |
| PII in uploaded documents must be handled consistently with the RBAC model -- if the CEO cannot see SSN in structured data, they should not be able to see SSN in a raw uploaded document either. Document access controls per role are specified in F14. | Patricia Reeves (Panelist 1), Security Review | Architect, Security |
| Document upload/analysis (F5), rate lock/closing date tracking (F27), and document contextual completeness (F28) have overlapping document/data tracking concerns. The architecture should define a single data model for the document lifecycle that satisfies all three features. | Orchestrator Review | Architect |
| Agent logic should be separated from domain logic. Domain should be injectable via configuration, tools, and knowledge bases. Configuration-driven agent definitions (YAML/config) rather than scattered code. | Angela Torres (Panelist 3) | Architect, Tech Lead |
| Compliance knowledge base should be cleanly abstracted as a RAG pipeline, not hardcoded into prompts. This makes it enormously valuable for adopters who want to swap in their own compliance content. | Angela Torres (Panelist 3) | Architect |
| CEO analytics queries should not be tightly coupled to the mortgage schema. If domain replacement requires a schema migration, the Quickstart loses extensibility value. | Angela Torres (Panelist 3) | Architect |
| Frontend stack is unspecified. 5 distinct UIs with no framework decision. SSR vs SPA matters for setup complexity and developer experience. | Angela Torres (Panelist 3) | Architect |
| Hardware/resource requirements must be specified for both local inference and remote inference configurations. Document prerequisites for each. | Angela Torres (Panelist 3) | Architect, DevOps |
| Consider OpenShift AI platform differentiation: model serving integration, namespace isolation mirroring application RBAC, data science pipeline for knowledge base building. | Marcus Webb (Panelist 4) | Architect, DevOps |
| Stakeholder requires real authentication via a production-grade identity provider (Keycloak suggested). The Architect should evaluate and select the appropriate identity provider. This is a stakeholder technology preference, not a product-level technology mandate. | Stakeholder | Architect, Security |

### Informational

These items inform documentation, demo preparation, or later phases but do not constrain the architecture.

| Note | Source | Relevant To |
|------|--------|-------------|
| "Build Your Own Persona" tutorial showing how to add a 6th persona (Loan Processor is the natural example) would be a high-value Quickstart addition. | Angela Torres (Panelist 3) | Technical Writer (post-launch) |
| Honest documentation about what is real vs. simulated (AUS integration, external credit pulls, identity verification, etc.) builds more trust than pretending everything is production-grade. | Angela Torres (Panelist 3) | Technical Writer |
| "Before vs. after" narrative for each persona flow helps demo audience calculate business value without having to figure it out themselves. | Marcus Webb (Panelist 4) | Technical Writer (demo documentation) |
| Consider "Day Two" story in documentation: what happens when you add products, update regulations, add roles. Shows the Quickstart has a life beyond the initial demo. | Marcus Webb (Panelist 4) | Technical Writer |
| Demo reliability: pre-warm models, use streaming for perceived responsiveness, have fallback strategy for LLM latency, use blessed documents for demo path, test guardrails extensively with adversarial prompts. | Marcus Webb (Panelist 4) | Tech Lead, DevOps |
| Model risk management (SR 11-7) should be referenced in the compliance knowledge base as a concept the system is aware of, even though full model governance is out of scope. | Patricia Reeves (Panelist 1) | Content (compliance knowledge base curation) |

## Phasing

### Phase 1: Foundation and Public Experience

**Capability milestone:** The system has a running backend with authentication, role-based access control (including agent-level security with input validation, tool access verification, and output filtering), and the HMDA data separation architecture. A public website with a guardrailed virtual assistant can answer mortgage questions, perform affordability calculations, and walk prospects through pre-qualification. Pre-seeded demo data exists for all personas across all six mortgage products. The observability dashboard is running and showing agent traces. Single-command local setup is functional. Model routing is operational.

**Features included:** F1 (Public Virtual Assistant with Guardrails), F2 (Prospect Affordability and Pre-Qualification), F14 (Role-Based Access Control), F18 (AI Observability Dashboard), F20 (Pre-Seeded Demo Data), F21 (Model Routing), F22 (Single-Command Local Setup), F25 (HMDA Demographic Data Collection)

**Key risks:**
- RBAC architecture must be correct from the start -- retrofitting access control is expensive. HMDA data separation must be built into the data architecture from day one.
- Agent security (input validation, tool access re-verification, output filtering) must be part of the RBAC foundation, not bolted on later.
- Pre-seeded data schema must accommodate all phases including conditions, rate locks, HMDA data, and adverse action notices. The schema and application must function correctly in both seeded and empty states -- dashboards, pipelines, and AI assistants must handle empty data gracefully.
- Compliance knowledge base content curation should begin as a parallel workstream during this phase.
- Compliance knowledge base storage and retrieval architecture should be included in the foundation even though F10 is delivered in Phase 3 -- the RAG pipeline infrastructure is needed early.
- Single-command setup must be maintained as new services are added in later phases.

### Phase 2: Borrower Experience and Document Processing

**Capability milestone:** An authenticated borrower can start a mortgage application via conversational AI, with HMDA demographic data collection demonstrating the collection-without-use tension. The borrower can track application status, upload documents with quality assessment and contextual completeness checking, and receive document extraction feedback. Cross-session memory allows borrowers to return and resume conversations. Rate locks and closing dates are tracked as first-class data elements. The audit trail is capturing all AI interactions with decision traceability, override tracking, data provenance, and append-only immutability.

**Features included:** F3 (Borrower Authentication and Personal Assistant), F4 (Mortgage Application Workflow), F5 (Document Upload and Analysis), F6 (Application Status and Timeline Tracking), F15 (Comprehensive Audit Trail), F19 (Cross-Session Conversation Memory), F27 (Rate Lock and Closing Date Tracking), F28 (Document Contextual Completeness)

**Key risks:**
- Conversational-only application workflow depends on AI quality for data collection -- the AI must reliably capture all required 1003/URLA fields through dialogue. Form fallback contingency accepted if conversational-only proves too brittle.
- Document analysis must enforce demographic data exclusion from extraction (F5 + F25 tension).
- Audit trail append-only immutability must be designed correctly from the start.
- Document quality assessment and contextual completeness expand the scope of document processing.

### Phase 3: Loan Officer Experience

**Capability milestone:** Loan officers have a dedicated workspace showing their pipeline with urgency-based prioritization (rate lock expirations, stale files, condition deadlines). The AI assistant helps manage applications, draft borrower communications, and prepare files for underwriting. Workflow transitions are functional with human-in-the-loop confirmation.

**Features included:** F7 (Loan Officer Pipeline Management), F8 (Loan Officer Workflow Actions), F24 (Loan Officer Communication Drafting)

**Key risks:**
- Loan officer pipeline view must enforce RBAC (only their own applications) while the data model supports the underwriter's broader view in Phase 4a.

### Phase 4a: Underwriting, Compliance, and Executive Experience

**Capability milestone:** The full mortgage lifecycle is functional from application through underwriting decision including iterative conditions clearing. Underwriters have a compliance-aware AI assistant backed by a three-tier knowledge base (regulations, agency guidelines, internal overlays) that supports risk assessment and compensating factor identification. TrustyAI fairness metrics (SPD, DIR) are integrated into the Compliance Service for HMDA fair lending analysis. Adverse action notices are generated for denials. The CEO has an executive dashboard with conversational drill-down analytics, fair lending / disparate impact monitoring, and a lightweight model monitoring overlay showing inference latency and token usage. All five persona experiences are complete. Fair lending guardrails with proxy discrimination awareness are active and demonstrable. The HMDA collection + fair lending refusal tension is fully demonstrable. Regulatory awareness is visible throughout using correct post-TRID terminology.

**Features included:** F9 (Underwriter Review Workspace), F10 (Compliance Knowledge Base -- three-tier), F11 (Underwriter Decision and Conditions Workflow), F12 (CEO Executive Dashboard), F13 (CEO Conversational Analytics), F16 (Fair Lending Guardrails and Proxy Discrimination Awareness), F17 (Regulatory Awareness and TRID Disclosures), F26 (Adverse Action Notices), F38 (TrustyAI Fair Lending Metrics), F39 (Model Monitoring Overlay)

**Key risks:**
- Compliance knowledge base quality depends on curating appropriate source material across three tiers (regulatory excerpts, agency guideline excerpts, and fictional internal policies). Content must be domain-reviewed before coding.
- The CEO dashboard requires sufficient pre-seeded historical data with HMDA demographic data to make fair lending analysis meaningful.
- Adverse action notice templates must be pre-reviewed for correct regulatory language.
- The conditions workflow creates a multi-step loop between personas (borrower, LO, underwriter) that is more complex than a linear workflow.

### Phase 4b: Container Platform Deployment

**Capability milestone:** Container platform deployment is ready. The system is ready for the Summit demo and Quickstart release. All services run on OpenShift with model serving via KServe/vLLM. Deployment manifests and documentation are complete.

**Features included:** F23 (Container Platform Deployment)

**Key risks:**
- Integration issues may surface when moving from Docker Compose to OpenShift deployment.
- Model serving latency on the target platform must be validated against demo responsiveness requirements.

### Phase 5: Demo Polish and Hardening

**Capability milestone:** The application is polished, stable, and reliable enough for a live Summit demo. All rough edges are smoothed, error handling is robust for the demo path, pre-seeded data and documents produce consistent results, and the end-to-end walkthrough is rehearsed and reliable.

**Features included:** No new features. This phase is dedicated to integration testing, demo rehearsal, performance tuning for the demo path, and fixing issues discovered during end-to-end testing.

**Key risks:**
- Bugs discovered during end-to-end testing may require changes across multiple phases' work.
- Demo reliability depends on model serving stability and latency.

### Phase 6: Additive Features (If Time Permits)

**Capability milestone:** The application includes additional features that enhance realism, expand persona capabilities, and demonstrate broader AI capabilities. These features are valuable but not essential for the core demo or Quickstart.

**Features included:** F29 (Borrower Document Status Dashboard), F30 (Underwriter Compliance Checklist), F31 (CEO Trend Analysis), F32 (Application Comparison for Underwriters), F33 (Fraud and Anomaly Indicators), F34 (Borrower Notification Preferences), F35 (Rate Lock Management), F36 (Property Valuation Insights), F37 (Multi-Language Support)

**Key risks:**
- This phase is explicitly designed to be the cut line. If earlier phases run long, features in this phase are cut. All P1 and P2 features are collected here so they can be cleanly identified and deprioritized as a group.
- Within this phase, P1 features (F29-F33) should be prioritized over P2 features (F34-F37) if partial delivery is possible.

## RICE Scoring Reference

The following RICE scores informed the MoSCoW classification above. "Reach" is evaluated against both demo viewers and Quickstart users. "Impact" reflects how much the feature contributes to the project's dual purpose (Summit demo + developer Quickstart). Features that were highlighted by multiple panelists as credibility-critical received confidence boosts.

| Feature | Reach | Impact | Confidence | Effort | Score | Priority |
|---------|-------|--------|------------|--------|-------|----------|
| F14: RBAC | All users (5) | Massive (3) | High (1.0) | Medium (3) | 5.0 | P0 |
| F25: HMDA Collection + Tension | Demo + QS (4) | Massive (3) | High (1.0) | Medium (3) | 4.0 | P0 |
| F15: Audit Trail + Compliance UI | All users (5) | Massive (3) | High (1.0) | High (5) | 3.0 | P0 |
| F16: Fair Lending + Proxy Awareness | Demo + QS (4) | Massive (3) | High (1.0) | Medium (3) | 4.0 | P0 |
| F26: Adverse Action Notices | Demo + QS (4) | Massive (3) | High (1.0) | Medium (3) | 4.0 | P0 |
| F1: Public Assistant + Guardrails | Demo + QS (4) | High (2) | High (1.0) | Low (2) | 4.0 | P0 |
| F3: Borrower Personal Assistant | Demo + QS (4) | Massive (3) | High (1.0) | Medium (3) | 4.0 | P0 |
| F2: Affordability + Pre-Qualification | Demo + QS (4) | High (2) | High (1.0) | Low (2) | 4.0 | P0 |
| F20: Pre-Seeded Demo Data | All users (5) | Massive (3) | High (1.0) | High (5) | 3.0 | P0 |
| F22: Single-Command Setup | QS + Dev (3) | Massive (3) | High (1.0) | Medium (3) | 3.0 | P0 |
| F18: Observability Dashboard | QS + Dev (3) | High (2) | High (1.0) | Low (2) | 3.0 | P0 |
| F11: UW Decision + Conditions | Demo + QS (4) | Massive (3) | High (1.0) | High (5) | 2.4 | P0 |
| F10: Compliance KB (three-tier) | Demo + QS (4) | Massive (3) | Medium (0.8) | High (5) | 1.9 | P0 |
| F5: Document Upload/Analysis | Demo + QS (4) | Massive (3) | Medium (0.8) | High (5) | 1.9 | P0 |
| F7: LO Pipeline Management | Demo + QS (4) | High (2) | High (1.0) | Medium (3) | 2.7 | P0 |
| F8: LO Workflow Actions | Demo + QS (4) | High (2) | High (1.0) | Medium (3) | 2.7 | P0 |
| F9: Underwriter Workspace | Demo + QS (4) | High (2) | High (1.0) | Medium (3) | 2.7 | P0 |
| F12: CEO Dashboard | Demo + QS (4) | High (2) | High (1.0) | Medium (3) | 2.7 | P0 |
| F13: CEO Analytics | Demo + QS (4) | High (2) | High (1.0) | Medium (3) | 2.7 | P0 |
| F24: LO Communication Drafts | Demo + QS (4) | High (2) | High (1.0) | Low (2) | 4.0 | P0 |
| F4: Application Workflow (conversational) | Demo + QS (4) | High (2) | High (1.0) | Medium (3) | 2.7 | P0 |
| F27: Rate Lock + Closing Date | Demo + QS (4) | High (2) | High (1.0) | Low (2) | 4.0 | P0 |
| F28: Document Contextual Completeness | Demo + QS (4) | High (2) | High (1.0) | Medium (3) | 2.7 | P0 |
| F17: Regulatory Awareness + TRID | Demo + QS (4) | High (2) | Medium (0.8) | Medium (3) | 2.1 | P0 |
| F19: Cross-Session Memory | Demo + QS (4) | High (2) | Medium (0.8) | Medium (3) | 2.1 | P0 |
| F6: Status + Timeline Tracking | Demo + QS (4) | Medium (1) | High (1.0) | Low (2) | 2.0 | P0 |
| F23: Container Deployment | QS (3) | High (2) | High (1.0) | Medium (3) | 2.0 | P0 |
| F21: Model Routing | QS + Dev (3) | High (2) | Medium (0.8) | Medium (3) | 1.6 | P0 |
| F38: TrustyAI Fair Lending Metrics | Demo + QS (4) | High (2) | High (1.0) | Low (2) | 4.0 | P0 |
| F39: Model Monitoring Overlay | QS + Dev (3) | Medium (1) | High (1.0) | Low (2) | 1.5 | P0 |
| F29: Document Status Dashboard | Demo + QS (4) | Medium (1) | High (1.0) | Low (2) | 2.0 | P1 |
| F30: UW Compliance Checklist | Demo + QS (4) | Medium (1) | High (1.0) | Low (2) | 2.0 | P1 |
| F31: CEO Trend Analysis | Demo + QS (4) | Medium (1) | Medium (0.8) | Medium (3) | 1.1 | P1 |
| F32: UW Application Comparison | Demo + QS (4) | Medium (1) | Medium (0.8) | Medium (3) | 1.1 | P1 |
| F33: Fraud + Anomaly Indicators | Demo + QS (4) | Medium (1) | Medium (0.8) | Medium (3) | 1.1 | P1 |
| F34: Notification Preferences | QS (2) | Low (0.5) | Low (0.5) | Medium (3) | 0.2 | P2 |
| F35: Rate Lock Management | QS (3) | Medium (1) | Medium (0.8) | Medium (3) | 0.8 | P2 |
| F36: Property Valuation | QS (2) | Low (0.5) | Low (0.5) | Medium (3) | 0.2 | P2 |
| F37: Multi-Language | Demo (2) | Low (0.5) | Low (0.5) | High (4) | 0.1 | P2 |
