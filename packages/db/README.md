# ai-quickstart-template Database

PostgreSQL database setup with Podman Compose and Alembic migrations.

PostgreSQL database architecture and development guide.

> **Setup & Installation**: See the [root README](../../README.md) for installation and quick start instructions.

## Features

- **PostgreSQL 16**: Latest PostgreSQL database with async support
- **Podman Compose**: Container orchestration for local development
- **Alembic**: Database migration management
- **Async SQLAlchemy**: Non-blocking database operations
- **Connection Pooling**: Efficient connection reuse
- **Health Checks**: Built-in database health monitoring

## Quick Start

Commands below assume you're in the `packages/db` directory. From the project root, prefix with `db:` (e.g., `pnpm db:migrate`).

```bash
# Start the database container
pnpm db:start

# Apply migrations
pnpm migrate

# View database logs
pnpm db:logs
```

## Architecture Overview

This database package provides async SQLAlchemy integration with Alembic migrations:

```
Application → DatabaseService → AsyncSession → PostgreSQL
                ↓
         Connection Pooling
                ↓
         Health Checks
```

### Key Architectural Patterns

- **Async SQLAlchemy**: Non-blocking database operations using `asyncpg` driver
- **Connection Pooling**: Managed by SQLAlchemy engine for efficient connection reuse
- **Dependency Injection**: `DatabaseService` and session management via FastAPI dependencies
- **Migration Management**: Alembic for version-controlled schema changes
- **Service Pattern**: `DatabaseService` class provides health checks and session management

## Project Structure

```
src/
└── db/
    ├── __init__.py          # Package exports (DatabaseService, get_db_service)
    └── database.py          # Database engine, session factory, DatabaseService class

alembic/
├── versions/                 # Migration files (auto-generated)
├── env.py                   # Alembic environment configuration
└── script.py.mako          # Migration template

tests/
└── test_database.py         # Database connection and health check tests

alembic.ini                  # Alembic configuration
pyproject.toml               # Python dependencies

# Note: compose.yml is at project root, not in this package
```

### Directory Purposes

- **`src/db/database.py`**: Core database module containing:
  - `engine`: SQLAlchemy async engine with connection pooling
  - `SessionLocal`: Session factory for creating database sessions
  - `Base`: Declarative base for SQLAlchemy models
  - `DatabaseService`: Service class for health checks and session management
  - `get_db_service()`: FastAPI dependency function for dependency injection

- **`alembic/`**: Alembic migration system:
  - `versions/`: Migration files (one per schema change)
  - `env.py`: Alembic environment configuration (connects to database, loads models)
  - `script.py.mako`: Template for new migration files

- **`tests/`**: Database tests. Use transaction rollback for test isolation.

## Database Service Architecture

### DatabaseService Class

The `DatabaseService` provides a clean interface for database operations:

```python
from db import DatabaseService, get_db_service

# In FastAPI routes (via dependency injection)
@router.get("/users")
async def get_users(db_service: DatabaseService = Depends(get_db_service)):
    # Use db_service for database operations
    session = await db_service.get_session()
    # ... use session
```

### Connection Pooling

The SQLAlchemy engine manages a connection pool automatically:

```python
# src/db/database.py
engine = create_async_engine(DATABASE_URL, echo=True)
```

**Key settings:**
- `echo=True`: Logs SQL queries (set to `False` in production)
- Connection pool size managed automatically
- Connections are reused efficiently

### Session Management

Sessions are created via the `SessionLocal` factory:

```python
async with SessionLocal() as session:
    # Use session for queries
    result = await session.execute(select(User))
```

**Best practices:**
- Always use `async with` for proper cleanup
- Sessions are not thread-safe (use one per request)
- Use dependency injection in FastAPI routes

## Adding New Models

Follow these steps to add a new database model:

### 1. Define SQLAlchemy Model

Create a model file (typically in `src/db/models.py` or similar):

```python
# src/db/models.py
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base
from db.database import Base

class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 2. Import Models in Alembic

Ensure Alembic can discover your models. Update `alembic/env.py` to import your models:

```python
# alembic/env.py (already configured)
from db.database import Base
# Import all models here so Alembic can detect them
from db import models  # or specific imports
```

### 3. Generate Migration

Auto-generate a migration based on model changes:

```bash
pnpm migrate:new -m "add user table"
```

This creates a new file in `alembic/versions/` with the migration SQL.

### 4. Review Migration

Always review the generated migration file:

```python
# alembic/versions/xxxx_add_user_table.py
def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

def downgrade():
    op.drop_table('user')
