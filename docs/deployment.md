<!-- This project was developed with assistance from AI tools. -->

# Deployment Guide

This guide covers three deployment methods for Summit Cap Financial:

1. **Local development** (no containers) — API and UI dev servers with hot reload
2. **Containerized local stack** (compose) — Full application stack with containers
3. **OpenShift / Kubernetes deployment** (Helm) — Production-ready deployment

## Prerequisites

### For Local Development
- Python 3.11+
- Node.js 18+
- pnpm 8+
- PostgreSQL 16+ (via `make db-start` or local installation)

### For Containerized Local Stack
- Podman or Docker
- podman-compose or docker compose v2

### For OpenShift / Kubernetes Deployment
- oc (OpenShift CLI) or kubectl
- Helm 3.x
- Access to an OpenShift cluster or Kubernetes cluster
- Container registry access (quay.io, Docker Hub, or private registry)

## Local Development (No Containers)

This is the fastest path for iterative development with hot reload for both API and UI.

### Setup

```bash
# Install all dependencies
make setup

# Start PostgreSQL container
make db-start

# Run database migrations
make db-upgrade
```

### Start Dev Servers

```bash
# Start API (uvicorn) and UI (vite) dev servers
make dev
```

This starts:
- **API**: http://localhost:8000 (uvicorn with auto-reload)
- **UI**: http://localhost:5173 (vite with HMR)
- **API Docs**: http://localhost:8000/docs

To run API and UI separately:

```bash
# API only
cd packages/api
uv run uvicorn src.main:app --reload --port 8000

# UI only
cd packages/ui
pnpm dev
```

### Configuration

Create a `.env` file at the project root:

```bash
# Database (container default)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/summit-cap
COMPLIANCE_DATABASE_URL=postgresql+asyncpg://compliance_app:compliance_pass@localhost:5433/summit-cap

# Disable auth for local dev
AUTH_DISABLED=true

# LLM endpoint (LMStudio, Ollama, or OpenAI)
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=not-needed

# Object storage (if using MinIO container)
S3_ENDPOINT=http://localhost:9090
S3_ACCESS_KEY=minio
S3_SECRET_KEY=miniosecret
```

## Containerized Local Stack (Compose)

The primary local deployment method. All services run in containers with profile-based composition.

### Profiles

The `compose.yml` file is organized into profiles:

| Profile | Services |
|---------|----------|
| (none) | postgres + minio + api + ui |
| `auth` | + keycloak |
| `ai` | + llamastack |
| `observability` | + redis, clickhouse, langfuse-web, langfuse-worker |
| `full` | everything |

### Quick Start

```bash
# Minimal stack (postgres + minio + api + ui)
podman-compose up -d

# Full stack (all services)
podman-compose --profile full up -d

# Or use the Makefile alias
make run
```

### Profile-Specific Commands

```bash
# Minimal stack
make run-minimal

# With authentication (+ keycloak)
make run-auth

# With AI services (+ llamastack)
make run-ai

# With observability (+ langfuse, redis, clickhouse)
make run-obs

# Full stack
make run
```

### Stop Services

```bash
# Stop all containers
make stop

# Or directly
podman-compose --profile full down
```

### Port Mappings

| Service | Port | URL |
|---------|------|-----|
| UI | 3000 | http://localhost:3000 |
| API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| PostgreSQL | 5433 | postgresql://localhost:5433/summit-cap |
| Keycloak | 8080 | http://localhost:8080 |
| LlamaStack | 8321 | http://localhost:8321 |
| MinIO API | 9090 | http://localhost:9090 |
| MinIO Console | 9091 | http://localhost:9091 |
| LangFuse | 3001 | http://localhost:3001 |
| Redis | 6380 | redis://localhost:6380 |
| ClickHouse HTTP | 8123 | http://localhost:8123 |
| ClickHouse Native | 9000 | tcp://localhost:9000 |

### LLM Configuration

By default, the API container connects to `host.docker.internal:1234/v1`, expecting an OpenAI-compatible LLM server running on your host machine.

