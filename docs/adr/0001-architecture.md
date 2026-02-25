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

## Decision 2: Middleware LIFO Ordering

**Chosen:** `add_middleware(RequestIDMiddleware)` called before `add_middleware(TenantMiddleware)`.

**Rationale:** Starlette builds the middleware stack as a LIFO chain. The first `add_middleware` call wraps the innermost position, meaning it executes **first** on ingress and **last** on egress. `RequestIDMiddleware` must execute first so that `request_id` is bound to structlog's context vars before `TenantMiddleware` (or any route handler) emits log records.

**Execution order per request:**
1. `RequestIDMiddleware` enters → clears context → binds `request_id`
2. `TenantMiddleware` enters → binds `tenant_id`
3. Route handler executes (all logs include both `request_id` and `tenant_id`)
4. `TenantMiddleware` exits → resets `_tenant_id` ContextVar
5. `RequestIDMiddleware` exits → writes `X-Request-ID` to response header

**Trade-off:** `BaseHTTPMiddleware` buffers the full response body before returning, which breaks streaming responses. For SSE or file downloads, replace with a pure ASGI middleware implementation. See [Starlette docs](https://www.starlette.io/middleware/#pure-asgi-middleware) for the upgrade path.

---

## Decision 3: Optional OpenTelemetry Group

**Chosen:** OTel packages as an optional Poetry dependency group (`--with otel`).

**Rationale:** OpenTelemetry adds ~15 MB to the image and several hundred milliseconds to cold start. Services that do not export traces should not pay this cost. The optional group pattern lets teams opt in per deployment environment. The `try/except ImportError` safety net in `core/otel.py` ensures a misconfigured deployment (OTel enabled via env var but packages not installed) logs a warning rather than crashing.

**Trade-off:** Developers must remember to run `poetry install --with otel` to enable tracing locally.

---

## Decision 4: In-Memory Item Store

**Chosen:** Module-level `dict[UUID, ItemResponse]` in `items/service.py`.

**Rationale:** Adding a database (SQLAlchemy, asyncpg, etc.) at the template level would triple the complexity and force technology choices on users. The in-memory store makes all tests fast, self-contained, and reproducible without external services. A comment block in `service.py` marks the exact insertion point for a repository layer.

**Trade-off:** Data is lost on restart. Tests sharing a session-scoped `TestClient` can observe state from other tests (e.g. items created in `test_create_item`). Tests use unique data and assert only on their own responses, avoiding cross-test dependencies.

---

## Decision 5: Multitenancy via Request Header (No Database)

**Chosen:** `X-Tenant-ID` header resolved in `TenantMiddleware`, stored in `ContextVar`.

**Rationale:** For a stateless API with no database, tenant isolation is achieved at the application layer via request context. The `ContextVar` pattern is async-safe: each coroutine inherits the parent context at creation time, and mutations do not propagate back. `get_tenant_id()` is a plain function callable from any layer (service, background task) without FastAPI `Depends` overhead.

**Upgrade path:** When adding a database, extend `TenantMiddleware` to validate the tenant against a tenants table and raise `HTTP 403` for unknown tenants.

---

## Decision 6: Health Endpoints at Root (No `/api/v1` Prefix)

**Chosen:** `GET /health` and `GET /ready` at root level.

**Rationale:** Kubernetes liveness/readiness probes, AWS ALB health checks, and most load balancers expect health endpoints at a stable, version-independent URL. Placing them under `/api/v1` would require updating all infrastructure configuration on every API version bump.

**Trade-off:** Health endpoints are outside the versioned API and therefore not covered by API versioning policies. This is intentional and standard practice.
