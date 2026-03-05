<!-- This project was developed with assistance from AI tools. -->

# Getting Started

This guide walks through running Summit Cap Financial locally. You'll have the full application running in under 10 minutes.

## Prerequisites

Install the following before proceeding:

| Tool | Version | Purpose |
|------|---------|---------|
| **Node.js** | 20+ | Frontend build and runtime |
| **pnpm** | 8+ | Node.js package manager |
| **Python** | 3.11+ | Backend runtime |
| **uv** | Latest | Fast Python package manager |
| **podman** or **docker** | Latest | Container runtime |
| **podman-compose** or **docker compose** | Latest | Multi-container orchestration |

### Local LLM Server (Recommended)

The application requires an OpenAI-compatible LLM endpoint. For local development, install one of:

- **[LM Studio](https://lmstudio.ai/)** -- GUI-based local LLM server (recommended for first-time users)
- **[Ollama](https://ollama.ai/)** -- CLI-based local LLM server

Alternatively, configure the application to use OpenAI's API or another compatible endpoint (see [Configuration](#configuration)).

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/rh-ai-quickstart/mortgage-ai.git
cd mortgage-ai
```

### 2. Install Dependencies

```bash
make setup
```

This command installs Node.js and Python dependencies for all packages in the monorepo.

### 3. Start the Database

```bash
make db-start
```

This starts a PostgreSQL 16 container with pgvector support on port 5433.

### 4. Run Database Migrations

```bash
make db-upgrade
```

This creates all tables, indexes, and database roles required by the application.

### 5. Start Development Servers

You have two options: run services individually or use the full containerized stack.

#### Option A: Development Servers (Fastest)

Start the API and UI in development mode with hot-reload:

```bash
make dev
```

This starts:

- **API** at http://localhost:8000 (FastAPI with auto-reload)
- **UI** at http://localhost:5173 (Vite dev server)

!!! note "Authentication Disabled by Default"
    In development mode, authentication is disabled (`AUTH_DISABLED=true`). You can access all endpoints without a JWT token. To enable Keycloak authentication, see [Running with Authentication](#running-with-authentication).

#### Option B: Full Containerized Stack

Start all services using podman-compose:

```bash
make run
```

This starts:

- **Database** (PostgreSQL 16 with pgvector)
- **API** (FastAPI on port 8000)
- **UI** (Nginx serving production build on port 3000)
- **MinIO** (S3-compatible storage on port 9090)
- **Keycloak** (identity provider on port 8080)
- **LangFuse** (observability on port 3001)
- **Redis, ClickHouse** (LangFuse dependencies)

!!! tip "Compose Profiles"
    The `make run` command uses the `full` profile. See [Compose Profiles](#compose-profiles) for other options.

### 6. Access the Application

| Service | URL | Credentials |
|---------|-----|-------------|
| **UI** | http://localhost:3000 (containerized) or http://localhost:5173 (dev) | N/A (auth disabled by default) |
| **API** | http://localhost:8000 | N/A |
| **API Docs** | http://localhost:8000/docs | N/A |
| **Admin Panel** | http://localhost:8000/admin | `admin` / `admin` |
| **Keycloak** | http://localhost:8080 | `admin` / `admin` |
| **LangFuse** | http://localhost:3001 | `admin@summitcap.dev` / `password` |
| **MinIO Console** | http://localhost:9091 | `minio` / `miniosecret` |

### 7. Configure LLM Endpoint

Create a `.env` file in the project root and configure your LLM endpoint:

```bash
# For LM Studio (default port)
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=not-needed
LLM_MODEL_FAST=qwen2.5-3b-instruct
LLM_MODEL_CAPABLE=qwen2.5-14b-instruct

# For Ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=not-needed
LLM_MODEL_FAST=llama3.2
LLM_MODEL_CAPABLE=llama3.2

# For OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL_FAST=gpt-4o-mini
LLM_MODEL_CAPABLE=gpt-4o
```

!!! warning "Model Selection"
    The application routes queries to two model tiers: `fast` (simple queries) and `capable` (complex reasoning + tools). Both tiers require function calling support. Qwen 2.5 3B and 14B are recommended for local development.

After updating `.env`, restart the API:

```bash
# If using make dev
# (Ctrl+C, then make dev again)

# If using containers
make stop
make run
```

## Compose Profiles

The application uses podman-compose profiles to control which services run:

| Command | Profile | Services |
|---------|---------|----------|
| `make run-minimal` | (none) | Database + API + UI + MinIO |
| `make run-auth` | `auth` | Minimal + Keycloak |
| `make run-ai` | `ai` | Minimal + LlamaStack |
| `make run-obs` | `observability` | Minimal + LangFuse (Redis, ClickHouse, LangFuse) |
| `make run` | `full` | All services |

Use the minimal profile for rapid iteration when you don't need authentication or observability:

```bash
make run-minimal
```

## Running with Authentication

To enable Keycloak authentication:

1. Start the full stack or auth profile:

   ```bash
   make run-auth
   ```

2. Update your `.env` file:

   ```bash
   AUTH_DISABLED=false
   KEYCLOAK_URL=http://localhost:8080
   KEYCLOAK_REALM=summit-cap
   KEYCLOAK_CLIENT_ID=summit-cap-ui
   ```

3. Restart the API (if running via `make dev`):

   ```bash
   # Ctrl+C to stop dev servers
   make dev
   ```

4. Access Keycloak at http://localhost:8080 and log in as `admin` / `admin`.

5. Create test users in the `summit-cap` realm with the following roles:

   | Username | Role | Persona |
   |----------|------|---------|
   | `borrower@example.com` | `borrower` | Borrower |
   | `lo@example.com` | `loan_officer` | Loan Officer |
   | `uw@example.com` | `underwriter` | Underwriter |
   | `ceo@example.com` | `ceo` | CEO |

!!! tip "Pre-configured Realm"
    The application includes a pre-configured Keycloak realm at `config/keycloak/summit-cap-realm.json` with test users and roles. This realm is automatically imported when starting Keycloak via compose.

## Configuration

All configuration is managed via environment variables. The application reads from a `.env` file in the project root. Key configuration options:

### Database

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/summit-cap
COMPLIANCE_DATABASE_URL=postgresql+asyncpg://compliance_app:compliance_pass@localhost:5433/summit-cap
```

### Authentication

```bash
AUTH_DISABLED=true  # Set to false to enable Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=summit-cap
KEYCLOAK_CLIENT_ID=summit-cap-ui
```

### LLM

```bash
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=not-needed
LLM_MODEL_FAST=qwen2.5-3b-instruct
LLM_MODEL_CAPABLE=qwen2.5-14b-instruct
```

### Storage (MinIO / S3)

```bash
S3_ENDPOINT=http://localhost:9090
S3_ACCESS_KEY=minio
S3_SECRET_KEY=miniosecret
S3_BUCKET=documents
S3_REGION=us-east-1
UPLOAD_MAX_SIZE_MB=50
```

### Observability (LangFuse)

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-dev-public
LANGFUSE_SECRET_KEY=sk-lf-dev-secret
LANGFUSE_HOST=http://localhost:3001
```

Leave these unset to disable LangFuse tracing.

## Running Tests

Run all tests across the monorepo:

```bash
make test
```

Run tests for a specific package:

```bash
# API tests
pnpm --filter @*/api test

# UI tests
pnpm --filter @*/ui test

# E2E tests
make test-e2e
```

## Stopping Services

Stop all containers:

```bash
make stop
```

Stop only the database:

```bash
make db-stop
```

## Troubleshooting

### Port Already in Use

If you see "port already in use" errors, another service may be occupying the required ports. The application uses:

- **5433** -- PostgreSQL
- **8000** -- API
- **3000** -- UI (containerized)
- **5173** -- UI (dev)
- **8080** -- Keycloak
- **3001** -- LangFuse
- **9090** -- MinIO API
- **9091** -- MinIO Console

Stop conflicting services or modify the port mappings in `compose.yml`.

### Database Connection Errors

If the API fails to connect to the database, ensure:

1. The database container is running: `make db-start`
2. Migrations have been applied: `make db-upgrade`
3. The `DATABASE_URL` in `.env` matches the connection string (default: `postgresql+asyncpg://user:password@localhost:5433/summit-cap`)

### LLM Connection Errors

If the API reports LLM connection errors:

1. Verify your LLM server is running (LM Studio, Ollama, or remote endpoint)
2. Check the `LLM_BASE_URL` in `.env` matches your server's address
3. Confirm the model names (`LLM_MODEL_FAST`, `LLM_MODEL_CAPABLE`) match models loaded in your LLM server

### Container Build Failures

If `make run` fails during image build:

1. Ensure you have sufficient disk space
2. Try building manually: `make containers-build`
3. Check for syntax errors in `Containerfile` paths

## Next Steps

- Explore the [Architecture](architecture.md) to understand system design
- Read the [Personas](personas.md) guide to see what each user can do
- Review the [API Reference](api-reference.md) for REST and WebSocket endpoints
- Deploy to OpenShift using the [Deployment](deployment.md) guide
