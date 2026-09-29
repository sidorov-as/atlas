## Why

`API` is currently a concrete kind inside `server.apps.catalog` alongside System/Component/Resource, with its own spec-source/spec-URL resolution logic (`api-spec-documents` spec) and its own list/detail/form pages. `docs/plugin-architecture.md` singles out APIs as the second proof point after Standard Catalog specifically because it's an *optional* Entity Kind with specialized schemas, its own routes, and its own views — the first case where a plugin depends on another plugin (Standard Catalog, for `Component.providesApis`/`consumesApis` and `System`) via a manifest dependency rather than shared core code (proving ADR 0004's "optional kind" claim and exercising manifest dependencies for the first time with two real plugins).

## What Changes

- Create `plugins/apis/` (backend `atlas_plugin_apis` + frontend `@atlas/plugin-apis`), declaring a manifest dependency on `atlas.standard-catalog` version-ranged as `plugin-architecture.md:260` illustrates.
- Move `ApiDetails`+`ApiKindHandler` (including the spec-source/spec-URL resolution behavior) and the API list/detail/form pages + Specification tab contribution into the new plugin.
- `Component.providesApis`/`consumesApis` (owned by Standard Catalog) become a capability-mediated relationship rather than a direct FK to an API-plugin model: Standard Catalog exposes `apis: EntityId[]`-shaped fields validated generically (any `CatalogEntity` reference, kind-checked at the application layer against whichever kind declares an "API provider" capability) instead of importing `ApiDetails`.
- Add specialized backend routes under `/api/plugins/atlas.apis/...` for anything API-specific that isn't generic entity CRUD (spec-URL refresh trigger, if it needs an explicit endpoint beyond the periodic ingestor-poll loop already described in `api-spec-documents`).
- Mark `atlas.apis` as **optional** — the composition validator must allow a distribution to omit it, and `Component`'s `providesApis`/`consumesApis` fields must degrade gracefully (empty/no-op) when absent, proving optionality for the first time.

## Capabilities

### New Capabilities
- `apis-plugin`: API is provided by an optional plugin with its own storage, spec-source resolution, and UI, installable or omittable independent of Standard Catalog's own kinds.

### Modified Capabilities
- `entity-catalog`: the "Component, Resource, and API CRUD" requirement's reference-field validation for `providesApis`/`consumesApis` now validates against whatever plugin currently provides API-shaped entities, resolved generically, rather than a hard-coded `API` model import — behaviorally the same validation (dangling references still rejected) but the mechanism is now capability-mediated and the fields become inert (empty, no validation error) when `atlas.apis` is not installed rather than a hard schema requirement.

## Impact

- **Backend**: new `plugins/apis/backend/`; `Component`'s `providesApis`/`consumesApis` M2M validation moves from a direct model import to a generic `CatalogEntity`-reference check; `api-spec-documents` behavior (spec source, periodic refresh, stale indicator) moves into the plugin unchanged.
- **Frontend**: new `plugins/apis/frontend/`; API list/detail/form pages and the Specification tab move; Component's Provides/Consumes API rail links (`catalog-web-ui`) keep working via generic entity-reference resolution.
- **First real manifest dependency**: `atlas.apis` requiring `atlas.standard-catalog` is the first case (per `plugin-architecture.md`'s dependency rules) where composition must fail if the required plugin is missing, distinct from the `atlas.standard-catalog` special-cased "always required" rule from change 5.
- **Dependents**: `extract-c4-plugin` targets APIs' entity capability rather than importing `ApiDetails` directly, proving the capability-targeting pattern a second time; `introduce-plugin-lifecycle-and-failure-isolation`'s Unavailable Entity behavior is first exercised by removing `atlas.apis` and confirming API entities degrade to read-only Unavailable Entities rather than disappearing.
