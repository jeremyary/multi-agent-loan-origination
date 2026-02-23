# ai-quickstart-template

A ready-made template for creating new AI Quickstarts

## Architecture

This project is built with:

- **Turborepo** - High-performance build system for the monorepo
- **React + Vite** - Modern frontend with TanStack Router
- **FastAPI** - Python backend with async support
- **PostgreSQL** - Database with Alembic migrations

## Project Structure

```
ai-quickstart-template/
├── packages/
│   ├── ui/           # React frontend application
│   ├── api/          # FastAPI backend service
│   └── db/           # Database and migrations
├── compose.yml       # Podman Compose configuration (all services)
├── Makefile          # Makefile with common commands
├── turbo.json        # Turborepo configuration
└── package.json      # Root package configuration
```

## Quick Start

### Prerequisites
- Node.js 18+
- pnpm 9+
- Python 3.11+
- uv (Python package manager)
- Podman and podman-compose (for database)

### Development

1. **Install all dependencies** (Node.js + Python):
```bash
make setup
```

   Or using pnpm directly:
```bash
pnpm setup
```

   Or install them separately:
```bash
pnpm install          # Install Node.js dependencies
pnpm install:deps     # Install Python dependencies in API package
```

2. **Start the database** (using Makefile - recommended):
```bash
make db-start
```

   Or using pnpm:
```bash
pnpm db:start
```

3. **Run database migrations**:
```bash
make db-upgrade
```

   Or using pnpm:
```bash
pnpm db:migrate
```

4. **Start development servers**:
```bash
make dev
```

   Or using pnpm:
```bash
pnpm dev
```

### Available Commands

**Using Makefile (Recommended)** - Works with any package manager (pnpm/npm/yarn):
```bash
make setup            # Install all dependencies
make dev              # Start all development servers
make build            # Build all packages
make test             # Run tests across all packages
make lint             # Check code formatting
make db-start         # Start database container
make db-stop          # Stop database container
make db-logs          # View database logs
make db-upgrade       # Run database migrations
make containers-build # Build all containers
make containers-up    # Start all containers (production-like)
make containers-down  # Stop all containers
make clean            # Clean build artifacts
```

**Using pnpm directly**:
```bash
# Development
pnpm dev              # Start all development servers
pnpm build            # Build all packages
pnpm test             # Run tests across all packages
pnpm lint             # Check code formatting
pnpm format           # Format code

# Database
pnpm db:start         # Start database containers
pnpm db:stop          # Stop database containers  
pnpm db:migrate       # Run database migrations
pnpm db:migrate:new      # Create new migration
pnpm compose:up       # Start all containers
pnpm compose:down     # Stop all containers
pnpm containers:build # Build all containers
# Utilities
pnpm clean            # Clean build artifacts (turbo prune)
```

**Note**: The `compose.yml` file at the project root manages all containerized services (database, and future API/UI containers). Service names follow the format `[project-name]-[package]` (e.g., `my-chatbot-db`).

## Development URLs

- **Frontend App**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: postgresql://localhost:5432

## Deployment

This project supports multiple deployment strategies for different environments.

### Container-Based Deployment (Podman Compose)

For local testing or single-server deployments, use Podman Compose:

```bash
# Build all container images
make containers-build

# Start all services
make containers-up

# View logs
make containers-logs

# Stop all services
make containers-down
```

**Note**: Before deploying, ensure you've:
1. Built production-ready container images
2. Configured environment variables in `.env` or `compose.yml`
3. Run database migrations if deploying with a database

### OpenShift/Helm Deployment

For production OpenShift (or Kubernetes) deployments, use the included Helm charts.

#### Prerequisites

- OpenShift cluster (4.10+) or Kubernetes cluster (1.24+)
- `oc` CLI configured to access your OpenShift cluster (or `kubectl` for Kubernetes)
- `helm` CLI installed (v3.8+)
- Container registry access (for pushing images)

#### Building Container Images

Before deploying to OpenShift, build and push your container images:

```bash
# Build API image (if API is enabled)
cd packages/api
podman build -t ai-quickstart-template-api:latest .
podman tag ai-quickstart-template-api:latest registry.example.com/ai-quickstart-template-api:latest
podman push registry.example.com/ai-quickstart-template-api:latest

# Build UI image (if UI is enabled)
cd packages/ui
podman build -t ai-quickstart-template-ui:latest .
podman tag ai-quickstart-template-ui:latest registry.example.com/ai-quickstart-template-ui:latest
podman push registry.example.com/ai-quickstart-template-ui:latest
```

#### Deploying with Helm

**Option 1: Using Makefile (Recommended)**