Supported local LLM servers:
- **LMStudio**: Start server, select model, set port to 1234
- **Ollama**: Run `ollama serve` (default port 11434, override with `LLM_BASE_URL`)
- **vLLM**: Run with `--port 1234`

To override:

```bash
# Use a different host port
LLM_BASE_URL=http://host.docker.internal:11434/v1 podman-compose up -d

# Use a remote endpoint
LLM_BASE_URL=https://api.openai.com/v1 LLM_API_KEY=sk-... podman-compose up -d
```

To use the bundled `llamastack` service instead:

```bash
# Start with ai profile
podman-compose --profile ai up -d

# Configure API to use llamastack container
# Set in compose.yml or override:
LLM_BASE_URL=http://llamastack:8321 podman-compose up -d
```

### Build Images Locally

```bash
# Build all images defined in compose.yml
podman-compose build

# Or use the Makefile
make containers-build
```

### Smoke Test

Automated test that starts the stack, verifies all endpoints, and tears down:

```bash
make smoke
```

### Docker vs Podman

All examples use `podman-compose` and `podman`. To use Docker instead:

```bash
# Override in environment
export COMPOSE="docker compose"
export CONTAINER_CLI="docker"

# Or per-command
COMPOSE="docker compose" make run
```

The Makefile auto-detects which tool is available, preferring Podman.

## OpenShift / Kubernetes Deployment

Production-ready Helm chart with optional components and external service integration.

### Build and Push Images

Before deploying, build the API and UI images and push them to a registry:

```bash
# Build images
make build-images

# Push to registry (default: quay.io/summit-cap)
make push-images

# Override registry and namespace
REGISTRY=docker.io REGISTRY_NS=myorg make push-images
```

Direct commands:

```bash
# Build
podman build -f packages/api/Containerfile -t summit-cap-api:latest .
podman build -f packages/ui/Containerfile -t summit-cap-ui:latest .

# Tag for registry
podman tag summit-cap-api:latest quay.io/myorg/summit-cap-api:latest
podman tag summit-cap-ui:latest quay.io/myorg/summit-cap-ui:latest

# Push
podman push quay.io/myorg/summit-cap-api:latest
podman push quay.io/myorg/summit-cap-ui:latest
```

### Deploy with Default Settings

```bash
# Deploy to OpenShift with full stack
make deploy

# Deploy with dev settings (auth disabled, smaller resources, no persistence)
make deploy-dev
```

This will:
1. Create the OpenShift project (namespace)
2. Push images to the registry
3. Update Helm chart dependencies
4. Deploy via `scripts/deploy.sh`

### Helm Deployment (Manual)

For full control over deployment:

```bash
# Create namespace
oc new-project summit-cap

# Deploy with custom values
helm upgrade --install summit-cap ./deploy/helm/summit-cap \
  --namespace summit-cap \
  --timeout 15m \
  --wait \
  --wait-for-jobs \
  --set global.imageRegistry=quay.io \
  --set global.imageRepository=myorg \
  --set global.imageTag=v1.0.0 \
  --set routes.sharedHost=summit-cap-demo.apps.example.com \
  --set secrets.AUTH_DISABLED=false \
  --set secrets.LLM_BASE_URL=http://vllm:8000/v1 \
  --set keycloak.enabled=true \
  --set langfuse.enabled=true
```

### Enable All Components

By default, only core services (api, ui, database, minio, keycloak) are enabled. To enable optional components:

```bash
helm upgrade --install summit-cap ./deploy/helm/summit-cap \
  --namespace summit-cap \
  --set keycloak.enabled=true \
  --set llamastack.enabled=true \
  --set langfuse.enabled=true
```

When `langfuse.enabled=true`, Redis and ClickHouse are automatically enabled as dependencies.

### OpenShift Route Configuration

The Helm chart creates two OpenShift Routes sharing a single hostname with path-based routing:

