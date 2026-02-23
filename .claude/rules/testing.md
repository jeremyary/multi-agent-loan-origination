# Testing Standards

## Requirements

These targets apply at **MVP** and **Production** maturity. At **PoC** maturity, focus on smoke tests for critical paths — see the maturity expectations table in the root CLAUDE.md.

- All new code must include tests before merge
- Bug fixes must include a regression test that fails without the fix
- Minimum coverage target: 80% line coverage for new code (MVP/Production)

## Test Frameworks

| Package | Framework | Location |
|---------|-----------|----------|
| UI | Vitest + React Testing Library | `packages/ui/src/**/*.test.tsx` (co-located) |
| API | Pytest | `packages/api/tests/` |
| DB | Pytest | `packages/db/tests/` |

## When to Add Tests

### Always Add Tests When

- Creating a component with user interactions or conditional logic
- Adding a new API endpoint
- Implementing business logic in hooks or utilities
- Fixing a bug (add regression test)
- Adding database models with custom methods

### Skip Tests When

- Creating purely presentational components with no logic
- Making trivial changes (typos, formatting)
- Prototyping or exploring (add tests before merging)

## Test Naming
Format: `should <expected behavior> when <condition>`

```
should return 404 when user is not found
should validate email format when registering
should retry on transient network failure
```

## Structure

- Follow Arrange-Act-Assert (AAA) pattern:

```python
def test_user_creation(client):
    # Arrange
    user_data = {"name": "Test", "email": "test@example.com"}

    # Act
    response = client.post("/users/", json=user_data)

    # Assert
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

- One assertion concept per test (multiple assertions OK if testing one behavior)
- Use descriptive test group names that read as specifications

## Isolation
- Tests must not depend on execution order
- Tests must not share mutable state
- Mock external services and I/O at boundaries
- Use factories or fixtures for test data, not raw literals
- Clean up any resources created during tests

## Types
- **Unit tests:** Test individual functions/modules in isolation
- **Integration tests:** Test module interactions and API boundaries
- **End-to-end tests:** Test critical user flows through the full stack

## Files
- Co-locate unit tests with source: `foo.ts` -> `foo.test.ts`, `foo.py` -> `test_foo.py`
- Integration/e2e tests in dedicated `tests/` directory

## UI Testing (Vitest)

### Test File Location

Co-locate tests with components:

```
components/
├── button/
│   ├── button.tsx
│   ├── button.test.tsx    # Tests here
│   └── button.stories.tsx
```

### Basic Component Test

```typescript
// button.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Button } from './button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    await userEvent.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### Testing with Providers

Use the test utilities for components requiring context:

```typescript
// test/test-utils.tsx provides renderWithProviders
import { renderWithProviders } from '@/test/test-utils';

it('fetches and displays data', async () => {
  renderWithProviders(<UserList />);

  await waitFor(() => {
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });
});
```

### Testing Hooks

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useUsers } from '@/hooks/users';
import { createWrapper } from '@/test/test-utils';

it('fetches users', async () => {
  const { result } = renderHook(() => useUsers(), {
    wrapper: createWrapper(),
  });

  await waitFor(() => {
    expect(result.current.isSuccess).toBe(true);
  });

  expect(result.current.data).toHaveLength(3);
});
```

### UI Test Commands

```bash
# Run tests (watch mode)
pnpm --filter ui test

# Run once
pnpm --filter ui test:run

# With coverage
pnpm --filter ui test:coverage

# Run specific file
pnpm --filter ui test button.test.tsx
```

## API Testing (Pytest)

### Test File Location

Tests go in `packages/api/tests/`:

```
tests/
├── conftest.py        # Shared fixtures
├── helpers.py         # Test utilities
├── test_health.py     # Health endpoint tests
└── test_users.py      # User endpoint tests
```

### Fixtures (conftest.py)

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)

@pytest.fixture
def health_response(client):
    """Get health check response data."""
    response = client.get("/health/")
    assert response.status_code == 200
    return response.json()
```

### Basic API Test

```python
# test_users.py
def test_create_user(client):
    """Test creating a new user."""
    response = client.post("/users/", json={
        "name": "Test User",
        "email": "test@example.com"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_create_user_invalid_email(client):
    """Test validation rejects invalid email."""
    response = client.post("/users/", json={
        "name": "Test User",
        "email": "not-an-email"
    })

    assert response.status_code == 422


def test_get_nonexistent_user(client):
    """Test 404 for missing user."""
    response = client.get("/users/99999")

    assert response.status_code == 404
```

### Using Test Helpers

```python
# helpers.py
def find_service(services: list, name: str) -> dict | None:
    """Find a service by name in health check response."""
    return next((s for s in services if s["name"] == name), None)

def assert_service_exists(services: list, name: str) -> dict:
    """Assert a service exists and return it."""
    service = find_service(services, name)
    assert service is not None, f"Service '{name}' not found"
    return service

# In tests
from helpers import assert_service_exists

def test_api_service_healthy(health_response):
    api = assert_service_exists(health_response, "API")
    assert api["status"] == "healthy"
```

### API Test Commands

```bash
# Run all tests
pnpm --filter api test

# From packages/api
cd packages/api
uv run pytest                    # All tests
uv run pytest -v                 # Verbose
uv run pytest -k "test_health"   # Pattern match
uv run pytest --tb=short         # Short tracebacks
```

## Test Patterns

### Test Edge Cases

- Empty inputs
- Invalid inputs
- Boundary values
- Error conditions
- Missing resources (404)
- Unauthorized access (401/403)

### Mock External Dependencies

```typescript
// Vitest
vi.mock('@/services/users', () => ({
  fetchUsers: vi.fn().mockResolvedValue([{ id: 1, name: 'Test' }]),
}));

// Pytest
from unittest.mock import patch

@patch('src.services.external_api.fetch')
def test_with_mock(mock_fetch, client):
    mock_fetch.return_value = {"data": "mocked"}
    # ... test code
```

## Running All Tests

```bash
# From root
pnpm test          # All packages
make test          # Same via Makefile

# Specific packages
pnpm --filter ui test
pnpm --filter api test
```
