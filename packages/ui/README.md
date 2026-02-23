# ai-quickstart-template UI

React frontend application architecture and development guide.

> **Setup & Installation**: See the [root README](../../README.md) for installation and quick start instructions.

## Architecture Overview

This UI package uses a modern React stack with file-based routing and component-driven development:

```
User Request → TanStack Router → Route Component → TanStack Query → API Service → Backend
                                                      ↓
                                                 Local State
                                                      ↓
                                                 UI Components
```

### Key Architectural Patterns

- **File-Based Routing**: TanStack Router automatically generates routes from `src/routes/` directory structure
- **Component Organization**: Atomic design pattern (atoms → molecules → organisms)
- **Server State**: TanStack Query for API data fetching, caching, and synchronization
- **Type Safety**: Full TypeScript with generated route types
- **Code Splitting**: Automatic route-based code splitting for optimal performance
- **Component Development**: Storybook for isolated component development and documentation

- **API Integration**: Service layer with hooks for type-safe API calls

## Directory Structure

```
src/
├── main.tsx                    # Application entry point, router setup
├── components/                 # Reusable UI components
│   ├── atoms/                  # Basic building blocks
│   │   ├── card/              # Card component
│   │   ├── badge/             # Badge component
│   │   ├── button/            # Button component
│   │   ├── separator/         # Separator component
│   │   ├── tooltip/           # Tooltip component
│   │   └── dropdown-menu/      # Dropdown menu component
│   ├── logo/                  # Logo component
│   ├── hero/                  # Hero component
│   ├── quick-stats/           # Quick stats component
│   ├── stat-card/             # Stat card component
│   ├── status-panel/           # Status panel component
│   ├── service-card/          # Service card component
│   ├── service-list/          # Service list component
│   ├── footer/                # Footer component
│   ├── header/                # Header component
│   ├── theme-provider/        # Theme provider component
│   ├── mode-toggle/           # Mode toggle component
│   └── lib/                   # Component utilities (cn helper)
├── routes/                     # File-based routes (TanStack Router)
│   ├── __root.tsx            # Root layout with router provider
│   ├── index.tsx             # Home page route
│   └── routeTree.gen.ts      # Auto-generated route tree (do not edit)
├── services/                   # API service layer (when API enabled)
│   └── health.ts              # Example: Health check service
├── hooks/                      # Custom React hooks (when API enabled)
│   └── health.ts              # Example: useHealth hook
├── schemas/                    # Zod schemas for API validation (when API enabled)
│   └── health.ts              # Example: Health response schema
└── styles/
    └── globals.css            # Global styles, Tailwind imports

.storybook/                     # Storybook configuration
public/                         # Static assets
components.json                 # shadcn/ui CLI configuration
```

### Directory Purposes

- **`src/main.tsx`**: Application entry point. Initializes React Router and renders the root route. Typically doesn't need modification.

- **`src/routes/`**: File-based routing directory. Each file becomes a route:
  - `__root.tsx`: Root layout component (wraps all routes)
  - `index.tsx`: Home page (`/`)
  - `about.tsx`: Creates `/about` route
  - `users/$userId.tsx`: Creates `/users/:userId` dynamic route
  - Routes are automatically code-split and type-safe

- **`src/components/`**: Reusable UI components:
  - **`atoms/`**: Basic, indivisible components organized in subdirectories (Card, Badge, Button, Separator, Tooltip, DropdownMenu)
  - **Other components**: More complex components directly in `components/` (Logo, Hero, QuickStats, StatCard, StatusPanel, ServiceCard, ServiceList, Footer, Header, ThemeProvider, ModeToggle)
  - Each component has its own directory containing the component file and optionally a Storybook story

- **`src/services/`**: API client functions. Each service file exports pure functions that make API calls and return promises. These functions handle HTTP requests, response parsing, and schema validation. **Services should never be called directly from components**—they are only used by hooks.

- **`src/hooks/`**: Custom React hooks that pair with services in `services/`. These hooks wrap TanStack Query's `useQuery` and `useMutation` hooks, extending their functionality with domain-specific logic (data transformation, computed values, UI-specific enhancements). **Components should always use hooks instead of calling React Query hooks or services directly.** This pattern provides a clean abstraction layer and ensures consistent behavior across the application.

