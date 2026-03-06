# Security

## Auth

This template includes JWT auth scaffolding using OAuth2 password flow.

### Settings

```bash
APP_AUTH_ENABLED=true
APP_AUTH_JWT_SECRET=replace-with-long-random-secret-min-32-chars
APP_AUTH_JWT_ALGORITHM=HS256
APP_AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_AUTH_ISSUER=__SERVICE_NAME__
APP_AUTH_AUDIENCE=__SERVICE_NAME__-clients
APP_AUTH_ADMIN_USERNAME=admin
APP_AUTH_ADMIN_PASSWORD=change-me
APP_AUTH_ADMIN_SCOPES=items:read,items:write
```

### Token Flow

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=change-me&scope=items:write"
```

Use returned bearer token:

```bash
curl -X POST http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Secure item","price":10.5}'
```

When `APP_AUTH_ENABLED=false`, scope dependencies are bypassed for local development.

## Rate Limiting

Limiter key: `client_ip + tenant_id + path`.

### Local / single instance

```bash
APP_RATE_LIMIT_ENABLED=true
APP_RATE_LIMIT_BACKEND=memory
APP_RATE_LIMIT_REQUESTS=120
APP_RATE_LIMIT_WINDOW_SECONDS=60
APP_RATE_LIMIT_FAIL_OPEN=true
APP_RATE_LIMIT_EXEMPT_PATHS=/health,/ready,/api/docs,/api/redoc,/api/openapi.json
```

### Multi-instance / HA (Redis backend)

```bash
APP_RATE_LIMIT_ENABLED=true
APP_RATE_LIMIT_BACKEND=redis
APP_RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
APP_RATE_LIMIT_REDIS_PREFIX=__SERVICE_NAME__
APP_RATE_LIMIT_REQUESTS=120
APP_RATE_LIMIT_WINDOW_SECONDS=60
APP_RATE_LIMIT_FAIL_OPEN=true
```

- `APP_RATE_LIMIT_FAIL_OPEN=true`: if Redis is temporarily unavailable, requests continue (higher availability).
- `APP_RATE_LIMIT_FAIL_OPEN=false`: if Redis is unavailable, requests return `503 RATE_LIMIT_UNAVAILABLE` (stricter enforcement).
- `APP_TRUST_X_FORWARDED_FOR=true`: use first IP from `X-Forwarded-For` (enable only behind trusted proxy/load balancer).

## Security Headers

```bash
APP_SECURITY_HEADERS_ENABLED=true
APP_SECURITY_CSP=default-src 'self'; frame-ancestors 'none'; base-uri 'self'
APP_SECURITY_HSTS_ENABLED=true
APP_SECURITY_HSTS_SECONDS=31536000
```

Headers applied by middleware:

- `Content-Security-Policy`
- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- `Strict-Transport-Security` (optional)
