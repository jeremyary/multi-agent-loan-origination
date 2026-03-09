<!-- This project was developed with assistance from AI tools. -->

# Summit Cap Financial -- Multi-Agent Loan Origination

A Red Hat AI Quickstart demonstrating agentic AI applied to the mortgage lending lifecycle. Built for [Red Hat Summit](https://www.redhat.com/en/summit), this reference application showcases multi-agent AI systems on Red Hat AI / OpenShift AI using a realistic, regulated-industry business use case.

Summit Cap Financial is a fictional mortgage lender headquartered in Denver, Colorado. The application covers the process from prospect inquiry through pre-qualification, application, underwriting, and approval -- with five distinct persona experiences sharing a common backend.

**[Documentation Site](https://jeremyary.github.io/multi-agent-loan-origination/)** | [API Docs](http://localhost:8000/docs) (when running)

> **Regulatory disclaimer:** All compliance content (HMDA, ECOA, TRID, ATR/QM, FCRA) is simulated for demonstration purposes and does not constitute legal or regulatory advice.

## Quick Start

### Prerequisites

- Node.js 18+ and pnpm 9+
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Podman and podman-compose
- An OpenAI-compatible LLM endpoint (e.g., LM Studio, vLLM, or OpenAI API key)

### Setup

```bash
# 1. Install all dependencies (Node.js + Python)
make setup

# 2. Configure your environment
cp .env.example .env   # Edit LLM_BASE_URL, LLM_API_KEY, and model names

# 3. Start database + MinIO
make db-start

# 4. Run database migrations
make db-upgrade

# 5. Start development servers (API + UI, with hot reload)
make dev
```

### Development URLs

| Service | URL |
|---------|-----|
| Frontend (Vite) | http://localhost:3000 |
| API Server | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Database | postgresql://localhost:5433 |
| MinIO Console | http://localhost:9091 |

## Architecture

```
packages/
  ui/     React 19 + Vite + TanStack Router/Query + shadcn/ui
  api/    FastAPI + LangGraph agents + SQLAlchemy 2.0 (async)
  db/     PostgreSQL 16 + pgvector + Alembic migrations

Supporting services (via compose.yml):
  PostgreSQL, MinIO (S3), Keycloak (OIDC), LangFuse (observability)
```

### Personas

| Persona | Role | Agent | Key Capabilities |
|---------|------|-------|-----------------|
| Prospect | Unauthenticated | Public Assistant | Product info, affordability estimates |
| Borrower | `borrower` | Borrower Assistant | Application intake, document upload, status tracking, condition response |
| Loan Officer | `loan_officer` | LO Assistant | Pipeline management, application review, communication drafting, KB search |
| Underwriter | `underwriter` | Underwriter Assistant | Risk assessment, compliance checks, condition management, decisions |
| CEO | `ceo` | CEO Assistant | Pipeline analytics, audit trail, decision trace, model monitoring |

### Key AI Patterns

- **Multi-agent orchestration** -- five LangGraph agents with role-scoped tools and RBAC
- **Compliance knowledge base** -- pgvector RAG with tiered boosting (federal > agency > internal)
- **Fair lending guardrails** -- HMDA data isolation, demographic data stored in separate schema
- **Model routing** -- complexity-based routing between fast/capable LLM tiers
- **Comprehensive audit trail** -- hash-chained, append-only audit events with LangFuse correlation
- **PII masking** -- middleware-based masking for CEO role (SSN, DOB, account numbers)
- **Safety shields** -- input/output content filters with escalation detection

## Project Structure

```
summit-cap/
├── packages/
│   ├── ui/              # React frontend (pnpm)
│   ├── api/             # FastAPI backend + agents (uv)
│   └── db/              # Database models + migrations (uv)
├── config/
│   ├── agents/          # Agent YAML configurations
│   └── keycloak/        # Keycloak realm export
├── deploy/helm/         # Helm charts for OpenShift
├── compose.yml          # Local development services
├── Makefile             # Development commands
└── turbo.json           # Turborepo pipeline config
```

## Common Commands

```bash
# Development
make setup              # Install all dependencies
make dev                # Start dev servers (frontend + API with hot reload)
make db-start           # Start database + MinIO containers
make db-upgrade         # Run migrations

# Testing
make test               # Run all tests
cd packages/api && uv run pytest -v   # API tests directly

# Code Quality
make lint               # Lint all packages
cd packages/api && uv run ruff check src/  # Python lint

# Containers
make containers-build   # Build all container images
make run-minimal        # Start default stack (db + minio + api + ui)
make run                # Start full stack (all services)
make run-auth           # Add Keycloak
make run-ai             # Add LlamaStack
make run-obs            # Add observability (LangFuse)
make stop               # Stop all containers
make containers-logs    # View container logs

# OpenShift Deployment
make deploy             # Deploy via Helm
make undeploy           # Remove deployment
make status             # Show deployment status
```

## Environment Configuration

Copy `.env.example` and adjust for your setup. The key settings to change:

```env
# LLM endpoint (LM Studio, vLLM, or OpenAI)
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=not-needed
LLM_MODEL_FAST=qwen3-30b-a3b
LLM_MODEL_CAPABLE=qwen3-30b-a3b
```

See `.env.example` for all available settings (database, auth, safety shields, LangFuse).

## Container Deployment

The `compose.yml` supports multiple profiles for different deployment scenarios:

```bash
# Build images
make containers-build

# Start default stack (db + minio + api + ui)
make run-minimal  # or: podman-compose up -d

# Start full stack (all services)
make run  # or: podman-compose --profile full up -d

# Add individual profiles to the default stack
make run-auth  # + Keycloak
make run-ai    # + LlamaStack
make run-obs   # + Redis + ClickHouse + LangFuse

# Stop all containers
make stop

# Check service status
podman-compose ps
```

## OpenShift / Kubernetes Deployment

```bash
# Deploy to OpenShift
make deploy
```

See the [documentation site](https://jeremyary.github.io/multi-agent-loan-origination/) for deployment details.

## Package Documentation

| Package | README | Key Topics |
|---------|--------|------------|
| API | [packages/api/README.md](packages/api/README.md) | Routes, agents, schemas, WebSocket protocol, testing |
| UI | [packages/ui/README.md](packages/ui/README.md) | Components, routing, state management |
| DB | [packages/db/README.md](packages/db/README.md) | Models, migrations, connection management |

## Testing

```bash
# Run all tests
make test

# Package-specific
cd packages/api && uv run pytest -v          # 1083 tests
cd packages/ui && pnpm test:run              # UI tests
```

| Package | Framework | Location |
|---------|-----------|----------|
| API | pytest | `packages/api/tests/` |
| UI | Vitest + RTL | `packages/ui/src/**/*.test.tsx` |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, TanStack Router/Query, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, LangGraph, SQLAlchemy 2.0 (async), Pydantic 2.x |
| Database | PostgreSQL 16 + pgvector |
| Identity | Keycloak (OIDC) |
| Observability | LangFuse (self-hosted) |
| Object Storage | MinIO (S3-compatible) |
| Deployment | Helm, OpenShift / Kubernetes |
| Build | Turborepo, uv (Python), pnpm (Node.js) |