- **`src/schemas/`**: Zod schemas for runtime validation of API responses. Ensures type safety at runtime and provides excellent TypeScript inference.

- **`src/styles/`**: Global styles and Tailwind CSS configuration. Tailwind utilities are used directly in components.

- **`components.json`**: Configuration file for the shadcn/ui CLI. Pre-configured to install components into `src/components/atoms/`. See [shadcn/ui components.json documentation](https://ui.shadcn.com/docs/components-json) for details.

## Adding New Routes

TanStack Router uses file-based routing. To add a new route:

### 1. Create Route File

Create a new file in `src/routes/`:

```typescript
// src/routes/about.tsx
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/about')({
  component: About,
});

function About() {
  return (
    <div className="container mx-auto p-4">
      <h1>About</h1>
      <p>About page content</p>
    </div>
  );
}
```

### 2. Dynamic Routes

For routes with parameters:

```typescript
// src/routes/users/$userId.tsx
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/users/$userId')({
  component: UserDetail,
});

function UserDetail() {
  const { userId } = Route.useParams();
  return <div>User ID: {userId}</div>;
}
```

### 3. Route Tree Regeneration

After creating routes, regenerate the route tree:

```bash
pnpm dev  # Route tree auto-generates during dev
# or manually:
pnpm exec tsr generate
```

The route tree is automatically generated in `src/routes/routeTree.gen.ts`. Do not edit this file manually.

## Adding New Components

### Using shadcn/ui CLI (Recommended for Atoms)

This project includes a `components.json` configuration file that's pre-configured to install shadcn/ui components into the `atoms/` folder. You can use the shadcn/ui CLI to quickly add atomic components:

```bash
# Add a component from shadcn/ui
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add dialog
```

Components will be automatically installed to `src/components/atoms/` based on the `components.json` configuration.

See the [shadcn/ui components documentation](https://ui.shadcn.com/docs/components) for a full list of available components.

**Note**: The `components.json` file configures `aliases.ui` to point to `@/components/atoms`, ensuring all shadcn/ui components are installed in the atoms folder.

### Manual Component Creation

For custom components or components not available in shadcn/ui, create them manually:

#### 1. Create Component Directory

Create a directory in the appropriate location. For basic atomic components, use `atoms/`. For more complex components, place them directly in `components/`:

```typescript
// src/components/atoms/input/input.tsx
import { cn } from '../../lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className, ...props }: InputProps) {
  return (
    <div>
      {label && <label>{label}</label>}
      <input
        className={cn(
          'rounded border px-3 py-2',
          className
        )}
        {...props}
      />
    </div>
  );
}
```

#### 2. Create Storybook Story

Create a story file for component development:

```typescript
// src/components/atoms/input/input.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Input } from './input';

const meta: Meta<typeof Input> = {
  title: 'Atoms/Input',
  component: Input,
};

export default meta;
type Story = StoryObj<typeof Input>;

export const Default: Story = {
  args: {
    placeholder: 'Enter text...',
  },
};

export const WithLabel: Story = {
  args: {
    label: 'Email',
    type: 'email',
    placeholder: 'user@example.com',
  },
};
```

#### 3. Export Component

Add to component index if using barrel exports:

```typescript
// src/components/atoms/index.ts
export { Input } from './input/input';
```

### Component Organization Principles

- **Atoms** (`components/atoms/`): Basic, single-purpose components (Card, Badge, Button, Separator, Tooltip, DropdownMenu)
- **Complex Components** (`components/`): More complex components directly in the components directory (Logo, Hero, QuickStats, StatCard, StatusPanel, ServiceCard, ServiceList, Footer, Header, ThemeProvider, ModeToggle)
- **Keep components focused**: One component, one responsibility
- **Use TypeScript interfaces**: Define props explicitly
- **Leverage Tailwind**: Use utility classes, avoid custom CSS when possible
- **Component directories**: Each component has its own directory containing the component file and optionally a Storybook story

## Hooks and Services Pattern

This project follows a **hooks/services pattern** that separates concerns and provides a clean abstraction layer for API integration:

### Architecture

```
Component → Hook → React Query → Service → API
              ↓
         Extended Logic
         (transformations,
          computed values,
          UI enhancements)
```

### Pattern Overview

1. **Services** (`src/services/`): Pure functions that make API calls
   - Handle HTTP requests and responses
   - Parse and validate data with Zod schemas
   - Return typed promises
   - **Never called directly from components**

2. **Hooks** (`src/hooks/`): Custom React hooks that pair with services
   - Wrap TanStack Query's `useQuery` and `useMutation`
   - Extend functionality with domain-specific logic
   - Provide enhanced data transformations
   - **Components should always use hooks, never services or React Query hooks directly**

### Why This Pattern?

- **Separation of Concerns**: Services handle API communication, hooks handle React state
- **Reusability**: Hooks can extend services with UI-specific logic without modifying services
- **Consistency**: All components use the same hook interface
- **Type Safety**: Full TypeScript support with inferred types
- **Testability**: Services and hooks can be tested independently

### Example: Extending React Query Functionality

Hooks can extend React Query hooks with additional functionality:

```typescript
// src/hooks/users.ts
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getUsers } from '../services/users';
import { User } from '../schemas/users';

export const useUsers = (): UseQueryResult<User[], Error> & {
  activeUsers: User[];
  totalCount: number;
} => {
  const queryResult = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
  });

  // Extend with computed values
  const activeUsers = useMemo(() => {
    return queryResult.data?.filter(user => user.isActive) ?? [];
  }, [queryResult.data]);

  const totalCount = useMemo(() => {
    return queryResult.data?.length ?? 0;
  }, [queryResult.data]);

  // Return extended query result
  return {
    ...queryResult,
    activeUsers,
    totalCount,
  };
};
```

Components can now use the extended hook:

```typescript
function Users() {
  const { data: users, activeUsers, totalCount, isLoading } = useUsers();
  
  // Use both original data and computed values
  return (
    <div>
      <p>Total: {totalCount}</p>
      <p>Active: {activeUsers.length}</p>
      {/* ... */}
    </div>
  );
}
```

### Mutation Hooks

For mutations, use `useMutation`:

```typescript
// src/services/users.ts
export const createUser = async (userData: CreateUserInput): Promise<User> => {
  const response = await fetch('/api/users/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  if (!response.ok) {
    throw new Error('Failed to create user');
  }
  const data = await response.json();
  return UserSchema.parse(data);
};

// src/hooks/users.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createUser } from '../services/users';

export const useCreateUser = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      // Invalidate and refetch users list
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};
```

### Best Practices

- ✅ **Always create a hook** for each service function
- ✅ **Extend hooks** with domain-specific logic when needed
- ✅ **Use hooks in components**, never services or React Query hooks directly
- ✅ **Pair hooks with services**—one hook file per service file
- ✅ **Return extended query results** when adding computed values
- ❌ **Don't call services directly** from components
- ❌ **Don't use React Query hooks directly** in components (use custom hooks instead)
- ❌ **Don't put API logic** in hooks (keep it in services)


## Adding API Integration

When the API package is enabled, follow this pattern to add new API integrations:

### 1. Create Zod Schema

Define the response schema for runtime validation:

```typescript
// src/schemas/users.ts
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.number(),
  email: z.string().email(),
  name: z.string(),
  isActive: z.boolean().default(true),
});

export type User = z.infer<typeof UserSchema>;
```

### 2. Create Service Function

Create an API service function that handles the HTTP request:

```typescript
// src/services/users.ts
import { UserSchema, User } from '../schemas/users';
import { z } from 'zod';

export const getUsers = async (): Promise<User[]> => {
  const response = await fetch('/api/users/');
  if (!response.ok) {
    throw new Error('Failed to fetch users');
  }
  const data = await response.json();
  return z.array(UserSchema).parse(data);
};

export const getUser = async (id: number): Promise<User> => {
  const response = await fetch(`/api/users/\${id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch user');
  }
  const data = await response.json();
  return UserSchema.parse(data);
};
```

### 3. Create Hook

Create a custom hook that wraps TanStack Query and pairs with the service:

```typescript
// src/hooks/users.ts
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { getUsers, getUser } from '../services/users';
import { User } from '../schemas/users';

// Simple query hook
export const useUsers = (): UseQueryResult<User[], Error> => {
  return useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
  });
};

