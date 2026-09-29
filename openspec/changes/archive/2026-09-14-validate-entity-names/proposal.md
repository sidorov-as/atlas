## Why

Every entity create/edit form (System, Component, Resource, API) and the Flow create/edit form let `name` be submitted empty, whitespace-only, or containing `/`/`:`. Nothing in the chain rejects it: the frontend forms have no `required`/validation, the Pydantic request schemas (`MetadataIn`/`MetadataPatch`, `FlowIn`/`FlowPatch`) place no constraint on `name`, and the Django model layer never runs `full_clean()` (`EntityService` calls `entity.save()` directly). An entity or Flow can end up with a blank or ambiguous name, and a name containing `:` cannot be unambiguously referenced by a bare `kind:name` ref elsewhere in the system (`refs.py`'s `REF_PATTERN` would parse the `:` as a kind separator).

## What Changes

- `MetadataIn`/`MetadataPatch` (`plugin-api/python/atlas_plugin_api/schemas.py`) gain a `name` validator: strip whitespace, reject empty, reject `/` or `:`. This is the single envelope every entity kind (System/Component/Resource/API, plus admin-only Group/Actor) nests as `metadata`, and it's the same schema `catalog-info.yaml` ingestion validates manifest documents against — so the CRUD API, Django admin, and YAML ingestion are all covered by this one change.
- `FlowIn`/`FlowPatch` (`plugins/flows/backend/atlas_plugin_flows/api/schemas.py`) get the identical `name` validator — Flow is not a `CatalogEntity` and does not go through `MetadataIn`, so it needs its own copy of the same rule.
- The now-redundant manual `if '/' in document.metadata.name` check in `plugins/ingestion/backend/atlas_plugin_ingestion/validation.py` is removed, since the schema itself now enforces it (with a friendlier, earlier Pydantic validation error instead of a hand-rolled `ManifestError`).
- `EntityFormShell.tsx`'s shared Name `TextInput` (used by System/Component/Resource/API forms) and `FlowFormPage.tsx`'s own Name `TextInput` both gain `required`, so the browser blocks submission of an empty/whitespace name client-side. No new client-side validation logic or UI is added — a rejected `/`/`:` name still surfaces through the existing `Alert theme="danger"` error path already wired into each form's submit handler.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `entity-catalog`: the "Entity envelope" requirement gains a `metadata.name` format constraint (non-empty after trim, no `/` or `:`) enforced on create and update.
- `flow-management`: the "Flow belongs to exactly one home System" requirement gains the same `name` format constraint.

## Impact

- Backend: `plugin-api/python/atlas_plugin_api/schemas.py`, `plugins/flows/backend/atlas_plugin_flows/api/schemas.py`, `plugins/ingestion/backend/atlas_plugin_ingestion/validation.py`.
- Frontend: `core/frontend/src/components/EntityFormShell.tsx`, `plugins/flows/frontend/src/pages/FlowFormPage.tsx`.
- Tests: `plugin-api/python/atlas_plugin_api/tests/test_schemas.py`, `core/backend/server/apps/catalog/tests/test_entity_crud.py`, flows backend schema tests, `plugins/flows/frontend/src/pages/FlowFormPage.test.tsx`, and any `EntityFormShell`/form-page frontend tests covering the Name field.
- No database migration: `CatalogEntity.name` (`core/backend/server/apps/catalog/models/base.py`) is unchanged; the constraint is enforced at the request-schema layer, not the model layer. No backfill for any pre-existing empty-name rows.
- Out of scope: Endpoint/Operation `name` fields (`plugins/apis/backend/atlas_plugin_apis/api/schemas.py`) — read-only, no self-service create/edit API; broader kebab-case/slug naming-convention validation beyond `/` and `:`.
