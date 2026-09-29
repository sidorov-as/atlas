## 1. Backend data model

- [x] 1.1 Add `ApiOperation` model to `plugins/apis/backend/atlas_plugin_apis/models/` (FK to `ApiDetails.entity`, `channel_address`, `channel_protocol`, `direction` (`send` | `receive`), `operation_key`, `operation_id`, `summary`, `description`, `tags`, `message` JSON, `status` (`active` | `removed`, default `active`), timestamps; `unique_together(api, operation_key)`; own UUID primary key) — no `deprecated` field (design.md Open Questions: no native AsyncAPI equivalent)
- [x] 1.2 Add `ServiceOperationUsage` model (FK to `ApiOperation`, FK to linked Service's `CatalogEntity`, `role` (`publisher` | `subscriber`), `created_at`, `created_by`, `unique_together(operation, service, role)`); enforce at the model/view layer that the linked Service is never the Operation's own `apiProvidedBy` Service (design.md Decision 5)
- [x] 1.3 Generate and review Django migrations for both models (additive only, per design.md Migration Plan)
- [x] 1.4 Register both models in `plugins/apis/backend/atlas_plugin_apis/models/__init__.py` and Django admin: `ApiOperation` admin allows creating/editing operation documentation (the only authoring surface in this change, per design.md Decision 9) and exposes a "Mark as removed" admin action that sets `status='removed'`; disable the default hard-delete admin action for `ApiOperation` so removal only happens through that action. The "Mark as removed" action MUST go through Django admin's standard `log_change`/`LogEntry` recording so who removed an operation and when is recoverable (design.md Decision 9's audit trail note)

## 2. Backend API — operation documentation (read-only)

