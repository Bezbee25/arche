# Secure Development Principles

description: Universal secure coding rules: input validation, secrets, TLS, injection prevention, logging, auth
tags: security, secops, input-validation, secrets, authentication, best-practices

Universal secure coding rules enforced across all languages and AI-generated code.

## Input Validation

- Never use raw user input directly in file access, command execution, or database queries
- Validate and sanitize all inputs at system boundaries (user input, external APIs, file uploads)
- Use allowlists over denylists for input validation
- Reject and log invalid input rather than silently discarding it

## Secrets & Credentials

- Secrets, API keys, and tokens must never appear in source code, frontend code, or public repos
- Use environment variables or secret management services (Vault, AWS SSM, Azure Key Vault)
- Rotate secrets regularly and immediately after suspected exposure
- Use `.gitignore` and pre-commit hooks to prevent accidental secret commits

## Transport Security

- Only use HTTPS/TLS for all external communication
- Use TLS 1.2+ minimum, prefer TLS 1.3
- Validate server certificates — never disable SSL verification
- Use HSTS headers on all web endpoints

## Code Execution

- Never execute dynamically constructed code/expressions from user input (`eval`, `exec`)
- Use parameterized queries exclusively — never string-concatenate SQL
- Avoid `subprocess` with `shell=True`; pass command arrays instead
- Sandbox or isolate untrusted code execution environments

## Logging & Data Privacy

- Logs must never contain credentials, tokens, session IDs, or PII
- Implement structured logging with appropriate log levels
- Mask sensitive fields before logging (e.g., credit cards, passwords)
- Ensure log storage access is restricted and audited

## Authentication & Authorization

- Critical auth/permission logic must never rely on client-side code alone
- Implement server-side session validation for every privileged operation
- Use battle-tested libraries for auth (do not roll your own crypto)
- Enforce principle of least privilege for all service accounts and roles

## Error Handling

- Never expose stack traces, internal paths, or system info in error responses
- Return generic error messages to clients; log details server-side
- Handle all exceptions explicitly — avoid bare `except` or `catch` blocks
- Use consistent error response formats across the API

## Dependencies

- Regularly audit dependencies with tools like `pip-audit`, `npm audit`, `trivy`
- Pin dependency versions and use lock files
- Remove unused dependencies
- Monitor CVE databases for critical vulnerabilities in used packages
