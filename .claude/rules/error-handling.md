---
paths:
  - "packages/api/**/*"
  - "packages/db/**/*"
---

# Error Handling

## Error Response Format (RFC 7807)

All API error responses must follow the RFC 7807 Problem Details standard:

```json
{
  "type": "https://api.example.com/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "User with ID 'abc123' was not found.",
  "instance": "/users/abc123"
}
```

Required fields: `type`, `title`, `status`. Include `detail` for human-readable context and `instance` for the specific resource. Add extension fields as needed (e.g., `errors[]` for validation).

## HTTP Status Code Usage

| Code | Use When |
|------|----------|
| 200 | Success with body |
| 201 | Resource created |
| 204 | Success with no body (DELETE, etc.) |
| 400 | Client sent malformed or invalid request |
| 401 | Missing or invalid authentication |
| 403 | Authenticated but not authorized |
| 404 | Resource does not exist |
| 409 | Conflict with current state (duplicate, version mismatch) |
| 422 | Request well-formed but semantically invalid (validation errors) |
| 429 | Rate limit exceeded |
| 500 | Unexpected server error |

Do not use 200 with an error body. Use the appropriate 4xx/5xx status code.

## Error Class Hierarchy

Define a base `AppError` class with domain-specific subclasses: `ValidationError` (422), `NotFoundError` (404), `ConflictError` (409), `AuthenticationError` (401), `AuthorizationError` (403), `ExternalServiceError` (502/503). Adapt to your language's error patterns.

- Throw domain-specific errors in service/business logic layers
- Map domain errors to HTTP responses at the handler/controller boundary
- Never expose internal error details (stack traces, SQL errors) to clients
- Log the full error internally, return the sanitized RFC 7807 response externally

## Guidelines

- Handle errors at the appropriate boundary — don't catch and re-throw without adding context
- Use early returns or guard clauses for validation — don't nest happy path inside error checks
- Distinguish between client errors (4xx — the caller did something wrong) and server errors (5xx — we did something wrong)
- Include enough context in error messages for the caller to fix the problem
- Never swallow errors silently — log them if you can't handle them
