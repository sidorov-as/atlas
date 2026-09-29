## Why

The catalog can only say a Service `consumesAPI` a whole API, which is too coarse for real impact analysis ("what breaks if I change `DELETE /v1/users/{id}`?") and gives no Swagger-like documentation of individual operations. This change adds an `Endpoint` sub-resource under `API` and a `Service consumesEndpoint Endpoint` relationship that refines the existing `consumesAPI` edge, so the catalog can answer endpoint-level "who uses this?" questions without replacing the API-level model.

## What Changes

- Add an `Endpoint` model under the existing `api` kind (method, path, operationId, summary/description, deprecated flag, tags, request parameters/body, responses), owned by the `atlas.apis` plugin. Endpoints are plugin-owned child data, not a registered Entity Kind — no top-level `/catalog/entities/endpoint/...` route.
- Add an Endpoint documentation UI: an API's detail page gains an "Endpoints" list, and each endpoint gets its own page (`/apis/:apiId/endpoints/:endpointId`) with Overview / Request / Response / Linked services tabs, mirroring existing entity-detail-page conventions.
- Add a `ServiceEndpointUsage` link (Service ↔ Endpoint), owned by `atlas.apis`, with its own create/delete API (`POST`/`DELETE /api/endpoints/{endpointId}/services`) — a plugin-owned relation, not routed through the core derived-relations system.
- Linking a Service to an Endpoint auto-creates the corresponding `consumesAPI` on that Service if it doesn't already exist (via the existing generic Component spec-PATCH path); unlinking an endpoint does **not** remove `consumesAPI`.
- Add a compact "Services using this endpoint" graph on the Endpoint Overview tab (React Flow, read-only, endpoint-center/service-ring layout, pan/zoom/fit-view, click-through to Service), plus a Linked Services management tab (search, team filter, sort, link/unlink) reusing the same consumer data.
- Endpoints are read-only in this change (documentation entered via Django admin/fixtures, no self-service create/edit UI); only Service↔Endpoint linking is interactive. Removing an endpoint is soft (`status=removed`) — existing links are preserved and surfaced with a warning, never silently discarded.
- Add `endpoint.read`, `endpointDependency.read`/`.create`/`.delete` permissions gating documentation reads and link/unlink actions.

Out of scope for this change (deferred, see design.md Non-Goals): OpenAPI import/sync, a full-screen multi-endpoint graph explorer beyond the compact Overview graph, impact-analysis reports, "unused endpoints" / "most consumed endpoints" views, and runtime-discovered dependencies.

## Capabilities

### New Capabilities
- `api-endpoints`: the `Endpoint` sub-resource of `API` — data model, CRUD, and documentation UI (Overview/Request/Response tabs), independent of who consumes it.
- `endpoint-service-dependencies`: the `Service consumesEndpoint Endpoint` link — its CRUD API, the auto-`consumesAPI` behavior, the compact consumers graph, and the Linked Services management tab.

### Modified Capabilities
(none — `apis-plugin`'s existing requirements, `entity-relations`'s derivation rules, and `standard-catalog-plugin`'s `consumesApis` field are all reused unchanged, not altered)

## Impact

- **Backend**: `plugins/apis/backend/atlas_plugin_apis/` gains `models/endpoint.py` (`ApiEndpoint`, including a `status` field for soft-delete), a `ServiceEndpointUsage` model, new migrations, read-only views/routes under `/api/apis/{apiId}/endpoints/` and `/api/endpoints/{endpointId}/...` for linking, and a call into a new narrow extension-point function on the standard-catalog side (`add_consumed_api`) for the auto-`consumesAPI` behavior. `plugins/standard-catalog/backend/atlas_plugin_standard_catalog/` gains that extension-point function.
- **Frontend**: `plugins/apis/frontend/` gains endpoint pages/components under the existing `pages`/`components`/`entityDetailTabs` layout, new routes/nav entries, and a new dependency (React Flow) not currently in that plugin's `package.json`, and not currently used anywhere else in this codebase (see design.md Decision 5 and its Risks).
- **Permissions**: new permission strings registered by `atlas.apis`; no change to existing ones.
- **No breaking changes**: existing `API`, `Component`, and `consumesApis` behavior is unchanged; this is purely additive.
