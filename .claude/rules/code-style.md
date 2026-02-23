# Code Style Guidelines

> **Scope:** This file is global — it covers both TypeScript and Python. Apply the relevant language section based on the file you are editing. For Python-only projects, you may use `python-style.md` instead.

## Automated Formatting

This project uses automated formatters. Run before committing:

```bash
pnpm lint        # Check all packages
pnpm lint:fix    # Auto-fix issues
pnpm format      # Format with Prettier
```

## General

- Never use emojis anywhere: code, comments, commit messages, documentation, agent output, PR descriptions, PR titles, GitHub comments, branch names, or any other artifact visible to users or stored in the repository
- Always include a comment at the top of code files indicating AI assistance: `// This project was developed with assistance from AI tools.` (JS/TS) or `# This project was developed with assistance from AI tools.` (Python) — this is a Red Hat policy requirement per `.claude/rules/ai-compliance.md`
- Code should be self-documenting; add comments only for "why", not "what"
- Include only comments necessary to understand the code
- TODO format: `// TODO: description` (JS/TS) or `# TODO: description` (Python)

## TypeScript

### General Rules

- Use TypeScript strict mode
- Prefer `interface` over `type` for object shapes
- Use explicit return types for exported functions
- Avoid `any` — use `unknown` if type is truly unknown

### Formatting

- 4-space indentation, no tabs
- Max line length: 150 characters (180 for strings/URLs)
- Trailing commas in multi-line structures
- Semicolons required
- Single quotes for strings, backticks for interpolation

### Variables & Functions

- Use `const` by default; `let` only when reassignment is necessary; never `var`
- Prefer early returns over deeply nested conditionals
- Destructure objects and arrays at point of use
- Arrow functions for callbacks; named `function` declarations for top-level exports

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `UserProfile`, `NavBar` |
| Hooks | camelCase with `use` prefix | `useAuth`, `useUsers` |
| Functions | camelCase | `fetchUser`, `handleClick` |
| Constants | SCREAMING_SNAKE_CASE | `API_BASE_URL` |
| Files (components) | kebab-case | `user-profile.tsx` |
| Files (utilities) | kebab-case | `format-date.ts` |
| Types/interfaces | PascalCase with no `I` prefix | `UserProfile`, not `IUserProfile` |
| Boolean variables | prefix with `is`, `has`, `should`, `can` | `isActive`, `hasPermission` |

### Component Patterns

```typescript
// Props interface above component
interface ButtonProps {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
  onClick?: () => void;
}

// Named export for components
export function Button({ variant = 'primary', children, onClick }: ButtonProps) {
  return (
    <button className={cn('btn', `btn-${variant}`)} onClick={onClick}>
      {children}
    </button>
  );
}
```

- Define props interface above the component
- Use named exports for components (not default exports)
- Use `cn()` helper for conditional class composition

### Import Order

1. React and external libraries
2. Internal aliases (`@/` paths)
3. Relative imports
4. Styles

```typescript
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/atoms/button';
import { useAuth } from '@/hooks/auth';

import { formatDate } from './utils';
import './styles.css';
```

- No circular imports
- Prefer named exports over default exports

### Comments

- Use JSDoc for public API functions

### ESLint Configuration

Located at `packages/ui/eslint.config.mjs`. Key rules:
- React Hooks rules enforced
- No unused variables (prefix with `_` to ignore)
- Consistent import ordering

## Python

### General Rules

- Follow PEP 8 (enforced by Ruff)
- Line length: 100 characters max
- Use type hints for all public function signatures
- Use async/await for database operations
- Use `dataclasses` or `pydantic` models for structured data, not raw dicts
- Use context managers (`with`) for resource management

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `UserService`, `BaseModel` |
| Functions | snake_case | `get_user`, `create_session` |
| Variables | snake_case | `user_id`, `is_active` |
| Constants | SCREAMING_SNAKE_CASE | `DATABASE_URL` |
| Files | snake_case | `user_service.py` |
| Private members | single leading underscore | `_internal_method` |
| Boolean variables | prefix with `is_`, `has_`, `should_`, `can_` | `is_active`, `has_permission` |

### Type Hints

- Use built-in generics (`list[str]`, `dict[str, int]`) over `typing` module equivalents (Python 3.9+)
- Use `X | None` over `Optional[X]` (Python 3.10+)
- Use `TypeAlias` or `type` statement for complex type definitions

### Function Signatures

```python
# Always use type hints for public functions
async def get_user(user_id: int, session: AsyncSession) -> User | None:
    """Get a user by ID.

    Args:
        user_id: The unique identifier of the user.
        session: Database session.

    Returns:
        The user if found, None otherwise.
    """
    return await session.get(User, user_id)
```

### Pydantic Models

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

class UserResponse(BaseModel):
    """Schema for user API responses."""
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}
```

### Import Order

1. Standard library
2. Third-party packages
3. Local imports

```python
import os
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session, User
from src.schemas.users import UserCreate, UserResponse
```

- Use absolute imports over relative imports
- No wildcard imports (`from module import *`)
- Sort imports with `isort` or `ruff` (isort-compatible)

### Docstrings

- Use Google-style docstrings consistently
- All public modules, classes, and functions must have docstrings

### Formatting

- 4-space indentation, no tabs
- Use trailing commas in multi-line structures
- Use double quotes for strings (Black/Ruff default)
- One blank line between methods, two blank lines between top-level definitions

### Ruff Configuration

Located in `packages/api/pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]  # Errors, pyflakes, isort, pyupgrade
```

## Pre-commit Hooks

The project uses Husky + lint-staged for pre-commit checks:

- **UI files**: Prettier + ESLint
- **Python files**: Ruff format + Ruff check

Hooks run automatically on commit. To skip (not recommended):

```bash
git commit --no-verify
```

## IDE Setup

### VS Code

Recommended extensions:
- ESLint
- Prettier
- Python
- Ruff
- Tailwind CSS IntelliSense

### Settings

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```
