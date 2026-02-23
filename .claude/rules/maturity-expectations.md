# Maturity Expectations

Maturity level governs **implementation quality** -- test coverage, error handling depth, documentation thoroughness, infrastructure complexity. It does **not** govern **workflow phases**. An MVP still follows the full plan-review-build-verify sequence when SDD criteria are met (see `workflow-patterns` skill). The artifacts may be lighter, but they are not skipped.

**Current maturity: MVP** (architected for production growth)

| Concern | MVP |
|---------|-----|
| Testing | Happy path + critical edges |
| Error handling | Basic error responses |
| Security | Auth + input validation |
| Documentation | README + API basics |
| Performance | Profile obvious bottlenecks |
| Code review | Light review |
| Infrastructure | Basic CI + single deploy target |
