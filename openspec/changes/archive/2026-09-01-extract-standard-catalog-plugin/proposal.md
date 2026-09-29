## Why

Changes 1-4 built the identity model, Entity Service, backend/frontend registries, and shell — but `System`, `Component`, `Resource`, `Group`/Team, and `Actor` still live inside `server.apps.catalog` and their contributions still live inside the single in-tree "core" frontend module from `introduce-frontend-extension-points`. `plugin-architecture.md` requires Atlas Core to contain *no* concrete Entity Kinds; System/Component/Resource/Team (and, per this program's own resolution of a gap the source document left open, Actor) belong to a required "Standard Catalog" plugin instead (ADR 0004, ADR 0024). This is the first real test of the boundary: if these five kinds can't be cleanly moved out of core using only the contracts already built, the contracts are wrong and need revisiting before APIs/C4/Ingestion repeat the same move.

## What Changes

- Create `plugins/standard-catalog/` (backend Django app `atlas_plugin_standard_catalog` + frontend workspace package `@atlas/plugin-standard-catalog`), still inside the monorepo, but built and selected as an independent plugin via the mechanisms from changes 3 and 4.
- Move `SystemKindHandler`/`ComponentKindHandler`/`ResourceKindHandler`/`GroupKindHandler`/`ActorKindHandler` (Group's and Actor's handlers didn't exist as such before — add them, formalizing Team and Actor as registered Entity Kinds rather than Django-admin-managed side models) and their `*Details` models into the new backend package.
- Move the corresponding frontend contributions (routes, nav items, entity-detail tabs for System/Component/Resource/Team) out of the "core" plugin module and into `@atlas/plugin-standard-catalog`. Actor gets no frontend contributions of its own in this change — it keeps today's product scope (no list/detail page, admin-managed only) even though it's now a fully registered kind.
- Mark `atlas.standard-catalog` as **required** in `SELECTED_PLUGINS` (the official distribution cannot omit it) — this is a deployment-manifest concept that doesn't fully exist until `introduce-plugin-distribution-and-composer`, so for now it's enforced by the composition validator failing if it's absent from the selection list.
- Confirm nothing remaining in `server.apps.catalog`/the frontend "core" module imports anything standard-catalog-specific — `apps/catalog` shrinks to genuinely kind-agnostic code (the Entity Service, registries) or is deleted if empty.
- **BREAKING (internal)**: package/import paths for System/Component/Resource/Group code move; no REST route, response shape, or UI behavior changes.

## Capabilities

### New Capabilities
- `standard-catalog-plugin`: System, Component, Resource, Team, and Actor are provided by one required first-party plugin with no special core privileges beyond what any other plugin has access to.

### Modified Capabilities
- None — `entity-catalog`, `entity-identity`, `entity-relations`, `catalog-web-ui`, `catalog-auth` behavior is unchanged; this is a pure code-location/packaging change validated by the existing spec-scenario suites continuing to pass unmodified.

## Impact

- **Backend**: new `plugins/standard-catalog/backend/` package; `server.apps.catalog` shrinks or is removed; `SELECTED_PLUGINS` gains `atlas.standard-catalog` as required.
- **Frontend**: new `plugins/standard-catalog/frontend/` workspace package; `frontend/src/plugins/core/` shrinks to whatever, if anything, remains genuinely core (likely nothing plugin-shaped — Login/Settings pages may stay core-owned, TBD in design).
- **Proves**: that `introduce-entity-kind-registry-and-service`'s handler protocol and `introduce-frontend-extension-points`'s contribution contract are sufficient for a real kind extraction with zero core changes required beyond marking the plugin required.
- **Dependents**: `extract-apis-plugin` and `extract-c4-plugin` both declare a manifest dependency on `atlas.standard-catalog` (API's `system`/`owner` fields and C4's diagrams reference System/Component/Resource/Team entities).
