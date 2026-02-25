from starlette.testclient import TestClient


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
