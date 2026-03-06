# Production Checklist

Use this checklist before promoting a service created from this template.

## 1. Configuration and Secrets

- [ ] `APP_ENVIRONMENT=prod`
- [ ] `APP_DEBUG=false`
- [ ] `APP_AUTH_ENABLED=true`
- [ ] `APP_AUTH_JWT_SECRET` set to a strong secret (>= 32 chars)
- [ ] `APP_AUTH_ADMIN_PASSWORD` changed from default placeholder
- [ ] `APP_ALLOWED_HOSTS` set to explicit domains (no `*`)
- [ ] `APP_API_DOCS_ENABLED=false`
- [ ] `APP_DATABASE_AUTO_CREATE_SCHEMA=false`

## 2. Runtime and Networking

- [ ] `APP_WEB_CONCURRENCY` tuned for CPU/memory budget
- [ ] `APP_LIMIT_CONCURRENCY` tuned for upstream/downstream capacity
- [ ] `APP_PROXY_HEADERS=true` only behind trusted LB/proxy
- [ ] `APP_FORWARDED_ALLOW_IPS` restricted to proxy ranges
- [ ] TLS terminated at ingress/LB

## 3. Data and Migrations

- [ ] PostgreSQL URL configured (`postgresql+asyncpg://...`)
- [ ] Alembic migrations applied (`make migrate`)
- [ ] Backup and restore process verified

## 4. Security and Resilience

- [ ] Security headers enabled
- [ ] Rate limit backend selected (`redis` for multi-instance HA)
- [ ] Request timeout and body-size limits tuned
- [ ] Health probes wired to `/health` and `/ready`

## 5. Observability

- [ ] Structured logs ingested centrally
- [ ] `X-Request-ID` propagation verified end-to-end
- [ ] Metrics scraped from `/metrics` (if enabled)
- [ ] Alerts for error-rate and latency SLOs configured

## 6. Pre-Release Validation

Run locally or in CI:

```bash
make verify
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app \
  PYTHONPATH=src pytest tests/db
```
