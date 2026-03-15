# OWASP Top 10 — Secure Coding Checklist

description: Mitigation rules for OWASP Top 10: broken access control, injection, XSS, SSRF, misconfiguration
tags: security, secops, owasp, injection, xss, ssrf, authentication, access-control

Mitigation rules for the OWASP Top 10 web application security risks.

## A01 — Broken Access Control

- Enforce access control server-side on every request; never trust client-side checks
- Deny by default — explicitly grant permissions, never assume
- Implement field-level access control for sensitive data attributes
- Log access control failures and alert on repeated violations
- Use RBAC or ABAC frameworks; never manage permissions ad hoc

## A02 — Cryptographic Failures

- Never store passwords in plaintext; use bcrypt/Argon2/scrypt with cost factor ≥ 12
- Use AES-256-GCM for symmetric encryption; RSA-2048+ or ECDSA P-256 for asymmetric
- Never use MD5, SHA-1, or DES for security-sensitive operations
- Generate cryptographic secrets using `secrets` module (Python) or `crypto.randomBytes` (Node)
- Use `hmac.compare_digest()` for timing-safe comparisons

## A03 — Injection

- Use parameterized queries / prepared statements for ALL database interactions
- Never concatenate user input into SQL, shell commands, LDAP, or XPath queries
- Use ORM query builders with proper escaping
- Validate input type, length, format, and range before processing

## A04 — Insecure Design

- Apply threat modeling (STRIDE) during design phase
- Implement rate limiting and anti-automation measures
- Design for failure — use circuit breakers and graceful degradation
- Document trust boundaries and data flows in architecture diagrams

## A05 — Security Misconfiguration

- Disable debug mode, stack traces, and verbose errors in production
- Remove default accounts, sample applications, and unused features
- Apply minimal permissions to all service accounts
- Use `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options` headers

## A06 — Vulnerable Components

- Maintain a software bill of materials (SBOM)
- Run `pip-audit`, `npm audit`, `trivy`, or `snyk` in CI pipelines
- Subscribe to security advisories for core dependencies
- Have a documented patching SLA (e.g., critical CVEs within 48h)

## A07 — Authentication Failures

- Enforce multi-factor authentication for sensitive operations and admin accounts
- Implement account lockout after 5 failed attempts with progressive delays
- Rate limit authentication endpoints (5 requests per 15 minutes per IP)
- Use secure, random session IDs; invalidate sessions on logout and password change
- Set `HttpOnly`, `Secure`, `SameSite=Strict` on session cookies

## A08 — Software and Data Integrity Failures

- Verify checksums/signatures for downloaded artifacts and packages
- Use signed container images with Cosign or Notary
- Implement CI/CD pipeline integrity checks (code signing, artifact attestation)
- Never deserialize untrusted data with `pickle`, `marshal`, or `shelve` in Python

## A09 — Logging & Monitoring Failures

- Log all authentication events (success, failure, account lockout)
- Log all access control failures with user context
- Set up real-time alerts for anomalous patterns (brute force, privilege escalation)
- Retain security logs for minimum 90 days with tamper protection

## A10 — SSRF

- Validate and allowlist target URLs before making server-side HTTP requests
- Block requests to private IP ranges: `127.x`, `10.x`, `172.16-31.x`, `192.168.x`, `169.254.x`
- Validate DNS resolution results, not just input URLs
- Use dedicated egress proxies to control outbound network access
- Never forward internal authentication tokens to external services
