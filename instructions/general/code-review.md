# Code Review Best Practices

description: Three-tier severity code review framework covering security, correctness, design, testing, and performance
tags: general, code-review, best-practices, security, design, testing, quality

Three-tier severity framework for thorough and actionable code reviews.

## Severity Tiers

### Critical — Blocks Merge
- Security vulnerabilities (injection, exposed secrets, broken auth)
- Data corruption or data loss bugs
- Logic errors that cause incorrect behavior
- Missing error handling for critical paths
- Performance issues that break scalability (N+1 queries, missing indexes)

### Important — Requires Discussion
- Violation of team coding standards or architecture patterns
- Missing test coverage for new logic
- Breaking changes without documentation
- Overly complex code that should be simplified
- Resource leaks (unclosed connections, file handles)

### Suggestions — Non-Blocking
- Readability improvements
- Documentation additions
- Alternative implementation approaches
- Style inconsistencies (minor)

## Review Checklist

### Security
- [ ] No hardcoded secrets or credentials
- [ ] User input is validated and sanitized
- [ ] SQL queries use parameterized statements
- [ ] Authentication/authorization checked on new endpoints
- [ ] Sensitive data not logged or exposed in errors

### Correctness
- [ ] All edge cases handled (null/empty, boundaries)
- [ ] Error handling is explicit and appropriate
- [ ] Concurrent access considered (race conditions, deadlocks)
- [ ] Business logic matches requirements

### Design
- [ ] Single Responsibility Principle followed
- [ ] No unnecessary duplication (DRY)
- [ ] Dependencies point in the right direction (dependencies flow inward)
- [ ] New abstractions justified — not over-engineered

### Testing
- [ ] New code has corresponding tests
- [ ] Tests cover happy path, error path, and edge cases
- [ ] Tests are independent and deterministic
- [ ] Mocks are used appropriately (not mocking what you're testing)

### Performance
- [ ] Database queries are optimized (no N+1, uses indexes)
- [ ] No unnecessary computation in hot paths
- [ ] Caching used where appropriate
- [ ] Pagination on list endpoints

## Comment Format

```
[CRITICAL] This query is vulnerable to SQL injection — use parameterized statements.
See: https://owasp.org/www-community/attacks/SQL_Injection

[IMPORTANT] This function is doing two things — consider splitting into `parseInput()`
and `validateInput()` to follow SRP.

[SUGGESTION] Consider using `pathlib.Path` here instead of `os.path.join()` for
cleaner path manipulation.
```

## Reviewing AI-Generated Code

AI-generated code requires extra scrutiny:
- Verify logic is correct — AI often generates plausible-looking but wrong code
- Check for security anti-patterns (AI frequently generates insecure patterns)
- Ensure code fits the existing architecture — AI ignores project conventions
- Verify all dependencies are actually imported and used
- Test edge cases that AI tends to miss (None, empty collections, Unicode)

## Giving Feedback Effectively

- Be specific: point to the exact line and explain why it's a problem
- Propose solutions: "Instead of X, consider Y because Z"
- Separate personal preference from objective issues
- Acknowledge good work: "Nice use of context managers here"
- Ask questions when unclear: "What happens if `user` is None here?"

## Receiving Feedback

- Treat all feedback as about the code, not about you
- Reply to every comment: acknowledge, address, or explain why you disagree
- If you disagree with a Critical/Important comment, discuss — don't ignore
- Thank reviewers for catching real issues
