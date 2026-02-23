# Agent Workflow Discipline

This rule applies to all agents. It operationalizes two practices that prevent AI-generated code from becoming unreviewed tech debt: **task chunking** (keeping autonomous work small enough to succeed) and **context engineering** (loading only what's relevant).

## Task Chunking Heuristics

### Why Chunking Matters

At 95% per-step reliability, a 20-step autonomous chain succeeds only ~36% of the time (0.95^20). Errors compound — each step that builds on a flawed prior step makes recovery harder. Small, verifiable chunks reset the error chain.

### Constraints

| Dimension | Limit | Rationale |
|-----------|-------|-----------|
| **Files touched** | 3–5 per task | More than 5 files signals over-scoping or a cross-cutting concern that needs a design phase first |
| **Autonomous steps** | 5–7 per chain | Keeps compound error probability above 70% (0.95^7 ≈ 0.70) |
| **Autonomy duration** | ~1 hour | If an agent can't complete in roughly 1 hour, the task needs splitting |
| **Scope** | Single concern | One endpoint, one migration, one component, one module — not a feature |

### Exit Conditions

Every task must have a **machine-verifiable** exit condition — a command that returns pass/fail:

| Acceptable | Not Acceptable |
|------------|----------------|
| `pytest tests/unit/test_foo.py` | "Implementation is complete" |
| `npx tsc --noEmit` | "Code follows conventions" |
| `curl -s localhost:3000/health \| jq .status` | "Endpoint works correctly" |
| `ruff check src/` | "Code is clean" |

If a task description doesn't include a verification command, add one before starting work. If you can't define one, the task is underspecified — report it rather than guessing.

### When to Split

Split a task if **any** of these apply:

- It touches more than 5 files
- It requires more than 7 sequential steps to complete
- It addresses more than one concern (e.g., "add endpoint AND update schema AND write tests")
- The exit condition requires manual verification (visual inspection, subjective judgment)
- You can't summarize what "done" looks like in one sentence

## Context Engineering

### Context Anchoring

Load only what the task requires:

1. **Task description** — the primary input
2. **Relevant rules** — project conventions that apply to the files being modified
3. **Specific files being modified** — read them before editing
4. **Interface contracts** — if the task references a Technical Design Document, load the relevant contracts

That's it. Don't speculatively load files that "might be related."

### Context Pruning

Before reading a file, articulate why it's relevant to the current task:

| Valid Reason | Invalid Reason |
|-------------|----------------|
| "I need to match the existing pattern in user.service.ts" | "It might have something useful" |
| "The API contract references this type definition" | "I should understand the whole module" |
| "The test imports this fixture" | "Let me read around to get more context" |

### Context Budget

Budget approximately **5 source files** per task. This is a soft limit — occasionally you'll need 6 or 7, but if you're regularly exceeding it, the tasks are too large.

When working within a **Work Unit**, shared context files (loaded for the first task) remain in context for subsequent tasks. Only count task-specific files against the budget for the second task onward — the WU shared context is already loaded.

Context budget does NOT include:
- Rule files (these are short and always relevant)
- The task description itself
- Generated files you're reading for reference (e.g., OpenAPI specs, migration files)

### Context Poisoning Awareness

More context does NOT mean better results. Loading irrelevant files:
- Dilutes attention on the files that matter
- Introduces patterns from unrelated parts of the codebase that may conflict
- Increases the chance of hallucinating connections between unrelated code

### Stale Context Detection

If you discover that the codebase has diverged from what the task description assumed (e.g., a file the task references doesn't exist, an interface has changed, a module has been restructured):

1. **Stop** — don't attempt to reconcile the discrepancy yourself
2. **Report** — describe what the task assumed vs. what you found
3. **Wait** — let the task be revised before proceeding

Working around a stale spec creates code that matches neither the spec nor the codebase. It's always cheaper to update the spec first.

## Session Continuity

### Long Workflows

The full SDD lifecycle will typically exceed a single context window. Plan for this:

- **One artifact per session** is a good target. A session that produces a TD and completes its review is a natural stopping point.
- **Per-phase design** (see workflow-patterns) keeps each session focused. Design Phase 1 in one session, implement in subsequent sessions, then design Phase 2.
- **Memory files** persist cross-session state. Agents with `memory: project` should write key decisions and learnings before their session ends.

### Before Context Compaction

If a session is approaching context limits, capture before compaction:
- Current phase in the SDD lifecycle
- Which artifacts are complete and which are in progress
- Pending decisions or open questions
- Key learnings that haven't been written to memory yet

### Session Boundaries

Structure work so each session completes a meaningful unit:
- Product plan + its review
- Architecture + its review
- Requirements + its review
- Phase N TD + its review
- Phase N WB + its review
- Phase N implementation (subset of stories)

Avoid starting an artifact review in the same session that will need to apply triage changes -- this often pushes past context limits.
