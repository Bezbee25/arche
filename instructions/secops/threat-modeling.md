# Threat Modeling — STRIDE Framework

description: Systematic threat identification with STRIDE: Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Privilege Escalation
tags: security, secops, threat-modeling, stride, architecture, design

Systematic approach to identifying and mitigating security threats during design and code review.

## STRIDE Categories

### Spoofing (Authentication)
- Who can impersonate a user or service?
- Are all API endpoints properly authenticated?
- Are service-to-service calls mutually authenticated?
- Can session tokens be forged or reused?

**Mitigations**: Strong authentication (MFA, JWT with short expiry), mutual TLS for services, secure session management.

### Tampering (Integrity)
- Can an attacker modify data in transit or at rest?
- Are database records protected against unauthorized modification?
- Can request parameters be altered to bypass logic?

**Mitigations**: Input validation, HMAC signatures for sensitive data, database integrity constraints, audit logs with immutability.

### Repudiation (Non-repudiation)
- Can a user deny having performed an action?
- Are critical operations logged with sufficient context?
- Are logs tamper-proof?

**Mitigations**: Comprehensive audit logging, log integrity protection (WORM storage), digital signatures for critical transactions.

### Information Disclosure (Confidentiality)
- What sensitive data could be exposed?
- Are error messages leaking internal details?
- Is data encrypted at rest and in transit?
- Could logs expose PII or credentials?

**Mitigations**: TLS everywhere, encryption at rest, data classification, minimal error responses, log sanitization.

### Denial of Service (Availability)
- Can an attacker overwhelm the system with requests?
- Are there unbounded operations (large file uploads, expensive queries)?
- Are external dependencies single points of failure?

**Mitigations**: Rate limiting, input size limits, circuit breakers, horizontal scaling, DDoS protection.

### Elevation of Privilege (Authorization)
- Can a low-privilege user access admin functionality?
- Is authorization checked on every sensitive endpoint?
- Can parameter manipulation grant additional access (IDOR)?

**Mitigations**: Centralized authorization checks, RBAC, principle of least privilege, server-side ownership validation.

## Threat Modeling Process

1. **Decompose the application**: Draw data flow diagrams, identify trust boundaries, entry/exit points
2. **Identify threats**: Apply STRIDE to each data flow and component
3. **Rate threats**: Use DREAD (Damage, Reproducibility, Exploitability, Affected users, Discoverability) or CVSS
4. **Mitigate**: For each High/Critical threat, define and implement a control
5. **Validate**: Test that mitigations are effective

## Trust Boundary Checklist

- [ ] All data crossing trust boundaries is validated
- [ ] All privileged operations check authorization
- [ ] All external dependencies are authenticated
- [ ] All sensitive data in transit uses TLS
- [ ] All sensitive data at rest is encrypted
- [ ] Error handling does not leak internal state
- [ ] Audit logging covers all security-relevant events
