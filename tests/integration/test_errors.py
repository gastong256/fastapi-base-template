import httpx
from fastapi import HTTPException

from __PROJECT_SLUG__.main import create_app


async def test_validation_error_envelope_uses_same_request_id_as_response(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/api/v1/items", json={"name": "", "price": 1.0})

    assert response.status_code == 422
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


async def test_http_exception_preserves_headers_and_request_id() -> None:
    app = create_app()

    @app.get("/_test/http-exception")
    async def _raise_http_exception() -> None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
            response = await test_client.get("/_test/http-exception")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "HTTP_401"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
