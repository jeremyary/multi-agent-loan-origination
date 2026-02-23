Equivalent demo based on mortgage app. Same core patterns (guardrails, RBAC, model routing) applied to deeper, workflow-connected story.

## Public Website -- Prospect

Same pattern as the original demo - visitor hits Summit Cap Financial's site, asks the virtual assistant about mortgage products. The assistant discusses our six products (30-year fixed, 15-year fixed, ARM, jumbo, FHA, VA), runs an affordability/payment estimation tool, and walks through pre-qualification basics. Ask it about investment advice, competitor rates, or off-topic questions -- it refuses. Tight guardrails.

## Customer -- Sarah Mitchell (Borrower)

Sarah logs in. She has an active mortgage application in progress. Her personal assistant can:

- Tell her what stage her application is in and what's still needed from her
- Accept document uploads through the chat ("Here's my W-2") and confirm processing status
- Answer questions about her specific loan terms, rate lock status, and timeline
- Walk her through providing application data conversationally

She can only see her own application. Ask about another borrower's loan -- RBAC blocks it. Same "customer sees only their own data" pattern from the original demo, but the stakes are higher because it's mortgage PII, not a checking balance.

## Employee -- James Torres (Loan Officer)

James logs in to the employee portal. He sees his pipeline of active applications. His assistant can:

- Prioritize his pipeline by urgency (rate lock expirations, approaching closing dates, stale files)
- Run a document completeness check on an application ("Is Sarah's file ready for underwriting?")
- Draft borrower communications ("Write Sarah a message about her missing paystub")
- Recommend workflow transitions ("This application looks complete -- submit to underwriting?") with manual confirmation

He sees only his own pipeline, not other LOs' work.

## Employee -- Maria Chen (Underwriter)

This is where we go beyond the original demo. Maria reviews applications with an AI assistant backed by a three-tier compliance knowledge base (federal regulations, agency/investor guidelines, internal policies). Her assistant can:

- Flag potential compliance issues and fraud indicators
- Cite compensating factors and regulatory references (correct TRID terminology, ATR/QM rules)
- Draft decision rationale for audit purposes
- All recommendations are advisory -- she makes the final call

She has read-only visibility into the full pipeline. The HMDA tension is the showpiece moment: the system collects demographic data for regulatory reporting while simultaneously refusing to surface it during lending decisions.

## Executive -- David Park (CEO)

David sees aggregate dashboards and has a conversational AI assistant for drill-down:

- "What's our pull-through rate this quarter?"
- "Show me approval rates broken down by demographic segment" (fair lending compliance)
- "How many loans does James have in underwriting?"

Sensitive PII is masked (SSN, DOB, account numbers) but borrower names remain visible for operational context.

## Key Demo Patterns

**Model routing:** The public chatbot's simple Q&A routes to a smaller model, while the underwriter's compliance analysis and CEO's analytical queries route to larger models. Called out explicitly as a pattern.

**RBAC graduation:** The original demo showed RBAC as "you can't see other people's data." Ours shows graduated access levels across a business process -- borrower sees one application, LO sees a pipeline, underwriter sees everything read-only, CEO sees aggregates with PII masking.

**Workflow continuity:** The original demo showed 3 isolated experiences. Ours shows 5 experiences with a real workflow threading through them -- an application moves from borrower to LO to underwriter, with an audit trail tying it all together.

## Live Extensibility Option

After the main walkthrough, the presenter demonstrates that the architecture is genuinely extensible - on-the-fly agent and model routing configuration changes (e.g. `config/agents/*.yaml` or `config/models.yaml`) take effect at new conversation start.

**Recommended demo: add a new tool to an existing agent.**

This segment slots in naturally after the LO demo section. The presenter finishes showing James's pipeline, then transitions to the editor to make the change. Navigating back to the LO workspace after the edit starts a fresh conversation, which picks up the new config automatically.

1. Write ~20 lines of Python: a property tax estimation function for Colorado counties
2. Add 5 lines to `config/agents/lo-assistant.yaml` tool registry with `allowed_roles: ["loan_officer"]`
3. Save the file -- no restart needed
4. Navigate app to LO or other workspace (NEED TO NATURALLY START NEW CONVERSATION, triggering the config reload)
5. As James: "What are the estimated property taxes on Sarah's property?" -- it works
5a. You *could* include LangFuse or audit trail optics, but not sure it's a fit for the intent
10. Log in as Sarah (borrower) and ask the same question -- RBAC blocks it

**Note:** Config hot-reload activates per-conversation, not per-message. The edit must happen between conversations, not mid-chat. The demo flow above handles this naturally -- the presenter leaves the LO workspace to edit code, and returning to it starts a new conversation.

**Alternative demos (same hot-reload mechanism):**
- Add a new language to the public assistant (system prompt edit -- fast but shallow)
- Add a new guardrail (system prompt edit -- same limitation)
- Add the Loan Processor persona (more impressive but too many files for live coding, better as a reader exercise)
