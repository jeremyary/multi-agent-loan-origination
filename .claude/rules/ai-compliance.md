# Red Hat AI Compliance

This rule codifies Red Hat's policies on the use of AI code assistants. It applies to all
files and all agents. For the full policy context, see the source documents in `docs/` and
the developer checklist at `docs/ai-compliance-checklist.md`.

## Human-in-the-Loop Obligation

- All AI-generated code **must** be reviewed, tested, and validated by a human before merge
- The developer who commits AI-generated code is accountable for its correctness, security, and legal compliance
- AI output is a starting point, not a finished product — treat it as untrusted input that requires verification
- Never merge AI-generated code without running the project's test suite and linter

## Sensitive Data Prohibition

- **Never** input the following into AI prompts or context:
  - Red Hat confidential or proprietary information
  - Customer data or personally identifiable information (PII)
  - Trade secrets, internal architecture details, or infrastructure specifics
  - Credentials, API keys, tokens, or passwords
  - Internal hostnames, URLs, or network topology (e.g., `*.redhat.com`, `*.corp.redhat.com`)
- Use synthetic or anonymized data when providing examples to AI tools
- When describing a problem, abstract away identifying details — focus on the technical pattern, not the specific system

## AI Marking Requirements

All AI-assisted work must be marked to maintain transparency and traceability.

### Source File Comment
Every code file produced or substantially modified with AI assistance must include a comment near the top:

- **JS/TS:** `// This project was developed with assistance from AI tools.`
- **Python:** `# This project was developed with assistance from AI tools.`
- **Other languages:** Use the appropriate comment syntax with the same text

This is a Red Hat policy requirement (see "Guidelines on Use of AI Generated Content"), not just a style preference.

### Commit Trailers
When committing code that was written or substantially shaped by an AI tool, include a trailer in the commit message:

- `Assisted-by: Claude Code` — for commits where AI assisted but a human drove the design and logic
- `Generated-by: Claude Code` — for commits where the code is substantially AI-generated

These trailers go in the footer section of the commit message, after the body.

### Pull Request Descriptions
When a PR contains substantial AI-generated code, note this in the PR description. Example: "AI assistance was used for [specific scope]."

## Copyright and Licensing

- Do not instruct AI to reproduce copyrighted code verbatim
- Verify that generated code does not closely match existing copyrighted implementations — if output looks suspiciously specific or familiar, investigate its origin
- All dependencies must use Red Hat-approved licenses (reference the [Fedora Allowed Licenses](https://docs.fedoraproject.org/en-US/legal/allowed-licenses/) list)
- When in doubt about license compatibility, check with Legal before proceeding
- Do not use AI to generate code that incorporates or derives from code with incompatible licenses

## Upstream Contribution Policy

- Before contributing AI-generated code to an upstream or open-source project, check whether that project has a policy on AI-generated contributions
- If the upstream project **prohibits** AI-generated contributions, do not submit AI-generated code to that project
- If the upstream project's policy is **unclear**, disclose AI assistance in the contribution (e.g., in the commit message or PR description)
- When contributing to Red Hat-led upstream projects, follow the project-specific guidance — if none exists, default to disclosure

## Security Review of AI-Generated Code

- Treat AI-generated code with the **same or higher** scrutiny as human-written code
- Pay special attention to these areas in AI-generated code:
  - Input validation and sanitization
  - Authentication and authorization logic
  - Cryptographic operations and secrets handling
  - SQL/query construction (watch for injection vulnerabilities)
  - File system and network operations
  - Deserialization of untrusted data
- AI tools may generate code that looks correct but contains subtle security flaws — do not trust it implicitly
- Run the project's security scanning tools (SAST, dependency audit) on all AI-generated code before merge