The easiest way to deploy is using the provided Makefile targets:

1. **Configure environment variables**:

   Create a `.env` file in the project root:

   ```env
   POSTGRES_DB=ai-quickstart-template
   POSTGRES_USER=your-db-user
   POSTGRES_PASSWORD=your-secure-password
   DATABASE_URL=postgresql+asyncpg://user:password@ai-quickstart-template-db:5432/ai-quickstart-template
   DEBUG=false
   ALLOWED_HOSTS=["*"]
   VITE_API_BASE_URL=https://api.example.com
   VITE_ENVIRONMENT=production
   ```

2. **Deploy to OpenShift**:

   ```bash
   # Production deployment
   make deploy
   
   # Development deployment (single replica, no persistence)
   make deploy-dev
   
   # Customize deployment
   make deploy REGISTRY_URL=quay.io REPOSITORY=myorg IMAGE_TAG=v1.0.0
   ```

   **Note**: The Makefile automatically creates an OpenShift project if it doesn't exist. For Kubernetes, use `--namespace` instead of `--project` in Helm commands.

**Option 2: Using Helm CLI Directly**

For more control, use Helm CLI directly:

1. **Configure environment variables**:

   Export environment variables or create a `.env` file:

   ```bash
   export POSTGRES_DB="ai-quickstart-template"
   export POSTGRES_USER="your-db-user"
   export POSTGRES_PASSWORD="your-secure-password"
   export DATABASE_URL="postgresql+asyncpg://user:password@ai-quickstart-template-db:5432/ai-quickstart-template"
   export DEBUG="false"
   export ALLOWED_HOSTS='["*"]'
   export VITE_API_BASE_URL="https://api.example.com"
   export VITE_ENVIRONMENT="production"
   ```

2. **Install the Helm chart**:

   **For OpenShift** (recommended):
   ```bash
   cd deploy/helm/ai-quickstart-template
   
   # Create OpenShift project first
   oc new-project ai-quickstart-template || oc project ai-quickstart-template
   
   # Install with default values
   helm install ai-quickstart-template . \
     --namespace ai-quickstart-template \
     --set secrets.POSTGRES_DB="$POSTGRES_DB" \
     --set secrets.POSTGRES_USER="$POSTGRES_USER" \
     --set secrets.POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
     --set secrets.DATABASE_URL="$DATABASE_URL" \
     --set secrets.DEBUG="$DEBUG" \
     --set secrets.ALLOWED_HOSTS="$ALLOWED_HOSTS" \
     --set secrets.VITE_API_BASE_URL="$VITE_API_BASE_URL"
   ```

   **For Kubernetes** (alternative):
   ```bash
   cd deploy/helm/ai-quickstart-template
   
   # Install with default values
   helm install ai-quickstart-template . \
     --namespace ai-quickstart-template \
     --create-namespace \
     --set secrets.POSTGRES_DB="$POSTGRES_DB" \
     --set secrets.POSTGRES_USER="$POSTGRES_USER" \
     --set secrets.POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
     --set secrets.DATABASE_URL="$DATABASE_URL" \
     --set secrets.DEBUG="$DEBUG" \
     --set secrets.ALLOWED_HOSTS="$ALLOWED_HOSTS" \
     --set secrets.VITE_API_BASE_URL="$VITE_API_BASE_URL"
   ```

3. **Update image references** (if using custom registry):

   Using Makefile:
   ```bash
   make deploy REGISTRY_URL=registry.example.com REPOSITORY=myorg IMAGE_TAG=v1.0.0
   ```

   Or edit `deploy/helm/ai-quickstart-template/values.yaml` directly:

   Edit `deploy/helm/ai-quickstart-template/values.yaml` and update image repository/tag:

   ```yaml
   api:
     image:
       repository: registry.example.com/ai-quickstart-template-api
       tag: latest
   ui:
     image:
       repository: registry.example.com/ai-quickstart-template-ui
       tag: latest
   ```

4. **Run database migrations** (if database is enabled):

   ```bash
   # Migrations run automatically via an OpenShift/Kubernetes Job on first deployment
   # To manually trigger migrations (OpenShift):
   oc create job --from=cronjob/ai-quickstart-template-migration ai-quickstart-template-migration-manual -n ai-quickstart-template
   
   # Or using kubectl (Kubernetes):
   kubectl create job --from=cronjob/ai-quickstart-template-migration ai-quickstart-template-migration-manual -n ai-quickstart-template
   ```

