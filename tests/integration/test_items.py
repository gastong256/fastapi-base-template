import httpx


async def test_create_item_returns_201_with_payload(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/items",
        json={"name": "Widget", "price": 9.99},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Widget"
    assert data["price"] == 9.99
    assert "id" in data
    assert "created_at" in data


async def test_create_item_stamps_default_tenant(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/items", json={"name": "Item A", "price": 1.0})

    assert response.status_code == 201
    assert response.json()["tenant_id"] == "public"


async def test_create_item_with_description(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/items",
        json={"name": "Gadget", "description": "A useful gadget", "price": 19.99},
    )

    assert response.status_code == 201
    assert response.json()["description"] == "A useful gadget"


async def test_create_item_rejects_empty_name(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/items", json={"name": "", "price": 9.99})

    assert response.status_code == 422
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in body["error"]


async def test_create_item_rejects_negative_price(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/items", json={"name": "Bad", "price": -1.0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_item_rejects_missing_required_field(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/items", json={"name": "No price"})

    assert response.status_code == 422
