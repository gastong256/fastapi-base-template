#!/usr/bin/env bash
set -euo pipefail

APP_MODULE="${APP_MODULE:-__PROJECT_SLUG__.main:app}"
HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-8000}"
WEB_CONCURRENCY="${APP_WEB_CONCURRENCY:-1}"
KEEPALIVE_TIMEOUT="${APP_KEEPALIVE_TIMEOUT:-5}"
BACKLOG="${APP_BACKLOG:-2048}"
LIMIT_CONCURRENCY="${APP_LIMIT_CONCURRENCY:-0}"
PROXY_HEADERS="${APP_PROXY_HEADERS:-false}"
FORWARDED_ALLOW_IPS="${APP_FORWARDED_ALLOW_IPS:-127.0.0.1}"

if ! [[ "$WEB_CONCURRENCY" =~ ^[0-9]+$ ]] || [ "$WEB_CONCURRENCY" -lt 1 ]; then
  echo "APP_WEB_CONCURRENCY must be an integer >= 1" >&2
  exit 1
fi

if ! [[ "$KEEPALIVE_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$KEEPALIVE_TIMEOUT" -lt 1 ]; then
  echo "APP_KEEPALIVE_TIMEOUT must be an integer >= 1" >&2
  exit 1
fi

if ! [[ "$BACKLOG" =~ ^[0-9]+$ ]] || [ "$BACKLOG" -lt 1 ]; then
  echo "APP_BACKLOG must be an integer >= 1" >&2
  exit 1
fi

if ! [[ "$LIMIT_CONCURRENCY" =~ ^[0-9]+$ ]]; then
  echo "APP_LIMIT_CONCURRENCY must be an integer >= 0" >&2
  exit 1
fi

cmd=(
  uvicorn "$APP_MODULE"
  --host "$HOST"
  --port "$PORT"
  --workers "$WEB_CONCURRENCY"
  --timeout-keep-alive "$KEEPALIVE_TIMEOUT"
  --backlog "$BACKLOG"
)

if [ "$LIMIT_CONCURRENCY" -gt 0 ]; then
  cmd+=(--limit-concurrency "$LIMIT_CONCURRENCY")
fi

if [ "$PROXY_HEADERS" = "true" ]; then
  cmd+=(--proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS")
fi

exec "${cmd[@]}"
