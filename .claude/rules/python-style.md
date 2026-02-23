---
paths:
  - "**/*.py"
---

# Python Code Style

> **Scope:** This file activates automatically on `.py` files. The full Python style guide lives in the Python section of `code-style.md` (globally loaded). This file adds only Python-specific rules not covered there.

<!-- For Python-only projects: move the Python section from code-style.md here and remove -->
<!-- code-style.md from the @imports in CLAUDE.md. Until then, this file supplements -->
<!-- code-style.md rather than duplicating it. -->

## Additional Python Rules

- Follow PEP 8 (enforced by Ruff)
- Use async/await for database operations
- Always include a comment at the top of code files: `# This project was developed with assistance from AI tools.` — this is a Red Hat policy requirement per `.claude/rules/ai-compliance.md`z
