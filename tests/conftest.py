import pytest
from starlette.testclient import TestClient

from __PROJECT_SLUG__.api.v1.features.items import service as items_service
from __PROJECT_SLUG__.main import create_app


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
