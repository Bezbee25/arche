# API Testing Best Practices

description: REST API testing: AAA pattern, schema validation, mocking, contract tests with Pact, load testing with k6
tags: testing, api, rest, fastapi, pytest, contract-testing, load-testing, k6, pact

Standards for testing REST APIs — unit, integration, contract, and load testing.

## Test Structure — Arrange/Act/Assert

```python
def test_create_user_returns_201_with_user_data():
    # Arrange
    payload = {"name": "Alice", "email": "alice@example.com"}

    # Act
    response = client.post("/api/users", json=payload)

    # Assert
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alice"
    assert body["email"] == "alice@example.com"
    assert "id" in body
    assert response.headers["Content-Type"] == "application/json"
```

## What to Test for Every Endpoint

- Happy path (valid input → success response)
- Invalid input (wrong types, missing fields, bad format)
- Authentication: 401 for missing token, 403 for insufficient permissions
- Not found: 404 for non-existent resources
- Validation errors: 422 with detailed error messages
- Idempotency for PUT/DELETE operations

## FastAPI Testing (Python)

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers(test_user_token):
    return {"Authorization": f"Bearer {test_user_token}"}

def test_list_items_requires_auth():
    response = client.get("/api/items")
    assert response.status_code == 401

def test_list_items_returns_user_items(auth_headers, db_with_items):
    response = client.get("/api/items", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == db_with_items.count
```

## Response Validation

- Always validate response schema (use Pydantic, JSON Schema, or ajv):
  ```python
  from pydantic import BaseModel

  class UserResponse(BaseModel):
      id: int
      name: str
      email: str
      created_at: str

  def test_create_user_response_schema():
      response = client.post("/api/users", json=valid_payload)
      assert response.status_code == 201
      UserResponse(**response.json())  # Validates schema — raises if invalid
  ```

## Test Data Management

- Use factories for test data creation (no hardcoded values):
  ```python
  @pytest.fixture
  def user_factory(db_session):
      def _factory(**kwargs):
          user = User(
              name=kwargs.get("name", f"User-{uuid4()}"),
              email=kwargs.get("email", f"{uuid4()}@test.com"),
          )
          db_session.add(user)
          db_session.commit()
          return user
      return _factory
  ```
- Use database transactions that rollback after each test
- Never depend on test execution order

## Mocking External APIs

```python
import httpx
import pytest
import respx

@respx.mock
def test_external_payment_api_called():
    respx.post("https://payment.api/charge").mock(
        return_value=httpx.Response(200, json={"status": "success"})
    )
    result = process_payment(amount=100, card_token="tok_123")
    assert result.status == "success"
```

## Load Testing (k6)

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // ramp up
    { duration: '1m',  target: 20 },   // steady state
    { duration: '10s', target: 0  },   // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed: ['rate<0.01'],    // < 1% errors
  },
};

export default function () {
  const res = http.get('http://api.example.com/users');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
```

## API Security Testing

- Test for IDOR: change user ID in path to access another user's data
- Test for mass assignment: send extra fields in request body
- Test rate limiting: send 100+ requests and verify 429 response
- Test CORS: send request from disallowed origin
- Verify no sensitive data in response (passwords, internal IDs, stack traces)
