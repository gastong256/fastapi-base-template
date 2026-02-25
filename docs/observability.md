# Observability

## Structured Logging

This project uses [structlog](https://www.structlog.org/) with a unified processor pipeline that bridges both structlog and standard library (`logging`) loggers through the same formatter.

### Log format

| Environment | Format | Command |
|---|---|---|
| `debug=True` (local dev) | Colorized, human-readable | `DEBUG=true make run` |
| `debug=False` (production) | JSON, one object per line | Default in Docker |

### Automatic context fields

Every log record includes the following fields, automatically injected by middleware via `structlog.contextvars`:

| Field | Source | Example |
|---|---|---|
| `request_id` | `RequestIDMiddleware` | `"550e8400-e29b-41d4-a716-446655440000"` |
| `tenant_id` | `TenantMiddleware` | `"acme"` |
| `timestamp` | `TimeStamper` processor | `"2024-01-01T00:00:00.000Z"` |
| `level` | `add_log_level` processor | `"info"` |
| `logger` | `add_logger_name` processor | `"__PROJECT_SLUG__.api.v1.features.items.router"` |

### Usage in route handlers

```python
import structlog

log = structlog.get_logger()

async def create_item(payload: ItemCreate) -> ItemResponse:
    log.info("creating_item", name=payload.name, price=payload.price)
    ...
```

`request_id` and `tenant_id` are automatically included — no need to pass them manually.

---

## Request ID (`X-Request-ID`)

- **On ingress:** If the client sends `X-Request-ID`, the value is preserved.
- **On egress:** `X-Request-ID` is always present in the response header.
- **In logs:** Bound via `structlog.contextvars` so every log line in the request lifecycle includes it.

**Testing with curl:**
```bash
curl -H "X-Request-ID: my-trace-123" http://localhost:8000/api/v1/ping -v
# < X-Request-ID: my-trace-123
```

---

## Tenant ID (`X-Tenant-ID`)

- Resolved from the `X-Tenant-ID` request header.
- Defaults to `"public"` when the header is absent.
- Accessible in any layer via `get_tenant_id()` from `core.middleware.tenant`.

**Testing with curl:**
```bash
curl -H "X-Tenant-ID: acme" -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Widget","price":9.99}'
# Response: {"tenant_id": "acme", ...}
```

---

## OpenTelemetry (Optional)

### Install

```bash
poetry install --with otel
```

### Enable

Set the following environment variables (in `.env` or as system env):

```bash
OTEL_ENABLED=true
OTEL_ENDPOINT=http://localhost:4317        # OTLP gRPC endpoint
OTEL_SERVICE_NAME=__SERVICE_NAME__
```

### What gets instrumented

- **FastAPI** — All HTTP requests become spans with route, method, and status code attributes.
- **httpx** — Outgoing HTTP calls (if using `httpx.Client` or `httpx.AsyncClient`) become child spans.

### Local Jaeger quickstart

```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Then start the app with OTel enabled:
OTEL_ENABLED=true OTEL_ENDPOINT=http://localhost:4317 make run

# View traces at:
open http://localhost:16686
```

### Disabling OTel

Set `OTEL_ENABLED=false` (the default). The `core/otel.py` module uses lazy imports inside a `try/except ImportError`, so the app runs safely even if the `otel` poetry group is not installed.

---

## Error Envelope

All API errors return a consistent JSON envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

| Field | Description |
|---|---|
| `code` | Machine-readable error code (`VALIDATION_ERROR`, `HTTP_404`, `INTERNAL_ERROR`) |
| `message` | Human-readable description, safe for display |
| `request_id` | Correlates the error with server logs |