5. **Verify deployment**:

   **Using OpenShift CLI** (`oc`):
   ```bash
   # Check pod status
   oc get pods -n ai-quickstart-template
   
   # Check services
   oc get svc -n ai-quickstart-template
   
   # Check routes (OpenShift)
   oc get routes -n ai-quickstart-template
   
   # View logs
   oc logs -n ai-quickstart-template -l app=ai-quickstart-template-api
   oc logs -n ai-quickstart-template -l app=ai-quickstart-template-ui
   oc logs -n ai-quickstart-template -l app=ai-quickstart-template-db
   ```

   **Using Kubernetes CLI** (`kubectl` - alternative):
   ```bash
   # Check pod status
   kubectl get pods -n ai-quickstart-template
   
   # Check services
   kubectl get svc -n ai-quickstart-template
   
   # View logs
   kubectl logs -n ai-quickstart-template -l app=ai-quickstart-template-api
   kubectl logs -n ai-quickstart-template -l app=ai-quickstart-template-ui
   kubectl logs -n ai-quickstart-template -l app=ai-quickstart-template-db
   ```

#### Upgrading a Deployment

Using Makefile:
```bash
# Upgrade with new image tag
make deploy IMAGE_TAG=v1.1.0

# Upgrade with custom values
make deploy HELM_EXTRA_ARGS="--set api.replicas=3"
```

Using Helm CLI:
```bash
cd deploy/helm/ai-quickstart-template

# Upgrade with new values
helm upgrade ai-quickstart-template . \
  --namespace ai-quickstart-template \
  --reuse-values \
  --set api.image.tag=v1.1.0
```

#### Uninstalling

Using Makefile:
```bash
make undeploy
```

Using OpenShift CLI (`oc`):
```bash
helm uninstall ai-quickstart-template --namespace ai-quickstart-template
oc delete project ai-quickstart-template
```

Using Kubernetes CLI (`kubectl` - alternative):
```bash
helm uninstall ai-quickstart-template --namespace ai-quickstart-template
kubectl delete namespace ai-quickstart-template
```

### Environment Configuration

#### Development

Create a `.env` file in the project root for local development:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai-quickstart-template
DB_ECHO=false
# API
DEBUG=true
ALLOWED_HOSTS=["http://localhost:5173"]
# UI
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
```

#### Production

For production deployments:

1. **Use OpenShift Secrets** (recommended):
   - Secrets are managed via Helm values.yaml
   - Never commit secrets to version control
   - OpenShift provides additional security features like secret rotation

2. **Use environment-specific values files**:
   ```bash
   # Create production values
   cp deploy/helm/ai-quickstart-template/values.yaml deploy/helm/ai-quickstart-template/values.prod.yaml
   
   # Deploy with production values
   helm install ai-quickstart-template . -f values.prod.yaml
   ```

3. **Configure resource limits**:
   Edit `deploy/helm/ai-quickstart-template/values.yaml` to adjust CPU/memory limits based on your workload.

### Production Considerations

- **Database Backups**: Set up regular backups for PostgreSQL if database is enabled
- **Monitoring**: Configure health checks and monitoring for all services
- **Scaling**: Adjust replica counts in Helm values.yaml based on load
- **Security**: 
  - Use strong passwords and API keys
  - Enable TLS/HTTPS for production
  - Configure network policies
  - Review security contexts in Helm templates
- **High Availability**: Consider multi-replica deployments for critical services
- **Resource Management**: Set appropriate CPU/memory limits based on your workload

### Troubleshooting

**Pods not starting**:

Using OpenShift CLI (`oc`):
```bash
oc describe pod <pod-name> -n ai-quickstart-template
oc logs <pod-name> -n ai-quickstart-template
oc get events -n ai-quickstart-template --sort-by='.lastTimestamp'
```

Using Kubernetes CLI (`kubectl` - alternative):
```bash
kubectl describe pod <pod-name> -n ai-quickstart-template
kubectl logs <pod-name> -n ai-quickstart-template
kubectl get events -n ai-quickstart-template --sort-by='.lastTimestamp'
```

**Database connection issues**:
- Verify database service is running: `oc get svc -n ai-quickstart-template` (or `kubectl get svc -n ai-quickstart-template`)
- Check DATABASE_URL format matches your database configuration
- Verify secrets are correctly set: `oc get secret -n ai-quickstart-template` (or `kubectl get secret -n ai-quickstart-template`)

**Image pull errors**:
- Verify image registry credentials
- Check image pull policy in values.yaml
- Ensure images are pushed to the registry

For more details, see the [Helm chart documentation](deploy/helm/ai-quickstart-template/README.md) (if available) or the [Helm values file](deploy/helm/ai-quickstart-template/values.yaml).

## Extending the Template

This section covers how to customize and extend the template for your project.

### Renaming the Project

After creating a repository from this template, rename the project to match your application:

```bash
# Replace all occurrences of the template name with your project name
# Example: renaming to "my-chatbot"

