---
paths:
  - "packages/db/**/*"
  - "packages/api/src/models/**/*"
---

# Database Development

<!-- This rule is path-scoped to the database package. Update the glob if your -->
<!-- database code lives elsewhere (e.g., "src/db/**/*" or "backend/models/**/*"). -->

## Technology Stack

- **PostgreSQL** - Primary database
- **SQLAlchemy 2.0** - Async ORM with type hints
- **Alembic** - Database migrations
- **asyncpg** - Async PostgreSQL driver

## Package Structure

<!-- Update to match your actual database package layout. -->

```
packages/db/
├── src/
│   ├── db/
│   │   ├── database.py   # Connection and session management
│   │   └── models.py     # SQLAlchemy model definitions
│   └── __init__.py       # Public exports
├── alembic/
│   ├── versions/         # Migration files
│   ├── env.py            # Alembic environment config
│   └── script.py.mako    # Migration template
├── alembic.ini           # Alembic configuration
└── pyproject.toml        # Python dependencies
```

## Database Connection

The database uses async SQLAlchemy with connection pooling:

```python
# Import from the db package
from db import get_session, engine, User

# Use in FastAPI with dependency injection
@router.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    return result.scalars().all()
```

## Adding a New Model

### 1. Define the Model

```python
# packages/db/src/db/models.py
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column()
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    author: Mapped["User"] = relationship(back_populates="posts")
```

### 2. Export from Package

```python
# packages/db/src/__init__.py
from .db.database import Base, engine, get_session
from .db.models import User, Post

__all__ = ["Base", "engine", "get_session", "User", "Post"]
```

### 3. Generate Migration

```bash
# From packages/db directory
uv run alembic revision --autogenerate -m "add users and posts tables"

# From root directory
pnpm db:migrate:new -m "add users and posts tables"
```

### 4. Review the Migration

Always review auto-generated migrations in `packages/db/alembic/versions/`:

```python
# Example migration file
def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade() -> None:
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')
```

### 5. Apply Migration

```bash
# From packages/db directory
uv run alembic upgrade head

# From root directory
pnpm db:migrate
# or
make db-upgrade
```

## Conventions

- Import database objects from the `db` package: `from db import get_session, engine, User`
- Export all public models and utilities from `packages/db/src/__init__.py`
- Use `Mapped[]` type annotations for all columns (SQLAlchemy 2.0 style, not legacy `Column()`)
- Use `X | None` for nullable columns: `Mapped[str | None]`
- Index frequently queried columns with `index=True`
- Use `server_default=func.now()` for timestamp columns (not Python-side defaults)
- Define relationships explicitly with `back_populates` on both sides
- Every migration must have both `upgrade()` and `downgrade()` functions

## Migration Commands

```bash
# From root directory (recommended)
pnpm db:migrate           # Apply all pending migrations
pnpm db:migrate:new -m "description"  # Create new migration
pnpm db:migrate:down      # Rollback one migration
pnpm db:migrate:history   # Show migration history

# From packages/db directory
uv run alembic upgrade head      # Apply migrations
uv run alembic downgrade -1      # Rollback one
uv run alembic history           # Show history
uv run alembic current           # Show current revision
```

## Model Best Practices

### Use Type Hints

SQLAlchemy 2.0 uses `Mapped[]` for all columns:

```python
# Good - explicit types
id: Mapped[int] = mapped_column(primary_key=True)
name: Mapped[str] = mapped_column(String(100))
email: Mapped[str | None] = mapped_column(String(255), nullable=True)

# Bad - old style
id = Column(Integer, primary_key=True)
```

### Index Frequently Queried Columns

```python
email: Mapped[str] = mapped_column(String(255), index=True)
```

### Use Server Defaults for Timestamps

```python
from sqlalchemy import func

created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now()
)
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    onupdate=func.now()
)
```

### Define Relationships Explicitly

```python
# Parent side
posts: Mapped[list["Post"]] = relationship(back_populates="author")

# Child side
author: Mapped["User"] = relationship(back_populates="posts")
```

## Database Commands

```bash
# Start/stop database container
make db-start
make db-stop
make db-logs

# Or using pnpm
pnpm db:start
pnpm db:stop
```

## Environment Variables

```env
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
DB_ECHO=false  # Set to true for SQL query logging
```
