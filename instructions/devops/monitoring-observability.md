# Monitoring & Observability Best Practices

description: Observability standards: Prometheus metrics, structured logs, OpenTelemetry traces, SLOs, DORA metrics
tags: devops, monitoring, observability, prometheus, grafana, opentelemetry, slo, logging

Standards for building observable systems using the three pillars: metrics, logs, and traces.

## Three Pillars of Observability

### Metrics (Prometheus)
- Expose `/metrics` endpoint on all services (Prometheus format)
- Instrument all four Golden Signals:
  1. **Latency**: `http_request_duration_seconds` histogram
  2. **Traffic**: `http_requests_total` counter
  3. **Errors**: `http_errors_total` counter with error code labels
  4. **Saturation**: CPU, memory, connection pool utilization
- Use appropriate metric types:
  - `Counter`: monotonically increasing values (requests, errors)
  - `Gauge`: values that can go up and down (queue depth, active connections)
  - `Histogram`: distribution of values (request duration, response size)
- Add meaningful labels: `service`, `method`, `status_code`, `endpoint`
- Avoid high-cardinality labels (no user IDs, request IDs in labels)

### Logs (Structured Logging)
- Use structured JSON logging in all services:
  ```json
  {"timestamp": "2024-01-15T10:30:00Z", "level": "ERROR", "service": "api", "trace_id": "abc123", "message": "DB connection failed", "error": "timeout after 5s"}
  ```
- Include correlation IDs in all log entries for request tracing
- Log at appropriate levels:
  - `DEBUG`: Development only, never in production
  - `INFO`: Normal operations, state transitions
  - `WARN`: Unexpected but recoverable situations
  - `ERROR`: Failures requiring attention
  - `FATAL`: System-level failures
- Never log: passwords, tokens, PII, credit cards

### Traces (Distributed Tracing)
- Use OpenTelemetry (OTel) SDK for instrumentation
- Propagate trace context across service boundaries (W3C Trace Context)
- Create spans for: HTTP calls, DB queries, cache operations, queue messages
- Add meaningful span attributes: `user.id`, `db.statement`, `http.url`

## DORA Metrics

Track these four key engineering metrics:
- **Deployment Frequency**: How often you deploy to production
- **Lead Time for Changes**: Time from commit to production
- **Change Failure Rate**: % of deployments causing incidents
- **Mean Time to Recovery (MTTR)**: How quickly you recover from incidents

Elite performers: Deploy multiple times/day, MTTR < 1 hour, change failure rate < 5%.

## Alerting Rules

- Alert on symptoms (user-facing impact), not causes (CPU > 80%)
- Use multi-window, multi-burn-rate SLO alerting
- Define SLOs before setting up alerts:
  ```yaml
  # 99.9% availability = 43.8 min/month error budget
  slo:
    target: 0.999
    window: 30d
  ```
- Set alert severity: `critical` (page oncall), `warning` (ticket), `info` (dashboard)
- Include runbook links in all alert annotations

## Dashboards (Grafana)

- Create service-level dashboards with: request rate, error rate, latency (p50/p95/p99)
- Use `USE Method` for infrastructure: Utilization, Saturation, Errors
- Include SLO burn rate panels on all service dashboards
- Add annotations for deployments and incidents

## Health Endpoints

Every service must expose:
```
GET /health       → 200 if alive (liveness)
GET /health/ready → 200 if ready to serve traffic (readiness)
GET /metrics      → Prometheus metrics
```
