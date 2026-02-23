# Review Governance

This rule establishes review discipline for AI-native development. It prevents rubber-stamping, enforces plan-review-first for non-trivial work, and limits PR size to what humans can meaningfully review.

## Plan Review First

> Correcting a plan takes minutes; refactoring bad code takes days.

For features with **3+ implementation tasks**, all planning artifacts must be reviewed before downstream work begins: Product Plan, Architecture, Requirements, Technical Design, and Work Breakdown. Each has a review checklist below. These are the highest-leverage reviews in the entire workflow — catching a spec error is always cheaper than refactoring the implementation.

### Product Plan Review Checklist

| Check | What to Look For |
|-------|-----------------|
| **No technology names in feature descriptions** | Features describe capabilities ("document storage", "real-time chat"), not solutions ("MinIO", "WebSockets", "LangGraph"). Technology mandates from stakeholders should be in a Constraints section, not woven into features. |
| **MoSCoW prioritization used** | Features classified as Must/Should/Could/Won't — not organized as numbered epics with dependency maps |
| **No epic or story breakout** | Features are described and prioritized, not decomposed into implementation work items. No dependency graphs, entry/exit criteria, or agent assignments. |
| **NFRs are user-facing** | Quality expectations framed as user outcomes ("feels responsive"), not implementation targets ("< 200ms Redis cache hit") |
| **User flows present** | Key persona journeys through the system are documented — not just feature lists |
| **Phasing describes capability milestones** | Each phase describes what the system can do, not which epics/stories are included |

### Architecture Review Checklist

| Check | What to Look For |
|-------|-----------------|
| **Component boundaries are clear** | Each component has a defined responsibility and interface surface. No overlapping concerns or ambiguous ownership. |
| **Technology decisions include trade-off analysis** | Each technology choice documents alternatives considered, why it was selected, and known risks. No unjustified choices. |
| **Integration patterns are explicit** | How components communicate (sync/async, protocols, data formats) is documented, not assumed. |
| **Deployment model addresses operational concerns** | Scaling, failover, data persistence, and environment strategy are addressed — not deferred to "later". |
| **ADRs present for significant decisions** | Architectural Decision Records exist for choices that constrain downstream work or are hard to reverse. |
| **No product scope changes** | Architecture stays within the feature set defined by the product plan. New capabilities or features are not introduced. |
| **No detailed API contracts or implementation details** | Component interfaces are described at the boundary level. Full API specs, handler logic, and task breakdown belong to downstream phases. |

### Requirements Review Checklist

| Check | What to Look For |
|-------|-----------------|
| **Stories trace to product plan features** | Every user story maps to a feature from the product plan. No orphan stories that introduce unplanned scope. |
| **Given/When/Then acceptance criteria present** | Every story has concrete, testable acceptance criteria — not vague descriptions like "user can manage items". |
| **Edge cases and error paths documented** | Not just happy paths. Negative scenarios, boundary conditions, invalid input, and concurrent operation cases are covered. |
| **NFRs are measurable** | Non-functional requirements have concrete thresholds ("page load < 2s"), not vague qualities ("fast", "secure"). |
| **Consistent with architecture boundaries** | Stories don't assume component interactions or data flows that contradict the architecture document. |
| **No architecture decisions embedded** | Requirements describe WHAT the system does, not HOW. No technology choices, component assignments, or data model decisions. |
| **No task breakdown or implementation approach** | Requirements don't size work, assign agents, or prescribe implementation steps. That scope belongs to Technical Design and Work Breakdown. |

### Technical Design Review Checklist

| Check | What to Look For |
|-------|-----------------|
| **Contracts are concrete** | Actual JSON shapes, actual type definitions, actual file paths — not "use a clean pattern" |
| **Data flow covers error paths** | Happy path AND what happens when things fail at each boundary |
| **Exit conditions are machine-verifiable** | Every task has a command that returns pass/fail (see `agent-workflow.md`) |
| **File structure maps to actual codebase** | Proposed paths match existing project layout — not an idealized structure |
| **No TBDs in binding contracts** | If something is undefined, it must be flagged as an open question, not left as "TBD" |

### Work Breakdown Review Checklist