// Query hook with parameter
export const useUser = (id: number): UseQueryResult<User, Error> => {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => getUser(id),
    enabled: !!id, // Only fetch when id is provided
  });
};
```

### 4. Use Hook in Components

**Always use hooks in components, never services or React Query hooks directly:**

```typescript
// src/routes/users.tsx
import { createFileRoute } from '@tanstack/react-router';
import { useUsers } from '../hooks/users';

export const Route = createFileRoute('/users')({
  component: Users,
});

function Users() {
  // ✅ Good: Use the custom hook
  const { data: users, isLoading, error } = useUsers();

  // ❌ Bad: Don't use the service directly
  // const users = await getUsers();

  // ❌ Bad: Don't use React Query hooks directly
  // const { data } = useQuery({ queryKey: ['users'], queryFn: getUsers });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {users?.map(user => (
        <div key={user.id}>{user.name}</div>
      ))}
    </div>
  );
}
```

### API Integration Patterns

- **Service Layer**: Keep API calls in `services/`, not in components or hooks
- **Hooks Layer**: Wrap TanStack Query in hooks, extend with domain logic
- **Component Layer**: Always use hooks, never services or React Query hooks directly
- **Schema Validation**: Always validate API responses with Zod schemas in services
- **Error Handling**: Handle loading and error states in components
- **Type Safety**: Infer TypeScript types from Zod schemas
- **Pairing**: One hook file per service file, hooks pair with their corresponding services

## State Management

### Server State (TanStack Query)

Use TanStack Query for all server state (API data):

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['resource', id],
  queryFn: () => fetchResource(id),
});
```

