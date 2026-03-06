# Database

## Stack

- SQLAlchemy 2.x async ORM
- Alembic for schema migrations
- `asyncpg` for PostgreSQL
- `aiosqlite` as lightweight local default

## Configuration

Environment variables (`.env`):

```bash
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app
APP_DATABASE_ECHO=false
APP_DATABASE_POOL_SIZE=10
APP_DATABASE_MAX_OVERFLOW=20
APP_DATABASE_POOL_TIMEOUT=30
APP_DATABASE_POOL_RECYCLE=1800
APP_DATABASE_CONNECT_ON_STARTUP=true
APP_DATABASE_AUTO_CREATE_SCHEMA=false
```

In production (`APP_ENVIRONMENT=prod`), this template requires a PostgreSQL async URL
(`postgresql+asyncpg://...`).

For quick local setup without PostgreSQL:

```bash
APP_DATABASE_URL=sqlite+aiosqlite:///./app.db
APP_DATABASE_AUTO_CREATE_SCHEMA=true
```

## Migrations

```bash
make migrate                            # upgrade to head
make migrate-down                       # downgrade one revision
make migrate-new MSG="add users table" # create new revision
```

Alembic files:

- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/*`

## Docker

`docker-compose.yml` includes a `postgres` service and wires app DB URL to it:

```bash
make docker-up
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app make migrate
```

## Testing

Database-focused tests live in `tests/db/`:

```bash
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app \
  PYTHONPATH=src pytest tests/db
```

`tests/db` intentionally target the production persistence path and require PostgreSQL.
If `APP_DATABASE_URL` is not a PostgreSQL async URL, the suite is skipped.

They cover:

- Alembic upgrade/downgrade path
- Repository persistence behavior
- Concurrent write behavior for `items`
- Auth persistence flow (`users` + `refresh_tokens`)
