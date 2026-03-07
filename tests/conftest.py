import os
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from __PROJECT_SLUG__.api.v1.features.items import service as items_service
from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.core.db import get_db_session
from __PROJECT_SLUG__.core.readiness import register_readiness_check


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[None, None, None]:
    db_dir = tmp_path_factory.mktemp("db")
    db_path = db_dir / "test.db"
    test_database_url = f"sqlite+aiosqlite:///{db_path}"

    previous = {
        "APP_ENVIRONMENT": os.environ.get("APP_ENVIRONMENT"),
        "APP_DATABASE_URL": os.environ.get("APP_DATABASE_URL"),
        "APP_DATABASE_AUTO_CREATE_SCHEMA": os.environ.get("APP_DATABASE_AUTO_CREATE_SCHEMA"),
        "APP_DATABASE_CONNECT_ON_STARTUP": os.environ.get("APP_DATABASE_CONNECT_ON_STARTUP"),
        "APP_AUTH_ENABLED": os.environ.get("APP_AUTH_ENABLED"),
    }

    os.environ["APP_ENVIRONMENT"] = "test"
    os.environ["APP_DATABASE_URL"] = test_database_url
    os.environ["APP_DATABASE_AUTO_CREATE_SCHEMA"] = "false"
    os.environ["APP_DATABASE_CONNECT_ON_STARTUP"] = "false"
    os.environ["APP_AUTH_ENABLED"] = "false"
    get_settings.cache_clear()

    yield

    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    get_settings.cache_clear()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def reset_item_store() -> None:
    items_service.clear_store()
    yield
    items_service.clear_store()


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    """Function-scoped AsyncClient for deterministic test isolation."""
    from __PROJECT_SLUG__.main import create_app

    app = create_app()

    async def _no_db_session():
        # Integration tests in this suite validate HTTP contracts and middleware behavior.
        # DB behavior is covered in tests/db with a real PostgreSQL backend.
        yield None

    async def _database_readiness_noop(_app: object) -> None:
        return None

    app.dependency_overrides[get_db_session] = _no_db_session
    register_readiness_check(app, "database", _database_readiness_noop)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c
