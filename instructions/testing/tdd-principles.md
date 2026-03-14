# TDD & Testing Principles

description: TDD methodology: Red-Green-Refactor, test pyramid, BDD, contract testing, test doubles taxonomy
tags: testing, tdd, bdd, unit-tests, integration-tests, e2e, test-pyramid, methodology

Test-Driven Development methodology and general testing philosophy.

## TDD Cycle: Red → Green → Refactor

1. **Red**: Write a failing test that describes desired behavior
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Clean up code while keeping tests green

```python
# 1. Red — write failing test
def test_fizzbuzz_returns_fizz_for_3():
    assert fizzbuzz(3) == "Fizz"  # NameError: fizzbuzz not defined

# 2. Green — write minimum implementation
def fizzbuzz(n: int) -> str:
    if n % 3 == 0:
        return "Fizz"
    return str(n)

# 3. Refactor — improve without changing behavior
```

## Test Pyramid

```
        /\
       /E2E\        ← Few, slow, high confidence
      /------\
     /  Integ \     ← Some, medium speed, real dependencies
    /----------\
   /  Unit Tests\   ← Many, fast, isolated
  /______________\
```

- Unit: 70% of tests — fast, isolated, pure logic
- Integration: 20% — real DB, real HTTP clients, no mocks
- E2E: 10% — critical user journeys only

## What to Test

**Test behavior, not implementation:**
```python
# BAD — tests implementation detail (will break on refactor)
def test_user_service_calls_repository():
    mock_repo = Mock()
    service = UserService(mock_repo)
    service.get_user(1)
    mock_repo.find_by_id.assert_called_once_with(1)

# GOOD — tests observable behavior
def test_get_user_returns_user_with_correct_id():
    user = service.get_user(1)
    assert user.id == 1
```

**Test edge cases:**
- Empty inputs, None/null values
- Boundary values (0, -1, max int, empty string)
- Invalid types or formats
- Concurrent access scenarios
- Error and exception paths

## BDD — Behavior-Driven Development

Use Gherkin-style descriptions for acceptance tests:
```gherkin
Feature: User login
  Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter "user@example.com" and "correct-password"
    And I click "Log in"
    Then I should be redirected to the dashboard
    And I should see "Welcome back, Alice"
```

Tools: `pytest-bdd` (Python), `Cucumber` (Java/JS), `behave` (Python).

## Test Quality Metrics

- **Coverage**: 80%+ line coverage, 100% for critical paths
- **Mutation Score**: Use `mutmut` or `pitest` to verify tests catch bugs
- **Test Performance**: Unit tests < 1ms, full suite < 5 minutes
- **Flakiness Rate**: 0% flaky tests — fix or delete flaky tests immediately

## Contract Testing

For microservices, use consumer-driven contract tests (Pact):
```python
# Consumer test (defines the contract)
@consumer_pact
def test_get_user_contract(pact):
    pact.given("user 1 exists") \
        .upon_receiving("a request for user 1") \
        .with_request(method="GET", path="/users/1") \
        .will_respond_with(200, body={"id": 1, "name": "Alice"})
```

## Test Doubles Taxonomy

- **Stub**: Returns predefined answers (no behavior verification)
- **Mock**: Verifies interactions were called correctly
- **Fake**: Working implementation suitable for tests (in-memory DB)
- **Spy**: Wraps real implementation, records calls
- **Dummy**: Placeholder passed but never used

Use the simplest double that satisfies your needs.

## Continuous Testing

- Run unit tests on every file save (watch mode)
- Run full test suite on every commit (pre-push hook or CI)
- Block merges if test suite fails
- Display coverage trends over time — fail if coverage drops
