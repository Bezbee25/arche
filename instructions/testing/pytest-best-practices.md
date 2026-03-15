# Pytest Best Practices

description: Python testing standards with pytest: AAA pattern, fixtures, parametrize, mocking, coverage, async tests
tags: testing, python, pytest, unit-tests, mocking, tdd, coverage, fixtures

Standards for writing maintainable, reliable, and fast Python tests.

## Structure & Organization

```
tests/
├── unit/           # Isolated unit tests, no I/O
├── integration/    # Tests with real DB, external services
├── e2e/            # Full workflow tests
└── conftest.py     # Shared fixtures
```

- Mirror the `src/` directory structure in `tests/unit/`
- One test file per source module: `src/core/router.py` → `tests/unit/core/test_router.py`
- Name test functions: `test_<what>_<condition>_<expected_outcome>`

## Test Structure — Arrange/Act/Assert (AAA)

```python
def test_user_creation_with_valid_data_returns_user():
    # Arrange
    user_data = {"name": "Alice", "email": "alice@example.com"}

    # Act
    user = create_user(user_data)

    # Assert
    assert user.id is not None
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
```

## Fixtures

- Use fixtures for shared setup — prefer function scope (default):
  ```python
  @pytest.fixture
  def db_session():
      session = Session()
      yield session
      session.rollback()
      session.close()
  ```
- Use `session` scope for expensive resources (DB setup, external services)
- Keep fixtures in `conftest.py` at the appropriate directory level
- Use `pytest-factoryboy` or `factory-boy` for model factories

## Parametrization

- Use `@pytest.mark.parametrize` for testing multiple inputs:
  ```python
  @pytest.mark.parametrize("email,expected", [
      ("valid@example.com", True),
      ("invalid-email", False),
      ("", False),
      (None, False),
  ])
  def test_email_validation(email, expected):
      assert is_valid_email(email) == expected
  ```

## Mocking

- Use `pytest-mock` (`mocker` fixture) or `unittest.mock`:
  ```python
  def test_send_notification_calls_email_service(mocker):
      mock_send = mocker.patch("myapp.email.send_email")
      notify_user(user_id=1, message="Hello")
      mock_send.assert_called_once_with(
          to="alice@example.com",
          subject="Notification",
          body="Hello"
      )
  ```
- Mock at the point of use, not the point of definition
- Verify mock calls with `assert_called_once_with`, `assert_called_with`
- Use `mocker.spy` to wrap real functions while recording calls

## Coverage & Quality

```ini
# pytest.ini
[pytest]
addopts = --cov=src --cov-report=html --cov-fail-under=80
testpaths = tests
```

- Target 80%+ coverage for new code — 100% for critical paths
- Don't chase coverage at the expense of test quality
- Use `# pragma: no cover` sparingly for genuinely untestable code

## Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await fetch_data(url="https://api.example.com")
    assert result["status"] == "ok"
```

- Use `pytest-asyncio` with `asyncio_mode = "auto"` in config
- Use `httpx.AsyncClient` for testing async HTTP clients

## Performance

- Mark slow tests: `@pytest.mark.slow`
- Run fast tests in CI, slow tests nightly: `pytest -m "not slow"`
- Use `pytest-xdist` for parallel test execution: `pytest -n auto`
- Avoid `time.sleep()` in tests — use `freezegun` for time-based tests

## Anti-Patterns

- Never use production databases — use SQLite in-memory or test containers
- Avoid testing implementation details — test behavior, not internals
- Don't share mutable state between tests — each test must be independent
- Avoid overly complex setup — if setup is complex, the code under test is too
