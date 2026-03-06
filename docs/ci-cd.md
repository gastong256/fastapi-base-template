# CI/CD

## CI workflow (`.github/workflows/ci.yml`)

Jobs:

- `quality`
  - initializes template placeholders
  - installs dependencies
  - runs `poetry check --lock`
  - runs lint/format/typecheck
  - runs unit + integration tests with SQLite
  - runs production launcher smoke test (`scripts/run-production.sh` + `/health`/`/ready`)
- `db-postgres`
  - starts PostgreSQL service container
  - applies Alembic migrations
  - runs DB-focused repository/concurrency/auth tests against PostgreSQL
- `docker`
  - builds final runtime image target

## Security workflow (`.github/workflows/security.yml`)

Jobs:

- `dependency-audit`: runs `pip-audit` over installed dependencies
- `bandit`: runs static security scan on `src/`

## Dependency automation

`dependabot.yml` tracks updates for:

- Python dependencies (`pip` ecosystem)
- GitHub Actions
- Docker base images
