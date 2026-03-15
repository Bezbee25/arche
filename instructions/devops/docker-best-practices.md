# Docker Containerization Best Practices

description: Production Docker standards: multi-stage builds, non-root user, secrets, healthchecks, image scanning
tags: devops, docker, containers, security, ci-cd, dockerfile, trivy

Production-grade Dockerfile and container management standards.

## Dockerfile Structure

- Use multi-stage builds to minimize final image size:
  ```dockerfile
  FROM python:3.11-slim AS builder
  RUN pip install --no-cache-dir -r requirements.txt

  FROM python:3.11-slim
  COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
  COPY . .
  ```
- Pin base image tags — never use `latest`: `FROM python:3.11.9-slim`
- Prefer minimal base images: `distroless`, `alpine`, `slim` variants

## Security

- Run as non-root user:
  ```dockerfile
  RUN groupadd -r appuser && useradd -r -g appuser appuser
  USER appuser
  ```
- Never store secrets in image layers (ENV, RUN, COPY of `.env`)
- Use Docker BuildKit secrets for build-time credentials: `--mount=type=secret`
- Use read-only filesystems where possible: `docker run --read-only`
- Scan images in CI: `trivy image myapp:latest`

## Performance & Size

- Order layers from least to most frequently changed (dependencies before code)
- Use `.dockerignore` to exclude unnecessary files:
  ```
  .git
  __pycache__
  *.pyc
  .env
  tests/
  docs/
  ```
- Combine RUN commands to reduce layers:
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      && rm -rf /var/lib/apt/lists/*
  ```

## Health Checks

- Always add HEALTHCHECK for service containers:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
  ```

## Entrypoint & CMD

- Use exec form (JSON array) for CMD and ENTRYPOINT — never shell form:
  ```dockerfile
  ENTRYPOINT ["python", "-m", "myapp"]
  CMD ["--port", "8080"]
  ```
- Use `tini` as PID 1 to handle signals properly:
  ```dockerfile
  RUN apt-get install -y tini
  ENTRYPOINT ["/usr/bin/tini", "--", "python", "-m", "myapp"]
  ```

## Resource Limits

- Always set resource limits in docker-compose:
  ```yaml
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
  ```

## Review Checklist

- [ ] Base image pinned to specific version
- [ ] Multi-stage build used (if applicable)
- [ ] Non-root user configured
- [ ] No secrets in Dockerfile or image layers
- [ ] `.dockerignore` present and comprehensive
- [ ] HEALTHCHECK defined
- [ ] Exec form used for CMD/ENTRYPOINT
- [ ] Image scanned with Trivy or Grype
- [ ] Resource limits defined
- [ ] Layers optimized (dependencies before code)
