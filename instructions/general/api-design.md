# REST API Design Principles

description: REST API design standards: URL conventions, HTTP methods, response codes, versioning, auth, pagination
tags: general, api, rest, design, http, openapi, authentication, pagination

Standards for designing clean, consistent, and developer-friendly REST APIs.

## URL Design

- Use nouns for resources, not verbs: `/users` not `/getUsers`
- Use plural nouns for collections: `/users`, `/orders`, `/products`
- Nest resources for clear ownership: `/users/123/orders`
- Keep nesting max 2 levels deep: `/users/{id}/orders/{orderId}`
- Use kebab-case for multi-word paths: `/user-profiles` not `/userProfiles`
- Use query parameters for filtering, sorting, pagination: `?status=active&sort=created_at&page=2`

## HTTP Methods

| Method | Usage | Idempotent | Safe |
|--------|-------|------------|------|
| GET | Retrieve resource(s) | Yes | Yes |
| POST | Create resource | No | No |
| PUT | Replace resource (full) | Yes | No |
| PATCH | Update resource (partial) | No | No |
| DELETE | Remove resource | Yes | No |

## Response Codes

- `200 OK` — Success (GET, PUT, PATCH)
- `201 Created` — Resource created (POST); include `Location` header
- `204 No Content` — Success with no body (DELETE)
- `400 Bad Request` — Invalid input (validation errors)
- `401 Unauthorized` — Missing or invalid authentication
- `403 Forbidden` — Authenticated but not authorized
- `404 Not Found` — Resource doesn't exist
- `409 Conflict` — Duplicate resource, optimistic lock conflict
- `422 Unprocessable Entity` — Semantically invalid (business rule violation)
- `429 Too Many Requests` — Rate limit exceeded
- `500 Internal Server Error` — Unexpected server error

## Response Format

```json
// Success (single resource)
{
  "id": 123,
  "name": "Alice",
  "email": "alice@example.com",
  "created_at": "2024-01-15T10:30:00Z"
}

// Success (collection)
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "next": "/api/users?page=2"
  }
}

// Error
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {"field": "email", "message": "Must be a valid email address"}
    ]
  }
}
```

## Versioning

- Version via URL prefix: `/api/v1/users` — most discoverable
- Or via Accept header: `Accept: application/vnd.myapi.v1+json`
- Maintain at least one previous version during transition
- Document deprecation timeline in headers: `Deprecation: Sun, 1 Jan 2025 00:00:00 GMT`

## Authentication & Security

- Use JWT Bearer tokens: `Authorization: Bearer <token>`
- Short-lived access tokens (15min) + long-lived refresh tokens (7 days)
- Rate limit all endpoints — use 429 with `Retry-After` header
- Return the same error for "user not found" and "wrong password" (prevent enumeration)
- Use HTTPS only — redirect HTTP to HTTPS

## Pagination

- Default to cursor-based pagination for large datasets (stable under insertions)
- Use offset pagination only for small, stable datasets
- Always include total count and next/prev links

```json
// Cursor-based
{
  "data": [...],
  "cursor": {
    "next": "eyJpZCI6MTIzfQ==",
    "has_more": true
  }
}
```

## Documentation

- Use OpenAPI 3.0 (Swagger) for all APIs
- Include request/response examples for all endpoints
- Document all error codes and their meanings
- Keep documentation in sync with implementation (generate from code annotations)

## HATEOAS (Optional but Valuable)

```json
{
  "id": 123,
  "name": "Alice",
  "_links": {
    "self": {"href": "/api/users/123"},
    "orders": {"href": "/api/users/123/orders"},
    "update": {"href": "/api/users/123", "method": "PATCH"}
  }
}
```
