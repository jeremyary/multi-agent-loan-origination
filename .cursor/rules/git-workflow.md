---
description: "Git workflow and commit conventions"
alwaysApply: true
---

# Git Workflow

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |

### Scopes

| Scope | Description |
|-------|-------------|
| `ui` | Frontend package |
| `api` | Backend package |
| `db` | Database package |
| `deploy` | Deployment/Helm |
| `deps` | Dependencies |

### Examples

```bash
feat(ui): add dark mode toggle to header
fix(api): handle null email in user creation
feat(api)!: change user endpoint response format

BREAKING CHANGE: User responses now include nested profile object
```

### Commitlint

Commit messages are validated. Invalid messages will be rejected:

```bash
# Bad
git commit -m "added feature"

# Good
git commit -m "feat(ui): add user profile page"
```

## Pre-commit Checks

On every commit, Husky runs:

1. **lint-staged**: Format and lint changed files
2. **commitlint**: Validate commit message format

## Pull Request Process

1. **Create feature branch**
   ```bash
   git checkout -b feat/add-user-profile
   ```

2. **Make changes and commit**
   ```bash
   git commit -m "feat(ui): add user profile page"
   ```

3. **Push and create PR**
   ```bash
   git push -u origin feat/add-user-profile
   ```

4. **PR Description**
   ```markdown
   ## Summary
   - Added user profile page
   - Connected to /users/:id endpoint

   ## Test plan
   - [ ] Profile page renders correctly
   - [ ] API errors show error message
   ```

## Semantic Release

Automated versioning based on commits:

- `feat` → minor version (1.0.0 → 1.1.0)
- `fix` → patch version (1.0.0 → 1.0.1)
- `BREAKING CHANGE` → major version (1.0.0 → 2.0.0)