# On macOS/Linux:
find . -type f -not -path './.git/*' -exec sed -i '' 's/ai-quickstart-template/my-chatbot/g' {} +

# Rename the Helm chart directory
mv deploy/helm/ai-quickstart-template deploy/helm/my-chatbot
```

**Files affected:**
- `package.json` (root and all packages)
- `compose.yml` and `.env.example`
- Helm chart files in `deploy/helm/`
- Python config files (`pyproject.toml`, `alembic.ini`)
- UI components (`header.tsx`, `hero.tsx`, `index.html`)

### Quick Reference

| Task | Location | Documentation |
|------|----------|---------------|
| Add API endpoint | `packages/api/src/routes/` | [API README](packages/api/README.md#adding-new-endpoints) |
| Add UI page | `packages/ui/src/routes/` | [UI README](packages/ui/README.md#adding-new-routes) |
| Add UI component | `packages/ui/src/components/` | [UI README](packages/ui/README.md#adding-new-components) |
| Add database model | `packages/db/src/db/` | [DB README](packages/db/README.md#adding-new-models) |
| Create migration | Run `pnpm db:migrate:new -m "message"` | [DB README](packages/db/README.md#migration-workflow) |
| Add API integration | `packages/ui/src/services/` + `hooks/` | [UI README](packages/ui/README.md#adding-api-integration) |

### Adding a New API Endpoint

1. **Create schema** in `packages/api/src/schemas/your_resource.py`
2. **Create route** in `packages/api/src/routes/your_resource.py`
3. **Register router** in `packages/api/src/main.py`
4. **Add tests** in `packages/api/tests/test_your_resource.py`

See the [API README](packages/api/README.md#adding-new-endpoints) for detailed examples.

### Adding a New UI Page

TanStack Router uses file-based routing. Create a file in `packages/ui/src/routes/`:

```typescript
// packages/ui/src/routes/about.tsx
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/about')({
  component: About,
});

function About() {
  return <div>About page</div>;
}
```

The route tree regenerates automatically during development. See the [UI README](packages/ui/README.md#adding-new-routes) for dynamic routes and layouts.

### Adding a Database Model

1. **Define model** in `packages/db/src/db/models.py`
2. **Generate migration**: `pnpm db:migrate:new -m "add your_table"`
3. **Review migration** in `packages/db/alembic/versions/`
4. **Apply migration**: `pnpm db:migrate`

See the [DB README](packages/db/README.md#adding-new-models) for model patterns and best practices.

### Connecting UI to API

This project uses a **hooks/services pattern** for API integration:

1. **Create Zod schema** in `packages/ui/src/schemas/` for response validation
2. **Create service** in `packages/ui/src/services/` for API calls
3. **Create hook** in `packages/ui/src/hooks/` wrapping TanStack Query
4. **Use hook in component** (never call services directly)

```
Component → Hook → TanStack Query → Service → API
```

See the [UI README](packages/ui/README.md#hooks-and-services-pattern) for detailed examples.

### Package Documentation

Each package has detailed documentation:

- **[API README](packages/api/README.md)** - FastAPI backend: routes, schemas, testing, configuration
- **[UI README](packages/ui/README.md)** - React frontend: routing, components, state management, Storybook
- **[DB README](packages/db/README.md)** - PostgreSQL: models, migrations, connection management

## Testing

This project uses **Vitest** for UI testing and **Pytest** for API testing.

### Running Tests

```bash
# Run all tests across packages
pnpm test

# Run specific package tests
pnpm --filter ui test       # UI tests (Vitest)
pnpm --filter api test      # API tests (Pytest)

# Watch mode (UI only)
cd packages/ui && pnpm test
```

### Test Locations

| Package | Framework | Test Location |
|---------|-----------|---------------|
| UI | Vitest + React Testing Library | `packages/ui/src/**/*.test.tsx` (co-located) |
| API | Pytest | `packages/api/tests/` |

### Writing Tests

See the individual package READMEs for detailed testing guides:
- [UI Testing Guide](packages/ui/README.md#testing)
- [API Testing Guide](packages/api/README.md#testing-patterns)

## Learn More

- [Turborepo](https://turbo.build/) - Monorepo build system
- [TanStack Router](https://tanstack.com/router) - Type-safe routing
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations

---

Generated with [AI QuickStart CLI](https://github.com/TheiaSurette/quickstart-cli)
