from __PROJECT_SLUG__.api.v1.features.items import service
from __PROJECT_SLUG__.api.v1.features.items.schemas import ItemCreate


def test_create_item_returns_response_with_id() -> None:
    payload = ItemCreate(name="Widget", price=9.99)
    result = service.create_item(payload, tenant_id="acme")

    assert result.name == "Widget"
    assert result.price == 9.99
    assert result.tenant_id == "acme"
    assert result.id is not None
    assert result.created_at is not None


def test_create_item_with_optional_description() -> None:
    payload = ItemCreate(name="Gadget", description="A useful gadget", price=19.99)
    result = service.create_item(payload, tenant_id="public")

    assert result.description == "A useful gadget"


def test_create_item_ids_are_unique() -> None:
    payload = ItemCreate(name="Duplicate", price=1.0)
    a = service.create_item(payload, tenant_id="t1")
    b = service.create_item(payload, tenant_id="t1")

    assert a.id != b.id


def test_create_item_stamps_tenant_id() -> None:
    payload = ItemCreate(name="Multi-tenant item", price=5.0)
    result = service.create_item(payload, tenant_id="tenant-xyz")

    assert result.tenant_id == "tenant-xyz"