```

### 5. Apply Migration

Apply the migration to your database:

```bash
pnpm migrate
```

### Model Best Practices

- **Table Names**: Use singular nouns (`user`, not `users`)
- **Column Names**: Use snake_case (`created_at`, not `createdAt`)
- **Primary Keys**: Always use `id` as the primary key column name
- **Foreign Keys**: Use `table_id` format (e.g., `user_id`)
- **Timestamps**: Include `created_at` and `updated_at` on all tables
- **Indexes**: Add indexes for frequently queried columns
- **Constraints**: Use database-level constraints (unique, foreign keys, check)

## Database Schema

The database schema is managed through SQLAlchemy models and Alembic migrations. Models define the structure of your database tables, and migrations track changes over time.

### Best Practices

- **Version Control**: Always commit migration files to version control
- **Review Migrations**: Review auto-generated migrations before applying them
- **Test Migrations**: Test migrations in development before applying to production
- **Backup Before Migration**: Always backup your database before running migrations in production
- **Rollback Plan**: Have a rollback plan for every migration
- **Naming Conventions**: Follow consistent naming conventions for tables, columns, and indexes
- **Documentation**: Document complex migrations and schema changes

## Migration Workflow

### Schema Changes (Auto-Generated)

For most schema changes, use auto-generation:

```bash
# 1. Modify your SQLAlchemy models
# 2. Generate migration
pnpm migrate:new -m "add user table"

# 3. Review the generated migration file
# 4. Apply migration
pnpm migrate
```

### Data Migrations (Manual)

For data transformations, create manual migrations:

```bash
# 1. Create empty migration
alembic revision -m "migrate user emails to lowercase"

# 2. Edit the migration file
```

```python
# alembic/versions/xxxx_migrate_user_emails.py
def upgrade():
    # Data migration logic
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE user SET email = LOWER(email)")
    )

def downgrade():
    # Rollback logic if needed
    pass
```

```bash
# 3. Apply migration
pnpm migrate
```

### Migration Commands

Run these from the `packages/db` directory, or use root commands (e.g., `pnpm db:migrate`).

```bash
# Apply migrations
pnpm migrate                    # Apply all pending migrations (or pnpm db:migrate from root)
uv run alembic upgrade head     # Direct alembic command
uv run alembic upgrade +2       # Apply next 2 migrations
uv run alembic upgrade ae1027a  # Apply to specific revision

# Rollback migrations
pnpm migrate:down               # Rollback last migration (or pnpm db:migrate:down from root)
uv run alembic downgrade -1     # Direct alembic command
uv run alembic downgrade base   # Rollback all migrations

# Information
pnpm migrate:history            # Show migration history (or pnpm db:migrate:history from root)
uv run alembic current          # Show current revision
uv run alembic show ae1027a     # Show specific migration
```

### Rollback Strategies

**Development:**
- Rollback is safe and common
- Use `pnpm migrate:down` to undo last migration

**Production:**
- Always test migrations in staging first
- Have a rollback plan before applying
- Consider zero-downtime migration strategies
- Never rollback migrations that have been applied to production for more than a few hours

## Using Models in API Package

When the API package is enabled, use models via dependency injection:

```python
# In API package: src/routes/users.py
from fastapi import APIRouter, Depends
from db import DatabaseService, get_db_service
from sqlalchemy import select
from db.models import User

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db_service: DatabaseService = Depends(get_db_service)
):
    session = await db_service.get_session()
    async with session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user
```

See the [API package README](../../api/README.md) for more details on using database models in routes.

## Testing Database Code

### Test Structure

Tests use `pytest` with `pytest-asyncio` for async support:

```python
# tests/test_database.py
import pytest
from db import DatabaseService

@pytest.mark.asyncio
async def test_database_health_check():
    service = DatabaseService()
    health = await service.health_check()
    assert health["status"] == "healthy"
```

### Transaction Rollback Pattern

For tests that modify the database, use transaction rollback:

```python
@pytest.mark.asyncio
async def test_create_user(db_session):
    # db_session is automatically rolled back after test
    from db.models import User
    
    user = User(email="test@example.com", name="Test User")
    db_session.add(user)
    await db_session.commit()
    
    # Test assertions
    assert user.id is not None
```

### Running Tests

```bash
# Start test database
pnpm db:start

# Run migrations
pnpm migrate

# Run tests
python -m pytest tests/
```

## Configuration

### Environment Variables

Database configuration is managed via environment variables:

```env
# Database connection (project root .env file)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai-quickstart-template
DB_ECHO=false  # Set to true for SQL query logging
```

### Connection String Format

```
postgresql+asyncpg://[user[:password]@][host[:port]][/database]
```

**Components:**
- `postgresql+asyncpg`: Driver specification (required for async)
- `user:password`: Database credentials
- `host:port`: Database server (default: localhost:5432)
- `database`: Database name

### Database Container

The database runs in a Podman container managed from the project root:

- **Service Name**: ai-quickstart-template-db
- **Host**: localhost
- **Port**: 5432
- **Database**: ai-quickstart-template
- **Username**: user
- **Password**: password

**Note**: The `compose.yml` file is at the project root, not in this package.

## Available Scripts

```bash
# Database Management
pnpm db:start       # Start PostgreSQL container
pnpm db:stop        # Stop container
pnpm db:logs        # View logs

# Migration Management
pnpm migrate        # Apply all pending migrations
pnpm migrate:down      # Rollback last migration
pnpm migrate:new -m "message"  # Create new migration
pnpm migrate:history        # Show migration history
```

---

Generated with [AI QuickStart CLI](https://github.com/TheiaSurette/quickstart-cli)