**Benefits:**
- Automatic caching and refetching
- Loading and error states
- Background updates
- Optimistic updates support

### Local State (React useState)

Use React's `useState` for component-local state:

```typescript
const [isOpen, setIsOpen] = useState(false);
```

**When to use:**
- UI state (modals, dropdowns, form inputs)
- Temporary state that doesn't need persistence
- State that doesn't need to be shared across components

### Global State

For shared state across components, consider:
- **TanStack Query**: For server state (preferred)
- **React Context**: For theme, auth, etc.
- **URL State**: For filters, search params (via TanStack Router)

## Styling Architecture

### Tailwind CSS

This project uses Tailwind CSS with a utility-first approach:

```typescript
<div className="container mx-auto p-4 bg-white dark:bg-gray-900">
  <h1 className="text-2xl font-bold">Title</h1>
</div>
```

### Component Styling Patterns

**Utility Classes (Preferred):**
```typescript
<button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
  Click me
```

**Component Variants (with cn helper):**
```typescript
import { cn } from '../lib/utils';

<button className={cn(
  'px-4 py-2 rounded',
  variant === 'primary' && 'bg-blue-500 text-white',
  variant === 'secondary' && 'bg-gray-200 text-gray-800'
)}>
  Click me
</button>
```

### Best Practices

- Use Tailwind utilities for styling
- Create reusable component variants when needed
- Use `cn()` helper for conditional classes
- Follow mobile-first responsive design
- Use semantic HTML elements for accessibility

## Essential Scripts

```bash
# Development
pnpm dev                # Start dev server + Storybook

# Building
pnpm build              # Production build
pnpm type-check         # TypeScript check

# Testing
pnpm test               # Run tests with Vitest
pnpm test --run         # Run tests once (no watch mode)

# Code Quality
pnpm lint               # ESLint
pnpm format             # Prettier

# Storybook
pnpm dev:storybook      # Storybook dev server
```

## Testing

This package uses **Vitest** with **React Testing Library** for component testing.

### Test Structure

```
src/
├── test/
│   └── setup.ts           # Test setup (jest-dom)
└── components/
    └── hero/
        ├── hero.tsx       # Component
        └── hero.test.tsx  # Component tests (co-located)
```

### Writing Tests

```typescript
// src/components/example/example.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Example } from './example';

describe('Example', () => {
  it('renders correctly', () => {
    render(<Example />);
    expect(screen.getByText('Expected text')).toBeInTheDocument();
  });
});
```

### Best Practices

- **Co-locate tests**: Place `*.test.tsx` files next to their components
- **Test behavior**: Focus on what users see and do, not implementation details
- **Use Testing Library queries**: Prefer `getByRole`, `getByText` over `getByTestId`
- **Keep tests focused**: One behavior per test

---

Generated with [AI QuickStart CLI](https://github.com/TheiaSurette/quickstart-cli)
