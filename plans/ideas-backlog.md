# Ideas Backlog

Items captured during planning that don't belong in the current product plan but should not be forgotten. These are candidates for future work, blog posts, tutorials, or conference content.

## Build Your Own Persona — Extensibility Exercise

**Source:** Stakeholder panel feedback (Enterprise Solutions Architect suggested configuration-driven agent definitions; VP Mortgage Operations and Loan Originator both flagged the Loan Processor as a missing persona)

**Concept:** Create a guided tutorial or accompanying blog post that walks a developer through adding a 6th persona (Loan Processor) to the Summit Cap Financial Quickstart. This serves dual purposes:

1. **Proves extensibility is real.** The Quickstart claims to be a production-extensible foundation. Walking someone through adding a persona — defining a new role, creating agent tools, configuring RBAC boundaries, connecting to the audit trail — proves that claim concretely.

2. **Addresses the Processor gap honestly.** The product plan explicitly excludes the Loan Processor persona for scope reasons (5 personas is the max for 3 months). This tutorial turns that exclusion into a feature — "here's how you add the persona we left out on purpose."

**Scope of the exercise:**
- Define a new RBAC role (Processor) with appropriate data access (broader than LO, narrower than Underwriter)
- Create agent tools for processor-specific tasks: ordering title/appraisal, chasing conditions, verifying employment, packaging files for underwriting
- Configure the Processor's AI assistant with relevant knowledge base access
- Wire into the existing audit trail
- Add the Processor to the conditions clearing workflow between LO and Underwriter

**Delivery options:**
- Quickstart documentation section ("Extending the Quickstart")
- Standalone blog post on Red Hat Developer
- Conference workshop or lab exercise
- All of the above

**Why it's compelling:** Most Quickstarts are "look but don't touch" — useful for understanding patterns but not for building on. A guided extension exercise transforms Summit Cap Financial from a demo into a platform.

---

## Stakeholder Panel as a Reusable Pattern

**Source:** Observed during product plan review process

**Concept:** The technique of creating domain-persona reviewers (CCO, VP Ops, Enterprise Architect, CTO, Loan Originator) to stress-test a product plan produced exceptionally valuable feedback that the standard Architect + Security Engineer review gate would have missed. This could be formalized as a reusable skill or pattern for the agent scaffold itself.

**What it would look like:**
- A skill that takes a product plan and a domain, then generates 4-5 synthetic stakeholder personas with relevant expertise
- Each persona reviews the plan from their perspective, flagging gaps, credibility risks, and "what would impress me" insights
- Output is a consolidated panel report organized by theme

**Why it matters:** Standard review gates catch technical and security issues. Stakeholder panels catch domain credibility issues, workflow realism gaps, and market fit problems that no amount of architecture review will surface.

---

## Interactive Demo Mode / Golden Path

**Source:** Marcus Webb (Red Hat Partner CTO) — flagged demo reliability as the #1 risk for Summit Spotlight

**Concept:** Build a "demo mode" into the application that provides a scripted, reliable walkthrough of all 5 personas. This is separate from the normal application mode.

**What it would include:**
- Pre-warmed model endpoints (no cold start latency during demo)
- "Blessed" documents with known, deterministic extraction results for the upload flows
- Pre-planted conversation history for the cross-session memory demonstrations (CEO "what did we discuss last time?")
- Scripted query paths with tested, reliable responses for each persona
- Fallback paths if a live model response is slow or incorrect
- A presenter's guide with timing notes and transition cues

**Why it matters:** A smooth 12-minute demo with 5 persona transitions has zero margin for latency hiccups, extraction hallucinations, or memory recall failures. The difference between a standing ovation and an awkward silence is preparation infrastructure.

---

## Mortgage Industry Onboarding Guide

**Source:** Observed during panel review — the volume of domain-specific terminology and concepts (1003/URLA, TRID, AUS, DU/LP, conditions loop, compensating factors, warehouse lines, pull-through rate, HMDA LAR) revealed a steep learning curve

**Concept:** Create a developer-facing primer: "How Mortgage Lending Actually Works." Not a regulatory document — a practical guide written for engineers who need to understand the domain they're building for.

**What it would cover:**
- The mortgage lifecycle from prospect to servicing, with the real-world messiness (conditions loop, document chasing, rate lock management)
- Key regulatory framework: TILA, RESPA, TRID, ECOA, HMDA, ATR/QM — what each one does and why developers should care
- Industry terminology glossary (1003, AUS, DU/LP, LTV, DTI, PMI, GFE vs. LE, conditions vs. stipulations, etc.)
- The roles: who does what (LO, processor, underwriter, closer) and how they interact
- Common pitfalls: the geographic inconsistency (Montreal + FHA/VA), using "credit line utilization" instead of "pull-through rate," etc.

**Delivery:** Include in the Quickstart docs. Could also be a standalone blog post.

---

## Compliance Content Authoring Sprint

**Source:** Patricia Reeves (CCO) — "have a domain-knowledgeable reviewer check the compliance knowledge base content BEFORE it's coded, not after"

**Concept:** Schedule a dedicated content authoring sprint during Phase 2 (before Phase 3 underwriting/compliance implementation begins) to create the three-tier compliance knowledge base content:

1. **Regulatory excerpts:** TILA, RESPA/TRID, ECOA, HMDA, ATR/QM, Dodd-Frank, CFPB guidelines — curated, correctly cited, with appropriate "simulated for demonstration" disclaimers
2. **Investor/agency guidelines:** Modeled on Fannie Mae Selling Guide, FHA Handbook 4000.1, VA Lender's Handbook — fictional but structurally realistic
3. **Internal policies:** Summit Cap Financial lending guidelines, risk thresholds, approval criteria, exception procedures

