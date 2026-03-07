import httpx

from __PROJECT_SLUG__.core.readiness import register_readiness_check
from __PROJECT_SLUG__.main import create_app


async def test_liveness(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness(client: httpx.AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_liveness_is_independent_of_api_prefix(client: httpx.AsyncClient) -> None:
    """Health endpoints must not require the /api/v1 prefix."""
    assert (await client.get("/health")).status_code == 200
    assert (await client.get("/api/v1/health")).status_code == 404


async def test_readiness_returns_503_when_dependency_check_fails() -> None:
    app = create_app()

    async def _failing_database_check(_app: object) -> None:
        raise RuntimeError("database is unavailable")

    register_readiness_check(app, "database", _failing_database_check)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as test_client:
        response = await test_client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "HTTP_503"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