| Check | What to Look For |
|-------|-----------------|
| **Story-to-WU mapping is 1:1** | Every work unit from the TD maps to exactly one story. No scope drift in story descriptions -- they should be faithful to TD intent, not reinterpreted. |
| **Dependencies are technically accurate** | Story dependencies match actual technical dependencies from the TD's dependency graph. Phase ordering is NOT the same as technical dependency -- flag over-strict chains that block parallelism unnecessarily. |
| **Exit conditions are machine-verifiable** | Every story has a runnable command that returns pass/fail. No "implementation is complete", no "review by X agent", no manual verification. See `agent-workflow.md`. |
| **Chunking heuristics respected** | Stories target 3-5 files, single concern. Stories exceeding these limits should be flagged for splitting. |
| **No methodology or effort estimation assumptions** | No sprints, velocity, capacity planning, or effort/time estimates (hours, person-days). Work breakdowns organize by dependency order and parallelism. Sprint planning requires a defined team. Effort estimation requires knowledge of who is doing the work. Agents must not fabricate either. Relative complexity sizing (story points, T-shirt sizes) is allowed -- it measures difficulty, not duration. |

### When to Skip Plan Review

Plan review can be skipped when:
- The feature has 1–2 implementation tasks (single-concern, single-implementer)
- The work is a bug fix with a clear root cause
- The change is purely additive (new test, new documentation) with no interface changes

### Anti-Self-Approval Principle

The creating agent must not be the sole reviewer of its own planning artifacts. Each planning phase has a designated reviewer with complementary expertise:

| Artifact | Creator | Reviewer(s) |
|----------|---------|-------------|
| Product Plan | Product Manager | Architect, Security Engineer |
| Architecture | Architect | Code Reviewer, Security Engineer |
| Requirements | Requirements Analyst | Product Manager, Architect |
| Technical Design | Tech Lead | Code Reviewer, Security Engineer |
| Work Breakdown | Project Manager | Tech Lead |

This ensures every artifact is validated by an agent whose expertise covers the creator's blind spots. The PM lacks implementation depth to validate its own dependency chains and exit conditions. The Architect lacks security depth to validate its own threat surface. Skipping review for a planning artifact because "it doesn't introduce new interfaces" misses the point -- every planning artifact makes decisions that downstream agents must live with.

## Orchestrator Review

At each SDD plan review gate (Phases 2, 5, 8, 10), the main session performs its own review **in parallel** with the specialist agents. The orchestrator acts as a safety net for cross-cutting issues that fall between specialist scopes.

### Focus Areas

| Area | What to Look For |
|------|-----------------|
| **Cross-cutting coherence** | Do the parts of this artifact tell a consistent story, or do sections contradict each other? |
| **Scope discipline** | Does the artifact stay within its phase's scope boundaries (see `workflow-patterns` SDD Scope Discipline table), or does it make decisions that belong to a downstream phase? |
| **Assumption gaps** | Are there unstated assumptions that two specialists might interpret differently? |
| **Compounding scope creep** | Has the cumulative scope grown beyond what the product plan authorized? Compare the artifact against the original feature set. |
| **Downstream feasibility** | Will downstream agents (implementers, testers, project manager) be able to act on this artifact without ambiguity? |
| **Review coverage gaps** | Is there a concern that no specialist reviewer is scoped to catch? Flag it explicitly. |

### How It Differs from Specialist Reviews

The orchestrator does **not** duplicate specialist work. It reads with the question: *"What would I miss if I only read the specialist reviews?"* Specialists evaluate depth within their domain; the orchestrator evaluates breadth across domains.

### Output Format

- Same severity levels as specialist reviews: **Critical**, **Warning**, **Suggestion**, **Positive**
- Same verdict options: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- The **Mandatory Findings Rule** applies — at least one Suggestion or Positive finding per review
- Output path: `plans/reviews/<artifact>-review-orchestrator.md`

## Code Review Anti-Rubber-Stamping

### PR Size Guidance

AI-generated PRs should target **~400 lines of changed code** (excluding tests and generated files). Beyond this threshold, meaningful human review is impractical — reviewers begin skimming rather than reading.

