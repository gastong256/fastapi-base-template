# Deployment

## Runtime command

Production container starts via:

```bash
./scripts/run-production.sh
```

This script configures uvicorn from environment variables and supports safe defaults.

## Runtime settings

```bash
APP_MODULE=__PROJECT_SLUG__.main:app
APP_HOST=0.0.0.0
APP_PORT=8000
APP_WEB_CONCURRENCY=1
APP_KEEPALIVE_TIMEOUT=5
APP_BACKLOG=2048
APP_LIMIT_CONCURRENCY=0
APP_PROXY_HEADERS=false
APP_FORWARDED_ALLOW_IPS=127.0.0.1
```

Notes:

- `APP_LIMIT_CONCURRENCY=0` disables uvicorn limit.
- Set `APP_PROXY_HEADERS=true` only when traffic always comes through trusted reverse proxies/load balancers.
- Keep `APP_FORWARDED_ALLOW_IPS` restricted to proxy/LB address ranges when possible.

## Local production-like run

```bash
make run-prod
```
