# Setup Context for New Project

This file captures decisions and context from the planning project that the /setup wizard needs but that aren't present in the planning artifacts (product-plan.md, architecture.md, requirements, demo-walkthrough.md, ideas-backlog.md). Read this before or during the brain dump phase.

## Project Identity

- **Project repo name:** multi-agent-loan-origination
- **Financial Institution Name:** Summit Cap Financial
- **Maturity:** Proof-of-Concept (architected for production growth)
- **Domain:** Financial Services -- mortgage lending lifecycle
- **Primary Users:** Red Hat Summit attendees, Quickstart adopters, AI BU stakeholders
- **Compliance:** None (PoC) -- but the application *demonstrates* compliance patterns (HMDA, ECOA, TRID) as part of its purpose
- **Timeline:** ~3 months targeting Red Hat Summit Spotlight

## Org Context

The developer is a Red Hat employee working with the Red Hat AI BU team. Keep Red Hat / OpenShift org-specific domains in settings.local.json -- do not strip them.

## Agent Scaffold Decisions Already Made

These decisions were made during planning in the scaffolding project. Apply them rather than re-asking:

- **Agents removed:** All agents should be kept.
- **Model tier:** Expanded hybrid (Opus for Product Manager, Architect, Tech Lead, Code Reviewer; Sonnet for all others). This is the scaffold default -- no changes needed.

## Technology Stack

Already decided (see architecture.md Section 6 for full detail). If you find anything here conflicts with the pre-existing code in the project, bring it to the user's attention before continuing.

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| AI/Agent Framework | LangGraph |
| Observability | LangFuse (self-hosted) |
| LLM Stack | LlamaStack (model serving abstraction) |
| Model Hosting | OpenShift AI (prod); local or OpenAI API-compatible (dev) |
| Web Framework | FastAPI |
| Data Validation | Pydantic 2.x |
| Database | PostgreSQL 16 + pgvector |
| Frontend | React (Vite), TanStack Router, TanStack Query, shadcn/ui, Tailwind CSS |
| Identity | Keycloak (OIDC) |
| Package Manager | uv (Python), npm/pnpm (frontend -- architect to finalize) |
| Linting/Formatting | Ruff |
| Testing | pytest |
| Container | Podman / Docker |
| Platform | OpenShift / Kubernetes |

