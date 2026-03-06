from starlette.testclient import TestClient

from __PROJECT_SLUG__.core.readiness import register_readiness_check
from __PROJECT_SLUG__.main import create_app


def test_liveness(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_is_independent_of_api_prefix(client: TestClient) -> None:
    """Health endpoints must not require the /api/v1 prefix."""
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 404


def test_readiness_returns_503_when_dependency_check_fails() -> None:
    app = create_app()

    async def _failing_database_check(_app: object) -> None:
        raise RuntimeError("database is unavailable")

    register_readiness_check(app, "database", _failing_database_check)

    with TestClient(app) as test_client:
        response = test_client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "HTTP_503"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
