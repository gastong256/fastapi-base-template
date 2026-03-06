# __PROJECT_NAME__

> __DESCRIPTION__

[![CI](https://github.com/gastong256/fastapi-base-template/actions/workflows/ci.yml/badge.svg)](https://github.com/gastong256/fastapi-base-template/actions/workflows/ci.yml)

Production-ready FastAPI template. Batteries included: structured logging, request tracing, multitenancy, PostgreSQL-ready persistence with Alembic migrations, JWT auth scaffolding, rate limiting, security headers, optional OpenTelemetry, Docker, and a full test suite.

---

## Table of Contents

- [How to use this template](#how-to-use-this-template)
- [Quickstart](#quickstart)
- [API Documentation](#api-documentation)
- [Development Workflow](#development-workflow)
- [Production Runtime](#production-runtime)
- [Database](#database)
- [Security](#security)
- [Observability](#observability)
- [Multi-Tenancy](#multi-tenancy)
- [Repository Structure](#repository-structure)
- [Releasing](#releasing)

---

## How to use this template

1. Click **"Use this template"** on GitHub to create a new repository from this template.

2. Clone your new repository:
   ```bash
   git clone https://github.com/your-org/your-repo.git
   cd your-repo
   ```

3. Initialize the template — replaces all placeholders and renames the source package:
   ```bash
   PROJECT_NAME="Acme API" \
   PROJECT_SLUG="acme_api" \
   SERVICE_NAME="acme-api" \
   OWNER="acme-org" \
   DESCRIPTION="Internal API for Acme services" \
   make init
   ```

4. Install dependencies and start developing:
   ```bash
   make lock
   make install
   make migrate
   make run
   curl http://localhost:8000/api/v1/ping
   ```

### Placeholder reference

| Placeholder | Example | Used in |
|---|---|---|
| `__PROJECT_NAME__` | `Acme API` | `pyproject.toml`, `README.md`, OpenAPI title |
| `__PROJECT_SLUG__` | `acme_api` | Package directory, all Python imports |
| `__SERVICE_NAME__` | `acme-api` | Docker image name, `docker-compose.yml` |
| `__OWNER__` | `acme-org` | `pyproject.toml`, GitHub Actions workflows |
| `__DESCRIPTION__` | `Internal API for Acme` | `pyproject.toml`, `README.md`, OpenAPI description |

---

## Quickstart

```bash
# Prerequisites: Python 3.12+, Poetry

make lock             # Generate/update poetry.lock for deterministic installs
make install          # Install all dependencies
cp .env.example .env  # Configure environment variables (edit as needed)
make migrate          # Apply Alembic migrations
make run              # Start with hot-reload at http://localhost:8000

# Smoke tests
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/ping
curl -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Widget","price":9.99}'
```

### Docker

```bash
make docker-build                                        # Build production image
make docker-up                                           # Start via docker-compose
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app make migrate
docker compose --profile with-redis up --build -d       # Include Redis
make docker-down                                         # Stop services
```

---

## API Documentation

All documentation endpoints are served under `/api/` (not versioned):

| URL | Description |
|---|---|
| `http://localhost:8000/api/docs` | Swagger UI |
| `http://localhost:8000/api/redoc` | ReDoc |
| `http://localhost:8000/api/openapi.json` | OpenAPI JSON schema |

Health probes (stable, version-independent):

| URL | Description |
|---|---|
| `http://localhost:8000/health` | Liveness — process is alive |
| `http://localhost:8000/ready` | Readiness — dependencies reachable |

Auth endpoint:

| URL | Description |
|---|---|
| `http://localhost:8000/api/v1/auth/token` | OAuth2 password flow token endpoint |

Readiness is extensible via `core.readiness.register_readiness_check(...)`, so new
dependencies (database, cache, broker) can be wired without changing the endpoint contract.
Database migrations are managed with Alembic (`alembic.ini` + `alembic/versions/`).

---

## Development Workflow

### Commands

```bash
make format      # Format with black + ruff --fix
make lint        # Lint with ruff (no auto-fix)
make typecheck   # Static type check with pyright
make test        # Run pytest with coverage report
make run-prod    # Run production-style server locally
make lock        # Refresh dependency lockfile
make migrate     # Apply DB migrations
make migrate-new MSG="add users table"  # Generate migration
```

### Pre-commit hooks

```bash
# Installed automatically by `make install`
# Or manually:
poetry run pre-commit install
poetry run pre-commit run --all-files
```

Hooks on every commit: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `black`, and `ruff`.

### Adding a new feature

1. Create `src/__PROJECT_SLUG__/api/v1/features/<feature>/`.
2. Add `schemas.py` (Pydantic models), `service.py` (business logic), `router.py` (FastAPI routes).
3. Register the router in `api/v1/router.py`.
4. Add integration tests in `tests/integration/test_<feature>.py`.

---

## Production Runtime

Production runtime is configurable via environment variables:

```bash
APP_WEB_CONCURRENCY=2
APP_KEEPALIVE_TIMEOUT=5
APP_BACKLOG=2048
APP_LIMIT_CONCURRENCY=1000   # 0 disables this uvicorn limit
APP_PROXY_HEADERS=true
APP_FORWARDED_ALLOW_IPS=10.0.0.0/8,127.0.0.1
```

Docker image entrypoint uses `scripts/run-production.sh` and applies these settings automatically.
See [docs/deployment.md](docs/deployment.md) for deployment-oriented defaults.

---

## Database

The template includes SQLAlchemy async persistence and Alembic migrations.

```bash
make migrate
make migrate-new MSG="create invoices table"
```

See [docs/database.md](docs/database.md) for PostgreSQL configuration, pooling settings, and migration workflow.
Database-focused test suite: `tests/db/`.

---

## Security

Security baseline included in the template:

- JWT auth scaffolding with OAuth2 password flow (`/api/v1/auth/token`)
- Scope-based authorization dependency (`items:write` on item creation)
- Rate limiting middleware with pluggable backend:
  - in-memory sliding window (single-process)
  - Redis fixed-window (multi-instance / HA)
- Readiness includes Redis backend check when `APP_RATE_LIMIT_BACKEND=redis`
- Security headers middleware (CSP, frame, referrer, permissions, HSTS optional)
- Trusted host middleware (configured by `APP_ALLOWED_HOSTS`)
- Optional `X-Forwarded-For` trust for deployments behind L7 proxies (`APP_TRUST_X_FORWARDED_FOR`)

See [docs/security.md](docs/security.md) for settings and usage examples.

---

## Observability

### Request tracing

Every request carries a `X-Request-ID` header:

- If the client sends `X-Request-ID`, the value is preserved and echoed in the response.
- Otherwise, a UUID4 is generated.
- The ID is bound to structlog's contextvars so it appears in **every log record** during the request lifecycle.

```bash
curl -H "X-Request-ID: my-trace-id" http://localhost:8000/api/v1/ping -v
# < X-Request-ID: my-trace-id
```

### Structured logging

| Mode | Format | Enable |
|---|---|---|
| Local dev | Colorized console | `APP_DEBUG=true` in `.env` |
| Production | JSON per line | `APP_DEBUG=false` (default in Docker) |

### OpenTelemetry (optional)

```bash
poetry install --with otel    # Install OTel packages

# Enable via environment variables:
APP_OTEL_ENABLED=true
APP_OTEL_ENDPOINT=http://localhost:4317
APP_OTEL_SERVICE_NAME=__SERVICE_NAME__
```

See [docs/observability.md](docs/observability.md) for a local Jaeger quickstart and full instrumentation details.

---

## Multi-Tenancy

Tenant context is resolved from the `X-Tenant-ID` request header:

- Missing header → defaults to `"public"`.
- Stored in a `ContextVar` — async-safe across concurrent requests.
- Available in route handlers via `Depends(get_tenant_id)` or by calling `get_tenant_id()` directly.
- Automatically included in all log records as `tenant_id`.

```bash
curl -H "X-Tenant-ID: acme" -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Widget","price":9.99}'
# Response includes: "tenant_id": "acme"
```

---

## Repository Structure

```
src/__PROJECT_SLUG__/
├── main.py                      # App factory: create_app() + module-level `app`
├── api/
│   └── v1/
│       ├── router.py            # v1 route aggregator
│       └── features/
│           ├── auth/            # POST /api/v1/auth/token
│           ├── ping/            # GET /api/v1/ping
│           └── items/           # POST /api/v1/items
├── core/
│   ├── config.py                # pydantic-settings (12-factor)
│   ├── db/                      # SQLAlchemy async engine/session + metadata
│   ├── errors.py                # Consistent JSON error envelope
│   ├── logging.py               # structlog pipeline
│   ├── otel.py                  # Optional OpenTelemetry setup
│   ├── security/                # JWT auth helpers + principal dependency
│   └── middleware/
│       ├── rate_limit.py        # Request throttling
│       ├── request_id.py        # X-Request-ID propagation
│       ├── security_headers.py  # HTTP response hardening headers
│       └── tenant.py            # X-Tenant-ID → ContextVar
└── health/
    └── router.py                # /health  /ready

alembic/
└── versions/                    # Database migration history

scripts/
└── run-production.sh            # Uvicorn production launcher (workers/timeouts/proxy)
```

---

## Releasing

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add rate limiting middleware
fix: correct item price validation
docs: update observability guide
chore: bump structlog to 24.4
```

**Creating a release:**

```bash
git tag v1.0.0
git push origin v1.0.0
```

The `release.yml` GitHub Actions workflow triggers on tag push, builds and pushes the Docker image to `ghcr.io`, and creates a GitHub Release with auto-generated changelog.

**Semantic versioning:** `MAJOR.MINOR.PATCH`

| Bump | When |
|---|---|
| `PATCH` | Bug fixes, non-breaking dependency updates |
| `MINOR` | New features, non-breaking API additions |
| `MAJOR` | Breaking API changes (new URL version or removed endpoints) |
