# GitHub Actions — CI/CD Best Practices

description: GitHub Actions standards: pinned actions, OIDC auth, secrets management, caching, deployment patterns
tags: devops, github-actions, ci-cd, security, deployment, automation, oidc

Standards for secure, efficient, and maintainable GitHub Actions workflows.

## Workflow Structure

- Split workflows by concern: `ci.yml` (lint + test), `build.yml` (image), `deploy.yml` (deploy)
- Use reusable workflows (`.github/workflows/reusable-*.yml`) for shared logic
- Name jobs and steps descriptively for clear audit trails

## Security

- Pin actions to full commit SHA — never use `@main` or `@latest`:
  ```yaml
  uses: actions/checkout@v4  # OK
  uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # Best
  ```
- Apply least-privilege `permissions` block on every workflow and job:
  ```yaml
  permissions:
    contents: read
    id-token: write  # For OIDC only
  ```
- Never echo secrets or use them in `run` commands that produce logs
- Use OIDC for cloud authentication — eliminates long-lived static credentials:
  ```yaml
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789:role/github-actions
      aws-region: us-east-1
  ```

## Secrets Management

- Use GitHub Secrets (`${{ secrets.MY_SECRET }}`) for all credentials
- Use GitHub Environments for environment-specific secrets with approval gates
- Rotate secrets regularly and audit access logs

## Performance

- Cache dependencies aggressively:
  ```yaml
  - uses: actions/cache@v4
    with:
      path: ~/.cache/pip
      key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
      restore-keys: ${{ runner.os }}-pip-
  ```
- Use matrix builds for parallel testing across Python/Node versions
- Use `actions/upload-artifact` sparingly — only for artifacts needed downstream
- Use shallow clones: `fetch-depth: 1` (default for `actions/checkout@v4`)

## Quality Gates

- Run linting and formatting checks before tests
- Fail fast on security scanning (SAST, dependency vulnerabilities)
- Set minimum test coverage thresholds
- Block merges without passing CI on protected branches

## Deployment Patterns

```yaml
# Staging validation gate before production
jobs:
  deploy-staging:
    environment: staging
    steps:
      - run: ./deploy.sh staging

  smoke-test:
    needs: deploy-staging
    steps:
      - run: ./smoke-test.sh ${{ vars.STAGING_URL }}

  deploy-prod:
    needs: smoke-test
    environment: production  # Requires manual approval
    steps:
      - run: ./deploy.sh production
```

- Use `environment` with required reviewers for production deploys
- Implement automatic rollback on health check failure
- Notify on deployment success/failure (Slack, Teams)

## Job Templates

```yaml
# Reusable test job template
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v4
```

## Anti-Patterns to Avoid

- Storing secrets in environment variables visible in logs
- Using `runs-on: self-hosted` without proper hardening
- Long-running jobs without timeout: `timeout-minutes: 30`
- Not pinning action versions
- Using `pull_request_target` without careful permission scoping
