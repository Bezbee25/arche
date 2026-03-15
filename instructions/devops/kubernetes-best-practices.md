# Kubernetes Best Practices

description: Production K8s standards: security contexts, RBAC, health probes, resource limits, network policies, PDB
tags: devops, kubernetes, k8s, containers, security, rbac, helm, deployment

Production Kubernetes deployment standards covering security, reliability, and observability.

## Workload Configuration

- Use `Deployment` for stateless apps, `StatefulSet` for stateful (databases, queues)
- Always set `replicas: 2+` for production workloads
- Use `RollingUpdate` strategy with `maxUnavailable: 0` for zero-downtime deploys:
  ```yaml
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  ```

## Labels & Selectors

- Apply standard labels to all resources:
  ```yaml
  labels:
    app.kubernetes.io/name: myapp
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: myplatform
    app.kubernetes.io/managed-by: helm
  ```

## Security Context

- Always set security context on pods and containers:
  ```yaml
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
  ```

## Resource Management

- Always set requests and limits — use `Guaranteed` QoS for critical services:
  ```yaml
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
  ```
- Use `LimitRange` and `ResourceQuota` per namespace

## Health Probes

- Define all three probe types:
  ```yaml
  livenessProbe:
    httpGet:
      path: /healthz
      port: 8080
    initialDelaySeconds: 10
    periodSeconds: 15
  readinessProbe:
    httpGet:
      path: /ready
      port: 8080
    initialDelaySeconds: 5
    periodSeconds: 10
  startupProbe:
    httpGet:
      path: /healthz
      port: 8080
    failureThreshold: 30
    periodSeconds: 10
  ```

## RBAC & Secrets

- Follow principle of least privilege for ServiceAccounts
- Use RBAC with specific resource/verb combinations — avoid `*` wildcards
- Use `ExternalSecrets` or `Sealed Secrets` for secret management — never commit plain Secrets
- Mount secrets as volumes rather than environment variables when possible

## Networking

- Define `NetworkPolicy` to restrict inter-pod communication
- Use `ClusterIP` for internal services, `LoadBalancer` for external exposure
- Implement `PodDisruptionBudget` for critical workloads:
  ```yaml
  spec:
    minAvailable: 1
    selector:
      matchLabels:
        app: myapp
  ```

## Scheduling

- Use `topologySpreadConstraints` or `podAntiAffinity` to spread pods across nodes/zones:
  ```yaml
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            topologyKey: kubernetes.io/hostname
  ```

## Observability

- Expose Prometheus metrics on `/metrics` endpoint
- Add sidecar containers for log shipping (Fluent Bit, Vector)
- Use structured JSON logging for easy parsing
- Set up alerts for: pod restarts, OOMKilled events, pending pods

## Validation Pipeline

```bash
kubectl apply --dry-run=server -f manifest.yaml
kubeconform -strict -summary manifest.yaml
conftest test manifest.yaml --policy rego/
```