**Who should be involved:** Someone with actual mortgage lending compliance experience — either from the AI BU team, a Red Hat customer in financial services, or an external consultant. A 90-minute working session (as the CCO recommended) would surface the scenarios that make the demo credible.

**Why it matters:** The compliance knowledge base is the foundation of the underwriter experience (F10), fair lending guardrails (F16), and regulatory awareness (F17). If the content is wrong, the entire compliance story collapses regardless of how good the architecture is.

---

## Domain Portability Guide

**Source:** Angela Torres (Enterprise Solutions Architect) — core adoption question was "can I swap mortgage for insurance claims?"

**Concept:** Document which components of the Quickstart are domain-agnostic (reusable patterns) vs. domain-specific (must be rewritten for a new domain). This helps Quickstart adopters estimate the effort to adapt it to their own use case.

**Domain-agnostic (extractable patterns):**
- RBAC framework (role definitions, data boundary enforcement, dual API + agent enforcement)
- Audit trail middleware (immutable logging, decision traceability, override tracking, export)
- Guardrail layer (configurable ethical constraints, refusal + logging pattern)
- Model routing (complexity-based routing to different model endpoints)
- Agent-per-persona architecture (tool scoping, knowledge base access by role)
- Cross-session memory with per-user isolation
- Single-command local setup and container deployment
- Observability integration

**Domain-specific (must be replaced):**
- Agent tool implementations (mortgage calculator, document analysis, compliance queries)
- Knowledge base content (regulatory documents, internal policies)
- Data model (applications, borrowers, properties, documents)
- Seed data
- Agent system prompts and persona definitions
- UI layouts and dashboard metrics

**Delivery:** Section in Quickstart docs titled "Adapting to Your Domain." Could also be a standalone blog post: "From Mortgage Lending to [Your Domain]: How to Customize the AI Banking Quickstart."

---

## Security: Rate Limiting on Authentication Endpoints (Phase 4b)

**Source:** Security Engineer review of Phase 1 TD (SE-W6)

**Concept:** Phase 1 has no rate limiting on API endpoints. Before any non-local deployment, implement rate limiting to prevent brute-force token scanning and authentication bypass attempts.

**Recommended approach:**
- fastapi-limiter with Redis backend (Redis already in stack for LangFuse)
- 100 requests/minute per IP for authenticated endpoints
- 10 requests/minute per IP for auth failures
- Log rate-limit events for incident detection

**Phase:** 4b (Container Platform Deployment)

---

## Security: Config-Driven Tool Authorization Registry (Phase 2)

**Source:** Security Engineer review of Phase 1 TD (SE-W7)

**Concept:** Phase 1 tool authorization registry (`TOOL_AUTHORIZATION` dict) is hardcoded in Python with a config-loading function defined but unused. Before agents are introduced in Phase 2, the registry should load from `config/agents/*.yaml` at module import time, with the hardcoded dict as fallback only.

**Recommended approach:**
- Initialize `TOOL_AUTHORIZATION` by loading from config on module import
- Fallback to hardcoded dict only if config files are missing (with loud warning log)
- Add test: verify modifying a YAML config changes authorization behavior

**Phase:** 2 (Borrower Experience)

---

## Red Hat Developer Blog Series

**Source:** Synthesis of panel feedback — each panelist highlighted different aspects that are independently compelling technical stories

**Concept:** A multi-part blog series on Red Hat Developer that uses Summit Cap Financial as a case study for agentic AI patterns in regulated industries. Each post is standalone but links to the Quickstart.

**Proposed posts:**
1. "RBAC Patterns for Agentic AI: Lessons from Building a Multi-Persona Financial Services App" — the five-persona RBAC model, dual enforcement (API + agent), PII masking by role
2. "The HMDA Tension: Collecting Demographics While Refusing to Discriminate" — the most compelling fair lending architecture challenge, how to design data separation
3. "Audit Trails for AI in Regulated Industries: Beyond Event Logging" — decision-centric traceability, override tracking, data provenance, the three query patterns
4. "Model Routing on OpenShift AI: Right-Sizing Inference for Agentic Workflows" — complexity-based routing, cost optimization, the observability story
5. "Building a Compliance Knowledge Base with RAG: Three-Tier Regulatory Architecture" — regulations, investor guidelines, internal policies as separate document collections
6. "From Demo to Platform: Making a Quickstart Genuinely Extensible" — configuration-driven agent definitions, the "Build Your Own Persona" exercise, domain portability

**Why it matters:** Drives traffic to the Quickstart, establishes thought leadership, and provides depth that a README cannot. Each post targets a different audience segment (security engineers, ML engineers, compliance teams, architects).

---

## Hands-On Workshop / Lab Format

**Source:** Natural extension of the "Build Your Own Persona" exercise and the Summit showcase context

**Concept:** Transform the Quickstart into a structured 2-3 hour hands-on lab for Red Hat events (Summit labs, partner workshops, customer engagements).

**Lab structure:**
1. **Setup (15 min):** Clone, single-command start, verify all personas are working
2. **Guided exploration (30 min):** Walk through each persona, observe RBAC differences, examine audit trail, trigger a guardrail
3. **Architecture deep-dive (30 min):** Examine agent definitions, model routing config, knowledge base structure, observability traces
4. **Build exercise (60 min):** Add the Loan Processor persona following the guided tutorial
5. **Customization challenge (30 min):** Modify a guardrail, add a new tool to an agent, update the knowledge base, verify in the audit trail

**Delivery options:**
- Red Hat Summit hands-on lab
- Partner enablement workshop
- Customer proof-of-value engagement
- Self-paced online lab (with pre-provisioned OpenShift environment)

**Why it matters:** Labs convert "that was a cool demo" into "I understand how this works and I could build on it." The 2-hour investment creates advocates who go back to their organizations and champion the platform.
