import os
from collections.abc import Generator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from __PROJECT_SLUG__.api.v1.features.items import service as items_service
from __PROJECT_SLUG__.core.config import get_settings
from __PROJECT_SLUG__.main import create_app

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(tmp_path_factory: pytest.TempPathFactory) -> Generator[None, None, None]:
    db_dir = tmp_path_factory.mktemp("db")
    db_path = db_dir / "test.db"
    test_database_url = f"sqlite+aiosqlite:///{db_path}"

    previous = {
        "APP_ENVIRONMENT": os.environ.get("APP_ENVIRONMENT"),
        "APP_DATABASE_URL": os.environ.get("APP_DATABASE_URL"),
        "APP_DATABASE_AUTO_CREATE_SCHEMA": os.environ.get("APP_DATABASE_AUTO_CREATE_SCHEMA"),
        "APP_DATABASE_CONNECT_ON_STARTUP": os.environ.get("APP_DATABASE_CONNECT_ON_STARTUP"),
    }

    os.environ["APP_ENVIRONMENT"] = "test"
    os.environ["APP_DATABASE_URL"] = test_database_url
    os.environ["APP_DATABASE_AUTO_CREATE_SCHEMA"] = "true"
    os.environ["APP_DATABASE_CONNECT_ON_STARTUP"] = "false"
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


@pytest.fixture
def client() -> TestClient:
    """Function-scoped TestClient for deterministic test isolation."""
    with TestClient(create_app()) as c:
        yield c
