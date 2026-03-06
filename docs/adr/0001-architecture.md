# ADR-0001: Core Architecture Decisions

**Date:** 2024-01-01
**Status:** Accepted

---

## Context

This document records the key architectural decisions made when designing the `__PROJECT_NAME__` template. Each decision documents the rationale and trade-offs so future maintainers can understand *why* the project is structured as it is, not just *how*.

---

## Decision 1: `src/` Layout

**Chosen:** `src/__PROJECT_SLUG__/` package layout.

**Rationale:** Without a `src/` prefix, running `python` or `pytest` from the repository root would resolve `import __PROJECT_SLUG__` to the local directory even without `pip install / poetry install`. This silently bypasses the installed package and produces version-mismatch bugs that are difficult to diagnose. The `src/` layout ensures the package is only importable after installation, catching missing setup steps at import time rather than at runtime.

**Trade-off:** Requires `packages = [{include = "...", from = "src"}]` in `pyproject.toml` and `pythonpath = ["src"]` in `[tool.pytest.ini_options]`.

---

## Decision 2: Pure ASGI Middleware + Ordering

**Chosen:** Request/tenant context middleware implemented as pure ASGI middleware and registered in reverse order (`TenantMiddleware` first, `RequestIDMiddleware` second).

**Rationale:** Starlette executes middleware in reverse registration order, so this setup guarantees `RequestIDMiddleware` runs first on ingress and binds `request_id` before tenant binding or route execution. Pure ASGI middleware avoids `BaseHTTPMiddleware` limitations for streaming responses and context propagation.

**Execution order per request:**
1. `RequestIDMiddleware` enters → clears context → binds `request_id`
2. `TenantMiddleware` enters → binds `tenant_id`
3. Route handler executes (all logs include both `request_id` and `tenant_id`)
4. `TenantMiddleware` exits → resets tenant context
5. `RequestIDMiddleware` exits → writes `X-Request-ID` header

**Trade-off:** Pure ASGI middleware is slightly more verbose than `BaseHTTPMiddleware`, but avoids subtle runtime edge cases.

---

## Decision 3: Optional OpenTelemetry Group

**Chosen:** OTel packages as an optional Poetry dependency group (`--with otel`).

**Rationale:** OpenTelemetry adds ~15 MB to the image and several hundred milliseconds to cold start. Services that do not export traces should not pay this cost. The optional group pattern lets teams opt in per deployment environment. The `try/except ImportError` safety net in `core/otel.py` ensures a misconfigured deployment (OTel enabled via env var but packages not installed) logs a warning rather than crashing.

**Trade-off:** Developers must remember to run `poetry install --with otel` to enable tracing locally.

---

## Decision 4: SQLAlchemy Async + Alembic Migrations

**Chosen:** Built-in async persistence stack with SQLAlchemy ORM, Alembic migrations, and PostgreSQL-ready configuration.

**Rationale:** A production-ready FastAPI golden path should include persistence, migration workflow, and connection pooling defaults. Shipping this stack in the template reduces bootstrap churn and aligns teams on one proven architecture.

**Trade-off:** Increased template complexity and dependency footprint compared to in-memory examples. To keep local onboarding friction low, SQLite remains available for zero-setup development.

---

## Decision 5: Multitenancy via Request Header + ContextVar

**Chosen:** `X-Tenant-ID` header resolved in `TenantMiddleware`, stored in `ContextVar`.

**Rationale:** `ContextVar` propagation remains the simplest async-safe way to expose tenant context across handlers, services, and logs. This works with database-backed repositories and keeps the HTTP contract explicit.

**Upgrade path:** Add tenant table validation and authorization checks in middleware/service layer (for example, unknown tenant → `HTTP 403`).

---

## Decision 6: Health Endpoints at Root (No `/api/v1` Prefix)

**Chosen:** `GET /health` and `GET /ready` at root level.

**Rationale:** Kubernetes liveness/readiness probes, AWS ALB health checks, and most load balancers expect health endpoints at a stable, version-independent URL. Placing them under `/api/v1` would require updating all infrastructure configuration on every API version bump.

**Trade-off:** Health endpoints are outside the versioned API and therefore not covered by API versioning policies. This is intentional and standard practice.
