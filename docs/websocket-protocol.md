# WebSocket Chat Protocol

This document describes the WebSocket chat protocol used by the Summit Cap Financial API. It covers all chat endpoints, authentication, message formats, and conversation history REST endpoints.

**Audience:** Frontend developers integrating the chat UI.

---

## Endpoints

| WebSocket Path | Required Role | Auth Required | Conversation Persisted |
|---|---|---|---|
| `ws://host/api/chat` | None (public) | No | No (ephemeral per connection) |
| `ws://host/api/borrower/chat` | `borrower` | Yes | Yes |
| `ws://host/api/loan-officer/chat` | `loan_officer` | Yes | Yes |
| `ws://host/api/underwriter/chat` | `underwriter` | Yes | Yes |
| `ws://host/api/ceo/chat` | `ceo` | Yes | Yes |

The public endpoint (`/api/chat`) is for unauthenticated prospects. It does not persist conversation history and assigns a new ephemeral session on every connection.

Authenticated endpoints persist conversation history across connections using a deterministic thread ID derived from the user's identity. When a user reconnects, the conversation resumes where it left off.

---

## Authentication

Authenticated endpoints require a Keycloak JWT passed as a query parameter on the WebSocket upgrade request:

```
ws://host/api/borrower/chat?token=<jwt>
```

The `token` parameter must be the raw JWT string (the same token obtained from the Keycloak OIDC flow). Do not prefix it with `Bearer`.

The public endpoint does not require a token. Providing one is accepted but has no effect on access control.

**Token validation:**

- Tokens are validated against Keycloak's JWKS endpoint (RS256)
- The token's `realm_access.roles` claim is checked for the required role
- Expired tokens are rejected with close code 4001

---

## WebSocket Close Codes

The server closes the WebSocket before the message loop begins if authentication or authorization fails.

| Code | Meaning |
|---|---|
| `4001` | Missing or invalid authentication token (includes expired tokens) |
| `4003` | Insufficient permissions — token is valid but the role does not match the required role for this endpoint |

After receiving a close code, the client should not attempt to send messages. For 4001, redirect to the login flow. For 4003, the user's session has an unexpected role.

---

## Message Format

### Client to Server

Send one message object per turn. The WebSocket connection stays open; send a new message after the server signals `done`.

```json
{"type": "message", "content": "What documents do I need for a mortgage application?"}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Must be `"message"` |
| `content` | string | The user's message text. Must not be empty. |

Sending a message with a missing or empty `content`, or with a `type` other than `"message"`, results in an `error` response. The connection remains open.

### Server to Client

The server streams the response as a sequence of events terminated by `done` or `error`.

**Token (streaming chunk):**

```json
{"type": "token", "content": "To apply for a mortgage..."}
```

Tokens arrive in order and should be concatenated to assemble the full response. Token boundaries are arbitrary — do not assume they align with words or sentences.

**Done (end of response):**

```json
{"type": "done"}
```

Signals that the current response is complete. The connection stays open. The client may send the next message.

**Error:**

```json
{"type": "error", "content": "Our chat assistant is temporarily unavailable. Please try again later."}
```

Errors caused by invalid client messages (malformed JSON, wrong `type`) keep the connection open. Errors caused by agent failures also keep the connection open, though a retry may be warranted. In both cases, `done` is not sent — `error` replaces it as the terminal event for that turn.

**Safety override:**

```json
{"type": "safety_override", "content": "I can only assist with mortgage-related questions."}
```

Sent when the output safety shield replaces the agent's response. The `content` is the safe replacement text and should be rendered in place of any tokens already received for that turn. After a `safety_override`, the server sends `done` to close the turn normally.

---

## Typical Message Sequence

```
Client                              Server
  |                                   |
  |-- {"type":"message","content":"-"}|
  |                                   |-- {"type":"token","content":"Sure"}
  |                                   |-- {"type":"token","content":", here"}
  |                                   |-- {"type":"token","content":" are..."}
  |                                   |-- {"type":"done"}
  |                                   |
  |-- {"type":"message","content":"-"}|
  |                                   |-- {"type":"token","content":"..."}
  |                                   |-- {"type":"done"}
```

When the output safety shield fires:

```
Client                              Server
  |                                   |
  |-- {"type":"message","content":"-"}|
  |                                   |-- {"type":"safety_override","content":"..."}
  |                                   |-- {"type":"done"}
```

---

## PII Masking

The CEO role has PII masking enabled at the data scope level. All WebSocket messages sent to CEO connections — including `token`, `error`, and `safety_override` payloads — are automatically masked before transmission. Names, SSNs, phone numbers, email addresses, and other PII fields are replaced with redacted placeholders.

No other role has PII masking enabled. The masking is server-side and transparent to the client.

---

## Conversation History (REST)

Authenticated personas can retrieve prior conversation messages via a REST endpoint. Use this to render existing history when the chat panel first opens.

| Endpoint | Allowed Roles |
|---|---|
| `GET /api/borrower/conversations/history` | `borrower`, `admin` |
| `GET /api/loan-officer/conversations/history` | `loan_officer`, `admin` |
| `GET /api/underwriter/conversations/history` | `underwriter`, `admin` |
| `GET /api/ceo/conversations/history` | `ceo`, `admin` |

Authentication uses the standard `Authorization: Bearer <jwt>` header (not the query parameter used for WebSocket).

**Response schema:**

```json
{
  "data": [
    {"role": "human", "content": "What is my application status?"},
    {"role": "ai", "content": "Your application is currently under review..."}
  ]
}
```

The history is scoped to the authenticated user. Each user's history is stored under a deterministic thread ID so reconnecting to the WebSocket resumes the same conversation.

The public chat endpoint (`/api/chat`) does not have a history endpoint — public sessions are ephemeral.

---

## Development Mode

When the API is started with `AUTH_DISABLED=true`, all WebSocket endpoints bypass JWT validation and return a dev user with the matching role. The `?token` parameter is ignored.

For HTTP endpoints in dev mode, the role can be overridden with the `X-Dev-Role` header (e.g., `X-Dev-Role: borrower`). This header has no effect on WebSocket connections — the role is determined by which endpoint is connected to.
