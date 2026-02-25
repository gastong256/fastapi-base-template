# API Versioning

## Strategy

This project uses **URI path versioning** (`/api/v1`, `/api/v2`, …). URI versioning is explicit, easy to test with `curl`, and requires no special header negotiation.

The OpenAPI schema, Swagger UI, and ReDoc are served under `/api/` (not under a versioned prefix) so tooling always resolves to the full multi-version spec.

---

## Current Structure

```
/api/openapi.json   ← Full OpenAPI schema (all versions)
/api/docs           ← Swagger UI
/api/redoc          ← ReDoc
/api/v1/ping
/api/v1/items
```

---

## Adding a New Version (v2)

1. Create the router module:

   ```
   src/__PROJECT_SLUG__/api/v2/
   ├── __init__.py
   ├── router.py
   └── features/
       └── items/
           ├── router.py
           └── schemas.py   ← New response shape
   ```

2. Implement `v2_router` in `api/v2/router.py`:

   ```python
   from fastapi import APIRouter
   from __PROJECT_SLUG__.api.v2.features.items.router import router as items_router

   v2_router = APIRouter()
   v2_router.include_router(items_router)
   ```

3. Register in `main.py`:

   ```python
   from __PROJECT_SLUG__.api.v2.router import v2_router

   app.include_router(v1_router, prefix="/api/v1")
   app.include_router(v2_router, prefix="/api/v2")
   ```

4. Tag v2 routes distinctly so Swagger separates them:

   ```python
   router = APIRouter(prefix="/items", tags=["items:v2"])
   ```

---

## Deprecation Policy

1. Announce deprecation in the v1 OpenAPI description (`deprecated=True` on the route).
2. Add a `Deprecation` response header in the v1 router.
3. Maintain v1 for at least one release cycle (one minor version bump or 90 days, whichever is longer).
4. Remove v1 in the next major version.

```python
# Mark a route as deprecated in OpenAPI:
@router.get("", response_model=ItemResponse, deprecated=True)
async def create_item_v1(...):
    ...
```

---

## Non-Breaking vs Breaking Changes

| Change | Classification |
|---|---|
| Adding optional request fields | Non-breaking |
| Adding response fields | Non-breaking (consumers must ignore unknown fields) |
| Removing or renaming fields | **Breaking → new version** |
| Changing field types | **Breaking → new version** |
| Changing HTTP status codes | **Breaking → new version** |
| Modifying validation rules (stricter) | **Breaking → new version** |
