## 1. Backend data model

- [x] 1.1 Add `ApiEndpoint` model to `plugins/apis/backend/atlas_plugin_apis/models/` (FK to `ApiDetails.entity`, `method`, `path`, `operation_id`, `summary`, `description`, `deprecated`, `tags`, `request` JSON, `responses` JSON, `status` (`active` | `removed`, default `active`), timestamps; `unique_together(api, method, path)`; own UUID primary key)
- [x] 1.2 Add `ServiceEndpointUsage` model (FK to `ApiEndpoint`, FK to consuming Service's `CatalogEntity`, `created_at`, `created_by`, `unique_together(endpoint, service)`); note `ApiEndpoint`'s `on_delete` behavior here is moot for removal — removing an endpoint is a `status` update (task 1.4), never a row delete, so this FK is never actually exercised by the removal path
- [x] 1.3 Generate and review Django migrations for both models (additive only, per design.md Migration Plan)
- [x] 1.4 Register both models in `plugins/apis/backend/atlas_plugin_apis/models/__init__.py` and Django admin: `ApiEndpoint` admin allows creating/editing endpoint documentation (the only authoring surface in this change, per design.md Decision 7) and exposes a "Mark as removed" admin action that sets `status='removed'`; disable the default hard-delete admin action for `ApiEndpoint` so removal only happens through that action

## 2. Backend API — endpoint documentation (read-only)

- [x] 2.1 Add Pydantic schemas for `Endpoint` read shapes (request/response/parameter/schema/example types) to `atlas_plugin_apis/api/schemas.py` — no create/update schema, per design.md Decision 7
- [x] 2.2 Add `GET /api/apis/{apiId}/endpoints` (list with `method`/`tag`/`search`/`deprecated` filters; defaults to `status=active`, with a `status`/`include_removed` param to surface removed endpoints separately)
- [x] 2.3 Add `GET /api/apis/{apiId}/endpoints/{endpointId}` (works for both `active` and `removed` endpoints, so a removed endpoint's page and its warning banner are still reachable)
- [x] 2.4 Enforce `(api, method, path)` uniqueness as a model-level constraint (exercised by the admin, not a create API)
- [x] 2.5 Register the `endpoint.read` permission and gate the two `GET` views on it

## 3. Backend API — service/endpoint dependency

- [x] 3.1 Add `GET /api/endpoints/{endpointId}/services` (paginated, `search`/`team_id`/`sort`/`order`/`page`/`page_size`, default sort by service display name ascending)
- [x] 3.2 Add `POST /api/endpoints/{endpointId}/services` — creates `ServiceEndpointUsage`, rejects duplicates, returns `apiRelationCreated`
- [x] 3.3 Add `DELETE /api/endpoints/{endpointId}/services/{serviceId}` — removes the link only, `consumesAPI` untouched
- [x] 3.4 Add `GET /api/endpoints/{endpointId}/consumers` — the compact graph-data contract (endpoint summary + service list with team)
- [x] 3.5 Register `endpointDependency.read`/`.create`/`.delete` permissions and gate the above views

## 4. Cross-plugin consumesAPI wiring

- [x] 4.1 Add `add_consumed_api(component_entity, api_entity)` to `plugins/standard-catalog/backend/atlas_plugin_standard_catalog/extension_points.py` (new or extended module, mirroring `atlas_plugin_apis.extension_points`'s existing shape): performs `component.component_details.consumes_apis.add(api_entity)`, then calls `atlas_plugin_api.relations.recompute_relations` for that Component
- [x] 4.2 Call `add_consumed_api` from `atlas_plugin_apis`'s link-service view when the Service doesn't already `consumesAPI` the endpoint's API — no direct import of `atlas_plugin_standard_catalog` models from `atlas_plugin_apis`
- [x] 4.3 Wrap `ServiceEndpointUsage` creation and the `add_consumed_api` call in one transaction; a failure in the latter rolls back the link
- [x] 4.4 Verify `recompute_relations` fires and `GET /api/apis/{apiId}/relations/` reflects the new `apiConsumedBy` immediately after an auto-created `consumesAPI`
- [x] 4.5 Verify `add_consumed_api` is idempotent under concurrent calls (two near-simultaneous links from the same Service to different Endpoints of the same API) — the M2M `.add()` should make this safe by construction; add a regression test rather than just asserting it

## 5. Frontend — endpoint documentation

- [x] 5.1 Add `Endpoint` types/API client to `plugins/apis/frontend/src/` following existing `entities`/`lib` conventions
- [x] 5.2 Add endpoint list to `ApiDetailPage.tsx` (search, method filter, deprecated filter; defaults to active endpoints)
- [x] 5.3 Add a "Removed endpoints" section/filter on the API's endpoint list, separate from the default active list
- [x] 5.4 Add `EndpointDetailPage` with route `/apis/:apiId/endpoints/:endpointId`, header (breadcrumbs, method badge, path, deprecated indicator), and Overview / Request / Response / Linked services tabs, with `?tab=`/search/filter/sort state kept in the URL
- [x] 5.5 Add a removed-endpoint warning banner on `EndpointDetailPage`, shown when `status=removed`, naming how many Services still have a `ServiceEndpointUsage` link to it
- [x] 5.6 Build Overview tab: documentation card, Details card, path/query/header parameter tables (omitted when empty), compact responses table
- [x] 5.7 Build Request tab: parameters, request body schema/example (schema viewer supporting object/array/string/integer/number/boolean/enum/nullable/$ref, expandable/collapsible nested objects)
- [x] 5.8 Build Response tab: status selector defaulting to first 2xx (else first response), content type, schema, example, with copy action
- [x] 5.9 Add loading skeletons (not a full-page spinner) and an endpoint-not-found state distinct from a documentation-load failure
- [x] 5.10 There is no endpoint create/edit UI in this change (documentation is admin-authored, design.md Decision 7) — do not build one; confirm this scope with the reviewer if tempted to add it

## 6. Frontend — linked services and consumers graph

- [x] 6.1 Confirm React Flow's current canonical npm package name and a concrete version (do not assume `reactflow` vs. `@xyflow/react` — design.md Decision 5 explicitly leaves this unpinned), then add it to `plugins/apis/frontend/package.json`
- [x] 6.2 Build `ServiceNode`/`EndpointNode` custom node components registered via React Flow's `nodeTypes` map, matching existing Gravity UI card visual language
- [x] 6.3 Implement the compact-graph fixed radial layout (endpoint center, service ring; cap at 12 nodes + "N more" indicator beyond that, per design.md Decision 5) — compute each node's `position` directly, no layout library needed
- [x] 6.4 Wire graph settings for read-only interaction: pan/zoom/fitView enabled (React Flow defaults + `Controls`), `nodesDraggable={false}`, `nodesConnectable={false}`, `elementsSelectable={true}`, node click navigates to the Service (Endpoint node click is a no-op)
- [x] 6.5 Add empty-graph state ("No services are linked to this endpoint yet" + Link service action) and an isolated inline error+retry state that doesn't block the rest of the page
- [x] 6.6 Build Linked Services tab: search box, team filter, sort (service/team, asc/desc), table (Service/Team/Actions columns for MVP), preview of up to 5 on Overview with "View all N services" link to the full tab
- [x] 6.7 Show the removed-endpoint warning (task 5.5's banner content, or an equivalent inline note) at the top of the Linked Services tab and the consumers graph when the endpoint is `removed`
- [x] 6.8 Build Link Service dialog: service search/select (already-linked services shown disabled with an "Already linked" marker), team display, informational message when linking will also create `consumesAPI`; the Link Service action itself is not offered at all on a `removed` endpoint's page (task 5.4/5.5)
- [x] 6.9 Build Unlink confirmation dialog
- [x] 6.10 Gate Link/Unlink actions behind `endpointDependency.create`/`.delete`, hidden (not disabled) without permission
- [x] 6.11 After link/unlink, refresh table, graph, and tab counter without a full page reload

## 7. Navigation and routing

- [x] 7.1 Register the new endpoint routes in `plugins/apis/frontend/src/routes.ts`
- [x] 7.2 Verify breadcrumbs (`APIs > {API name} > {method} {path}`) and the API-entity/version chip link back correctly

## 8. Tests

- [x] 8.1 Backend: endpoint read/list/uniqueness constraint, default excludes `removed`, permission gating (per `specs/api-endpoints/spec.md` scenarios)
- [x] 8.2 Backend: soft-delete via the admin "Mark as removed" action preserves `ServiceEndpointUsage` rows and never hard-deletes the `ApiEndpoint` row (per `specs/api-endpoints/spec.md`'s removal scenarios)
- [x] 8.3 Backend: link/unlink CRUD, duplicate-link rejection, auto-`consumesAPI` creation and non-duplication via `add_consumed_api`, unlink not removing `consumesAPI`, search/filter/sort/pagination (per `specs/endpoint-service-dependencies/spec.md` scenarios)
- [x] 8.4 Backend: linking is rejected (or the action is simply unavailable — match whatever 6.8 implements) when targeting a `removed` endpoint
- [x] 8.5 Frontend: Endpoint page tab rendering, empty-section omission, deprecated indicator, Response tab default-selection logic, removed-endpoint warning banner
- [x] 8.6 Frontend: Linked Services search/filter/sort/URL-state, Link/Unlink dialogs, permission-based hiding of actions, removed-endpoint warning and absent Link action
- [x] 8.7 Frontend: consumers graph — edge direction, node click navigation, no drag/connect/delete, empty state, >12-node cap, isolated error/retry

## 9. Demo data (optional but recommended for reviewability)

- [x] 9.1 Resolve design.md Open Question on seed data; if in scope, extend `seed_booking_demo.py` with sample endpoints and `ServiceEndpointUsage` links for at least one API with multiple consumers
