---
paths:
  - "packages/api/**/*"
  - "packages/db/**/*"
---

# Observability

## Structured Logging

Use structured (JSON) log output in all environments except local development. Every log entry must include:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 format |
| `level` | Log level (see below) |
| `message` | Human-readable description |
| `correlationId` | Request/trace ID for distributed tracing |
| `service` | Service name |

Add contextual fields as needed: `userId`, `operation`, `durationMs`, `statusCode`, `error`.

## Log Levels

| Level | Use When |
|-------|----------|
| `error` | Something failed and requires attention — broken functionality, unhandled exceptions |
| `warn` | Something unexpected happened but the system recovered — retry succeeded, fallback used, deprecated usage |
| `info` | Significant business events — request handled, job completed, user action |
| `debug` | Diagnostic detail for troubleshooting — function entry/exit, intermediate state, query plans |

Default to `info` in production. Use `debug` in development. Never use `debug` for anything you'd want in production logs.

## What to Log

- Request start and completion (with duration, status code, correlation ID)
- Authentication and authorization events (success and failure)
- Business-significant operations (created, updated, deleted resources)
- External service calls (with duration and outcome)
- Error details (full stack trace server-side, never in responses)
- Job/queue processing events (started, completed, failed, retried)

## What NEVER to Log

- Passwords, tokens, API keys, secrets
- PII (emails, names, phone numbers, addresses, SSNs) unless required and compliant
- Credit card numbers or financial account details
- Full request/response bodies in production (may contain sensitive data)
- Session tokens or auth headers

## Correlation IDs

- Generate a unique ID at the system entry point (API gateway, first handler)
- Propagate through all downstream calls (services, queues, async jobs)
- Include in all log entries and error responses
- Use standard headers: `X-Request-ID` or `traceparent` (W3C Trace Context)

## Health Checks

Every deployable service must expose:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` or `GET /healthz` | Liveness — is the process running? Returns 200 if alive. |
| `GET /ready` or `GET /readyz` | Readiness — can the service handle traffic? Checks dependencies (DB, cache, etc.) |

Health endpoints must not require authentication. Keep them fast — no heavy computation.

## Metrics Naming

Follow the `<namespace>_<subsystem>_<name>_<unit>` convention:

```
app_http_requests_total
app_http_request_duration_seconds
app_db_connections_active
app_queue_messages_processed_total
```

Use `_total` suffix for counters, `_seconds`/`_bytes` for measured units.
