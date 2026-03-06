import httpx


async def test_request_id_generated_when_header_absent(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert "X-Request-ID" in response.headers


async def test_request_id_echoed_from_client(client: httpx.AsyncClient) -> None:
    rid = "my-correlation-id"
    response = await client.get("/health", headers={"X-Request-ID": rid})

    assert response.headers["X-Request-ID"] == rid


async def test_tenant_defaults_to_public(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/items", json={"name": "Item", "price": 1.0})

    assert response.status_code == 201
    assert response.json()["tenant_id"] == "public"


async def test_custom_tenant_header_propagated_to_response(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/items",
        json={"name": "Tenant item", "price": 5.0},
        headers={"X-Tenant-ID": "acme-corp"},
    )

    assert response.status_code == 201
    assert response.json()["tenant_id"] == "acme-corp"
