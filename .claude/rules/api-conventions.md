---
paths:
  - "packages/api/**/*"
---

# API Conventions

## Resource Design

- URLs represent resources (nouns), not actions (verbs): `/users`, not `/getUsers`
- Use kebab-case for URL paths: `/user-profiles`, not `/userProfiles`
- Use camelCase for JSON field names: `firstName`, not `first_name`
- Use plural nouns for collections: `/users`, `/orders`
- Nest sub-resources under parents: `/users/:id/orders`
- Keep URLs shallow — max 2 levels of nesting before introducing a top-level resource

## HTTP Methods

```
GET    /resources          List (paginated)
GET    /resources/:id      Get single resource
POST   /resources          Create resource
PUT    /resources/:id      Full replace (all fields required)
PATCH  /resources/:id      Partial update (only changed fields)
DELETE /resources/:id      Delete resource
```

- GET and DELETE have no request body
- POST returns 201 with `Location` header pointing to the new resource
- PUT/PATCH return 200 with the updated resource
- DELETE returns 204 with no body

## Pagination

Use cursor-based pagination for dynamic or large datasets. Use offset-based for small, static collections.

```json
{
  "data": [...],
  "pagination": {
    "nextCursor": "eyJpZCI6MTAwfQ==",
    "hasMore": true
  }
}
```

Query parameters: `?cursor=<value>&limit=<number>` (default limit: 20, max: 100).

## Filtering and Sorting

- Filter via query parameters: `?status=active&role=admin`
- Sort via `sort` parameter: `?sort=createdAt` (ascending), `?sort=-createdAt` (descending)
- Support multiple sort fields: `?sort=-priority,createdAt`

## Response Envelope

Consistent top-level structure for all responses:

```json
// Single resource
{ "data": { ... } }

// Collection
{ "data": [...], "pagination": { ... } }

// Error (RFC 7807 — see error-handling rule)
{ "type": "...", "title": "...", "status": 422, "detail": "..." }
```

## Versioning

- Use URL path versioning for major versions: `/v1/users`, `/v2/users`
- Use additive, non-breaking changes within a version (new fields, new endpoints)
- Breaking changes require a new major version
- Support at most 2 major versions simultaneously
- Document deprecation timeline when introducing a new version

## Authentication

- Use `Authorization: Bearer <token>` header for API authentication
- Return 401 for missing/invalid credentials, 403 for insufficient permissions
- Document authentication requirements per endpoint in OpenAPI specs
- Never pass tokens in URL query parameters

## Rate Limiting

- Return 429 when rate limit is exceeded
- Include standard headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Document rate limits per endpoint or tier
