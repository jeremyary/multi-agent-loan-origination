---
description: "Code style and formatting conventions"
alwaysApply: true
---

# Code Style Guidelines

## Automated Formatting

Run before committing:

```bash
pnpm lint        # Check all packages
pnpm lint:fix    # Auto-fix issues
pnpm format      # Format with Prettier
```

## TypeScript (UI Package)

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `UserProfile`, `NavBar` |
| Hooks | camelCase with `use` prefix | `useAuth`, `useUsers` |
| Functions | camelCase | `fetchUser`, `handleClick` |
| Constants | SCREAMING_SNAKE_CASE | `API_BASE_URL` |
| Files | kebab-case | `user-profile.tsx` |

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

### Import Order

1. React and external libraries
2. Internal aliases (@/ paths)
3. Relative imports
4. Styles

```typescript
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/atoms/button';
import { useAuth } from '@/hooks/auth';

import { formatDate } from './utils';
```

## Python (API/DB Packages)

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user` |
| Variables | snake_case | `user_id` |
| Constants | SCREAMING_SNAKE_CASE | `DATABASE_URL` |
| Files | snake_case | `user_service.py` |

### Function Signatures

```python
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

from fastapi import APIRouter, Depends
from sqlalchemy import select

from db import get_session, User
from src.schemas.users import UserCreate
```

## Pre-commit Hooks

Husky + lint-staged runs automatically:

- **UI files**: Prettier + ESLint
- **Python files**: Ruff format + Ruff check

## Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```