| PR Size (changed lines) | Review Quality |
|--------------------------|---------------|
| < 200 | Thorough review feasible |
| 200–400 | Careful review feasible with focused attention |
| 400–800 | Reviewer fatigue sets in; split if possible |
| > 800 | Meaningful review is impractical — must split |

If a task produces more than 400 lines of changes, the task was likely over-scoped. Split it for the next iteration.

### Mandatory Findings Rule

A review that produces zero findings and an APPROVE is suspicious. There is always at least one improvement — a clearer name, a missing edge case, a test that could be stronger, a comment that would help the next reader. Zero findings suggests the review was skimmed, not read.

Acceptable minimum: at least one **Suggestion** or **Positive** finding per review, even if the overall verdict is APPROVE.

### Two-Agent Review

The following code categories require review by **both** `@code-reviewer` and `@security-engineer`:

- Authentication and authorization logic
- Cryptographic operations and secrets handling
- Data deletion or hard-delete operations
- Input validation at system boundaries (user input, external API responses)
- Database migration with data transformation

For all other code, `@code-reviewer` alone is sufficient. Add `@security-engineer` whenever you're unsure.

### "Explain It to Me" Protocol

When a reviewer flags a finding, the implementing agent must:

1. **Summarize the finding in its own words** — not quote the reviewer's text
2. **Explain what it will change and why** — demonstrate understanding, not just compliance
3. **Make the fix**

This prevents pattern-matching fixes where the agent changes code to look different without understanding the underlying issue.

## Review Scope Rules

### Scope Matching

Review must match task scope. If a PR contains changes to files that weren't in the original task description:

- Those out-of-scope changes are **themselves a finding** (Warning severity)
- The reviewer should flag them and ask for justification
- Unjustified out-of-scope changes should be reverted and handled in a separate task

### Test Review

Test review is **not optional**. Reviewers must verify:

- Tests cover the behavior described in the task's exit conditions
- Tests include at least one error/edge case — happy-path-only tests are a **Warning** finding
- Test names describe the behavior being verified (see `testing.md` naming convention)
- Tests are deterministic — no timing dependencies, no order dependencies, no shared mutable state

### Repeat Pattern Detection

If `@code-reviewer` flags the **same pattern** 3+ times across different reviews in the same project, that pattern should be promoted to a project rule:

1. Document the pattern in the relevant rule file (e.g., `code-style.md`, `security.md`)
2. Add a brief rationale for why it matters
3. Future reviews can reference the rule instead of re-explaining

This prevents review fatigue from repeatedly flagging the same issue and ensures institutional knowledge is captured.

## Review Resolution Process

After reviews complete at any review gate, the orchestrator follows this process to resolve findings:

### 1. Parallel Reviews + Orchestrator Assessment

Launch designated reviewers in parallel. While reviews run, the orchestrator (main session) reads the artifact independently and prepares its own assessment. The orchestrator assessment catches issues that specialist reviewers miss and provides a generalist perspective.

### 2. Consolidate into Triage Table

Use `/consolidate-reviews` to merge all review files into a single de-duplicated triage table. Example: `/consolidate-reviews plans/reviews/requirements-review-*.md`. The skill reads all matching review files, de-duplicates findings, surfaces disagreements, and outputs a structured triage document.

Findings are classified by disposition:

| Disposition | Meaning |
|-------------|---------|
| **Fix** | Must be addressed before proceeding. Incorrect, inconsistent, or violates a project rule. |
| **Improvement** | Would make the artifact better but not blocking. Apply if approved. |
| **Defer** | Valid concern but out of scope for this artifact. Track for future work. |
| **Positive** | Something done well. Noted for pattern reinforcement. |

Each row includes: source (which reviewer), finding ID, severity, disposition, and a concise description of both the problem and the recommended change.

### 3. User Approval

Present the full triage table to the user. The user approves, modifies, or rejects individual items. No changes are applied without explicit user approval.

### 4. Batch Application

Launch the appropriate agent to apply all approved changes in a single pass. This is more efficient and consistent than applying changes one at a time.

### 5. Spot-Check and Commit

Verify key changes with targeted searches (grep for removed patterns, check critical edits). Then commit, push, and create PR.
