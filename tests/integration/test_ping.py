from starlette.testclient import TestClient


def test_ping_returns_pong(client: TestClient) -> None:
    response = client.get("/api/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"message": "pong"}


def test_ping_generates_request_id_when_absent(client: TestClient) -> None:
    response = client.get("/api/v1/ping")

    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_ping_echoes_client_request_id(client: TestClient) -> None:
    custom_id = "test-request-id-abc123"
    response = client.get("/api/v1/ping", headers={"X-Request-ID": custom_id})

    assert response.headers["X-Request-ID"] == custom_id