| Path | Service | Purpose |
|------|---------|---------|
| `/` | summit-cap-ui | React frontend |
| `/api/*` | summit-cap-api | API endpoints |
| `/health/` | summit-cap-api | Health check |
| `/docs` | summit-cap-api | OpenAPI docs |
| `/admin/*` | summit-cap-api | SQLAdmin panel |

To set a custom hostname:

```bash
--set routes.sharedHost=summit-cap-demo.apps.example.com
```

If `routes.sharedHost` is empty, the chart derives a hostname from the cluster domain:

```bash
# Auto-detected from oc whoami --show-server
summit-cap-summit-cap.apps.cluster.example.com
```

To disable routes (for local clusters without OpenShift):

```bash
--set routes.enabled=false
```

## Reusing OpenShift AI Services

Instead of deploying your own infrastructure, point at existing cluster services.

### Use Existing Model Serving (KServe / OpenShift AI)

Skip LlamaStack and point at an existing InferenceService:

```bash
helm upgrade --install summit-cap ./deploy/helm/summit-cap \
  --namespace summit-cap \
  --set llamastack.enabled=false \
  --set secrets.LLM_BASE_URL=https://my-model-serving.apps.example.com/v1 \
  --set secrets.LLM_API_KEY=<token>
```

### Use Existing Object Storage (ODF / MinIO)

Skip MinIO and point at existing S3-compatible storage:

```bash
helm upgrade --install summit-cap ./deploy/helm/summit-cap \
  --namespace summit-cap \
  --set minio.enabled=false \
  --set secrets.S3_ENDPOINT=https://s3.example.com \
  --set secrets.S3_ACCESS_KEY=<access-key> \
  --set secrets.S3_SECRET_KEY=<secret-key> \
  --set secrets.S3_BUCKET=summit-cap-docs \
  --set secrets.S3_REGION=us-east-1
```

### Use Existing Keycloak / RHSSO

Skip Keycloak and point at existing OIDC provider:

```bash
helm upgrade --install summit-cap ./deploy/helm/summit-cap \
  --namespace summit-cap \
  --set keycloak.enabled=false \
  --set secrets.KEYCLOAK_URL=https://sso.example.com \
  --set secrets.KEYCLOAK_REALM=my-realm \
  --set secrets.KEYCLOAK_CLIENT_ID=summit-cap
```

### Use Existing PostgreSQL

Skip database deployment and point at existing PostgreSQL:

```bash
helm upgrade --install summit-cap ./deploy/helm/summit-cap \
  --namespace summit-cap \
  --set database.enabled=false \
  --set secrets.DATABASE_URL=postgresql+asyncpg://user:pass@postgres.example.com:5432/summit-cap \
  --set secrets.COMPLIANCE_DATABASE_URL=postgresql+asyncpg://compliance:pass@postgres.example.com:5432/summit-cap
```

### Combined Example

Deploy minimal footprint using only external services:

```bash
helm upgrade --install summit-cap ./deploy/helm/summit-cap \
  --namespace summit-cap \
  --set database.enabled=false \
  --set keycloak.enabled=false \
  --set minio.enabled=false \
  --set llamastack.enabled=false \
  --set secrets.DATABASE_URL=<external-db> \
  --set secrets.COMPLIANCE_DATABASE_URL=<external-db> \
  --set secrets.KEYCLOAK_URL=<external-keycloak> \
  --set secrets.S3_ENDPOINT=<external-s3> \
  --set secrets.LLM_BASE_URL=<external-llm>
```

## Configuration Reference

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `summit-cap` | Database name |
| `POSTGRES_USER` | `user` | Database user |
| `POSTGRES_PASSWORD` | `password` | Database password |
| `DATABASE_URL` | `postgresql+asyncpg://user:password@summit-cap-db:5432/summit-cap` | SQLAlchemy connection string |
| `COMPLIANCE_DATABASE_URL` | `postgresql+asyncpg://compliance_app:compliance_pass@summit-cap-db:5432/summit-cap` | Connection string for compliance role (HMDA schema) |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_DISABLED` | `false` | Bypass JWT validation (set `true` for dev/demo) |
| `KEYCLOAK_URL` | `http://keycloak:8080` | Keycloak server URL |
| `KEYCLOAK_REALM` | `summit-cap` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | `summit-cap-ui` | OIDC client ID |
| `JWKS_CACHE_TTL` | `300` | JWKS cache lifetime in seconds |

