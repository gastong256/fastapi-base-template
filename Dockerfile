# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir "poetry==1.8.*"

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.in-project true \
    && poetry install --without dev --no-root --no-interaction --no-ansi

COPY src/ ./src/

RUN poetry install --without dev --no-interaction --no-ansi


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --gid 1001 app \
    && useradd --uid 1001 --gid app --no-create-home --shell /sbin/nologin app

WORKDIR /app

COPY --from=builder /build/.venv ./.venv
COPY --from=builder /build/src ./src

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

USER app

EXPOSE 8000

CMD ["uvicorn", "__PROJECT_SLUG__.main:app", "--host", "0.0.0.0", "--port", "8000"]