- [x] 2.1 Add Pydantic schemas for `Operation` read shapes (channel/direction/message types) to `atlas_plugin_apis/api/schemas.py` — no create/update schema, per design.md Decision 9
- [x] 2.2 Add `GET /api/apis/{apiId}/operations` (list with `direction`/`tag`/`search` filters, grouped-by-`channel_address` response shape or a flat list the frontend groups client-side — pick whichever the frontend task (5.2) actually needs; defaults to `status=active`, with a `status`/`include_removed` param to surface removed operations separately)
- [x] 2.3 Add `GET /api/apis/{apiId}/operations/{operationId}` (works for both `active` and `removed` operations, so a removed operation's page and its warning banner are still reachable); response includes the document-owner's implied role (derived from `direction` + `apiProvidedBy`, not stored)
- [x] 2.4 Enforce `(api, operation_key)` uniqueness as a model-level constraint (exercised by the admin, not a create API)
- [x] 2.5 Register the `operation.read` permission and gate the two `GET` views on it

## 3. Backend API — service/operation dependency

- [x] 3.1 Add `GET /api/operations/{operationId}/services` (paginated, `search`/`team_id`/`role`/`sort`/`order`/`page`/`page_size`, default sort by service display name ascending)
- [x] 3.2 Add `POST /api/operations/{operationId}/services` — body includes `serviceId` and `role`; creates `ServiceOperationUsage`, rejects duplicates (same operation+service+role), rejects linking the Operation's own `apiProvidedBy` Service (design.md Decision 5, spec's "document owner is never self-linked")
- [x] 3.3 Add `DELETE /api/operations/{operationId}/services/{serviceId}?role=publisher|subscriber` — `role` is a required query parameter (resolved per design.md Decision 5: a Service can hold both roles on one Operation, so the delete must target exactly one `(operation, service, role)` row, never all of a service's roles at once)
- [x] 3.4 Add `GET /api/operations/{operationId}/consumers` — resolves the operation, then queries **by its `channel_address`** across all `ApiOperation` rows sharing it (design.md Decision 7), returning every aggregated Operation's linked Services plus each one's document-owner implied role, not just the current operation's own direct links. Visibility filter intentionally **not implemented**: verified no per-entity visibility mechanism exists anywhere in the catalog (`catalog-auth` spec makes unrestricted read for any authenticated user an explicit requirement) — see design.md Decision 7's "Verified during implementation" note; user decision 2026-09-06 to ship without it.
- [x] 3.5 Register `operationDependency.read`/`.create`/`.delete` permissions and gate the above views (no evaluator change needed — design.md Decision 10 confirms `RBACPolicyEvaluator` already grants `.create`/`.delete` to any authenticated principal for `resource=None`)

## 4. Frontend — operation documentation

- [x] 4.1 Add `Operation` types/API client to `plugins/apis/frontend/src/` following existing `entities`/`lib` conventions
- [x] 4.2 Add operation list to `ApiDetailPage.tsx`, **grouped into sections by `channel_address`** (design.md Decision 6) — each section header shows a publisher/subscriber count summary; search and direction filter; defaults to active operations
- [x] 4.3 Add a "Removed operations" section/filter on the API's operation list, separate from the default active/grouped list
- [x] 4.4 Add `OperationDetailPage` with route `/apis/:apiId/operations/:operationId`, header (breadcrumbs, direction badge reading "Send"/"Receive", channel address/protocol), and Overview / Message / Linked services tabs, with `?tab=`/search/filter/sort state kept in the URL
- [x] 4.5 Add a removed-operation warning banner on `OperationDetailPage`, shown when `status=removed`, naming how many Services still have a `ServiceOperationUsage` link to it
- [x] 4.6 Build Overview tab: documentation card, channel details card (address, protocol, direction), the document-owner's implied role (publisher/subscriber label, distinct vocabulary from Send/Receive per design.md Decision 8), compact message summary
- [x] 4.7 Build Message tab: message selector (when more than one shape), schema/example viewer reusing `EndpointSchemaViewer`'s object/array/string/integer/number/boolean/enum/nullable/$ref support where applicable
- [x] 4.8 Add loading skeletons (not a full-page spinner) and an operation-not-found state distinct from a documentation-load failure
- [x] 4.9 There is no operation create/edit UI in this change (documentation is admin-authored, design.md Decision 9) — do not build one; confirm this scope with the reviewer if tempted to add it

## 5. Frontend — linked services and publishers/subscribers graph

- [x] 5.1 Build `PublisherNode`/`SubscriberNode` (or a single `ServiceRoleNode` parameterized by role) custom node components registered via React Flow's `nodeTypes` map, matching existing Gravity UI card visual language and `EndpointConsumerNodes.tsx`'s conventions; publisher/subscriber distinguished by label, not color alone (specs/operation-service-dependencies/spec.md)
- [x] 5.2 Implement the compact-graph fixed layout aggregated by `channel_address` (design.md Decision 7) — decide and document the layout shape (e.g. two rings: publishers on one side, subscribers on the other, or a single ring split by role) since this is genuinely different from `EndpointConsumersGraph.tsx`'s single-center-node shape; cap at 12 nodes + "N more" indicator
- [x] 5.3 Wire graph settings for read-only interaction: pan/zoom/fitView enabled, `nodesDraggable={false}`, `nodesConnectable={false}`, `elementsSelectable={true}`, node click navigates to the Service
- [x] 5.4 Add empty-graph state ("No services are linked to this channel yet" + Link service action) and an isolated inline error+retry state that doesn't block the rest of the page
- [x] 5.5 Build Linked Services tab: search box, team filter, role filter, sort (service/team, asc/desc), table (Service/Role/Team/Actions columns for MVP), preview on Overview with "View all N services" link to the full tab
- [x] 5.6 Show the removed-operation warning (task 4.5's banner content, or an equivalent inline note) at the top of the Linked Services tab when the operation is `removed`
- [x] 5.7 Build Link Service dialog: service search/select (the operation's own `apiProvidedBy` Service excluded from the picker per design.md Decision 5; already-linked service+role pairs shown disabled with an "Already linked" marker), role picker (`publisher`/`subscriber`); the Link Service action itself is not offered at all on a `removed` operation's page
- [x] 5.8 Build Unlink confirmation dialog
- [x] 5.9 Gate Link/Unlink actions behind `operationDependency.create`/`.delete`, hidden (not disabled) without permission
- [x] 5.10 After link/unlink, refresh table, graph, and channel-group counts (task 4.2's summary) without a full page reload

## 6. Navigation and routing

- [x] 6.1 Register the new operation routes in `plugins/apis/frontend/src/routes.ts`
- [x] 6.2 Verify breadcrumbs (`APIs > {API name} > {channel address}`) and the API-entity link back correctly

## 7. Tests

- [x] 7.1 Backend: operation read/list/uniqueness constraint (`operation_key`), default excludes `removed`, permission gating (per `specs/api-operations/spec.md` scenarios)
- [x] 7.2 Backend: direction values are stored as `send`/`receive` only — no code path can write `publish`/`subscribe` literally (guards against reintroducing design.md Decision 3's confusion)
- [x] 7.3 Backend: soft-delete via the admin "Mark as removed" action preserves `ServiceOperationUsage` rows and never hard-deletes the `ApiOperation` row
- [x] 7.4 Backend: link/unlink CRUD, duplicate-link rejection (same operation+service+role), multiple-services-same-role allowed, self-link-of-document-owner rejection, search/filter/sort/pagination (per `specs/operation-service-dependencies/spec.md` scenarios)
- [x] 7.5 Backend: `GET /api/operations/{operationId}/consumers` aggregates across every `ApiOperation` sharing the operation's `channel_address`, including operations belonging to a different `API` entity
- [x] 7.5a N/A — no restricted-visibility `API` concept exists in this catalog (verified task 3.4, design.md Decision 7's "Verified during implementation" note); nothing to test here unless a future change introduces per-entity visibility
- [x] 7.5b Backend: unlinking via `DELETE /api/operations/{operationId}/services/{serviceId}?role=...` removes only the targeted `(operation, service, role)` row, leaving the other role's row intact when a Service holds both
- [x] 7.6 Frontend: Operation page tab rendering, channel-grouped list rendering, direction badge text ("Send"/"Receive" only), removed-operation warning banner
- [x] 7.7 Frontend: Linked Services search/filter (including role)/sort/URL-state, Link/Unlink dialogs, permission-based hiding of actions, removed-operation warning and absent Link action
- [x] 7.8 Frontend: publishers/subscribers graph — cross-API aggregation by channel, role-label distinction, node click navigation, no drag/connect/delete, empty state, >12-node cap, isolated error/retry

## 8. Demo data (optional but recommended for reviewability)

- [x] 8.1 Extend `seed_booking_demo.py` with sample operations and `ServiceOperationUsage` links for at least one `asyncapi`-typed demo API, including one channel with operations from two different API documents (to exercise the channel-aggregated graph and grouped list) and at least one multi-subscriber-same-role case