### Object Storage (S3 / MinIO)

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT` | `http://minio:9000` | S3-compatible endpoint URL |
| `S3_ACCESS_KEY` | `minio` | S3 access key |
| `S3_SECRET_KEY` | `miniosecret` | S3 secret key |
| `S3_BUCKET` | `documents` | Bucket name for document storage |
| `S3_REGION` | `us-east-1` | AWS region (required even for MinIO) |
| `UPLOAD_MAX_SIZE_MB` | `50` | Maximum upload size in megabytes |

### LLM

| Variable | Default (Compose) | Default (Helm) | Description |
|----------|-------------------|----------------|-------------|
| `LLM_BASE_URL` | `http://host.docker.internal:1234/v1` | `http://vllm:8000/v1` | OpenAI-compatible LLM endpoint |
| `LLM_API_KEY` | `not-needed` | `not-needed` | API key for LLM endpoint |
| `LLM_MODEL_FAST` | (empty, uses default) | `gpt-4o-mini` | Model name for fast/simple queries |
| `LLM_MODEL_CAPABLE` | (empty, uses default) | `gpt-4o-mini` | Model name for complex reasoning |

### Safety / Shields (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `SAFETY_MODEL` | (empty) | Llama Guard model name (enables safety if set) |
| `SAFETY_ENDPOINT` | (empty) | Safety model endpoint (defaults to `LLM_BASE_URL`) |
| `SAFETY_API_KEY` | (empty) | Safety model API key (defaults to `LLM_API_KEY`) |

### Observability (LangFuse)

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | (empty) | LangFuse public key (enables tracing if set) |
| `LANGFUSE_SECRET_KEY` | (empty) | LangFuse secret key |
| `LANGFUSE_HOST` | (empty) | LangFuse server URL (e.g., `http://langfuse-web:3000`) |

When using the `observability` profile in compose or `langfuse.enabled=true` in Helm, these are automatically configured for the bundled LangFuse instance.

### Admin Panel

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLADMIN_USER` | `admin` | SQLAdmin username |
| `SQLADMIN_PASSWORD` | `admin` | SQLAdmin password |
| `SQLADMIN_SECRET_KEY` | `change-me-in-production` | Session cookie secret key |

Access SQLAdmin at http://localhost:8000/admin (compose) or https://<hostname>/admin (OpenShift).

### API / General

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode (verbose logging, better error messages) |
| `ALLOWED_HOSTS` | `["*"]` | CORS allowed origins (JSON array) |

## Deployment Status and Debugging

### Check Deployment Status

```bash
# Show deployment status
make status

# Or directly
helm status summit-cap --namespace summit-cap
oc get pods -n summit-cap
```

### Debug Failed Deployments

```bash
# Run diagnostic script
make debug

# Manual checks
oc describe pod <pod-name> -n summit-cap
oc logs <pod-name> -n summit-cap
oc get events -n summit-cap --sort-by='.lastTimestamp'
```

### Lint and Preview Helm Chart

```bash
# Lint chart
make helm-lint

# Preview rendered templates
make helm-template

# Save rendered templates to file
helm template summit-cap ./deploy/helm/summit-cap \
  --set global.imageRegistry=quay.io \
  --set global.imageRepository=myorg \
  > rendered.yaml
```

### Undeploy

```bash
# Remove deployment
make undeploy

# Or directly
helm uninstall summit-cap --namespace summit-cap
oc delete project summit-cap
```

## Next Steps

- [Getting Started Guide](getting-started.md) — Quickstart tutorial
- [Architecture Overview](architecture.md) — System design and component interaction
- [API Reference](api-reference.md) — REST and WebSocket API documentation
- [Personas & Workflows](personas.md) — Exploring the 5 user personas
