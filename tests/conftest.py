import pytest
from starlette.testclient import TestClient

from __PROJECT_SLUG__.main import create_app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped TestClient wrapping the FastAPI ASGI app.

    Session scope keeps app initialization cost to a single run per test session.
    Tests that mutate shared state (e.g. the in-memory item store) should use
    unique data per test rather than relying on isolation between tests.
    Switch to scope="function" if full per-test isolation is required.
    """
    with TestClient(create_app()) as c:
        yield c
