## Context

Today `Component.provides_apis`/`consumes_apis` (`backend/server/apps/catalog/models/component.py:28-29`) are `ManyToManyField(API, ...)` — a direct model import from Component to API. Once API moves to its own plugin, Standard Catalog cannot import `ApiDetails` (ADR 0006: plugins isolated behind capabilities, no cross-plugin model imports). This change has to solve that specific coupling, which is exactly the scenario `plugin-architecture.md`'s "Operation Impact" example (line 313, "does not read API tables or import API models") describes one level further out — here it's Standard Catalog owning the M2M field, not a third plugin consuming a capability.

## Goals / Non-Goals

**Goals:**
- `API` is fully removed from `server.apps.catalog`/Standard Catalog and lives only in `plugins/apis/`.
- `atlas.apis` declares a manifest dependency on `atlas.standard-catalog`, and composition fails if Standard Catalog is missing (it can't be, since it's required, but the dependency must still be declared and validated).
- `Component.providesApis`/`consumesApis` keep working exactly as today when `atlas.apis` is installed, and degrade to empty/inert when it is not.
- Every `api-spec-documents` and API-related `catalog-web-ui`/`entity-catalog` scenario keeps passing.

**Non-Goals:**
- Defining the general `EntityCapability` mechanism in full (declaring `provides=[...]` on every kind, `entitySupports()` gating in the registry) — that's formalized end-to-end in `extract-c4-plugin`, the first change that actually needs cross-kind capability matching for *view* contributions. This change only needs the narrower "does a reference field point at a kind that currently exists" check, which doesn't require the full capability-declaration surface.
- Building `/api/plugins/atlas.apis/spec-preview` or any other specialized endpoint beyond what `api-spec-documents` already requires — add one only if extraction reveals a genuine need.
- Preserving existing `providesApis`/`consumesApis` M2M rows across the schema change. This project has no production deployment yet (see `introduce-catalog-entity-identity/design.md`'s Non-Goals); the field retype ships against an empty database. If a production deployment exists by implementation time, this must be revisited as an expand/contract migration.

## Decisions

**`Component.providesApis`/`consumesApis` become `ManyToManyField('catalog.CatalogEntity', ...)`, validated at the application layer to reference `kind='api'` rows, rather than importing `ApiDetails`.** This is the direct application of `plugin-architecture.md`'s facet/relation rule ("Facets reference only core `CatalogEntity`... A plugin does not create FK on another plugin's table" — the same rule extends to any cross-plugin M2M). Alternative considered: a generic "entity reference field" type that isn't kind-restricted at all — rejected because Standard Catalog's UI (Component's Provides/Consumes API rail links) needs to know these are specifically API-shaped references to render sensibly, not arbitrary entities.

**The kind-restriction check ("is this referenced entity's kind actually `api`") is a Standard Catalog-owned validator, not something `atlas.apis` has to implement or that core enforces generically.** Standard Catalog already owns the `providesApis`/`consumesApis` fields; it's the natural owner of "these must point at API kind" the same way it already validates `dependsOn` targets exist. If `atlas.apis` isn't installed, no `CatalogEntity` will ever have `kind='api'`, so the fields degrade to "always empty, never validatable against a real API" — matching `plugin-architecture.md`'s Unavailable Entity story that reads/writes against an absent kind's data don't crash, they just find nothing.

**API's spec-source/spec-URL periodic refresh logic moves as-is into `ApiKindHandler`/the plugin's own background task, unchanged from its current implementation** (already an internal detail of `api-spec-documents`, not something core needs to know about) — this change is a relocation, not a rewrite of that logic. Its periodic run is scheduled via `django-apscheduler` (the program's chosen background-job runtime, formalized in `extract-ingestion-plugin`'s design), registered as a job the plugin owns and `introduce-plugin-lifecycle-and-failure-isolation` can pause when `atlas.apis` is disabled.

**Manifest dependency validation (`atlas.apis requires atlas.standard-catalog >=X <Y`) is added to the composition validator from `introduce-plugin-registries`**, which so far only checked duplicate ids — this is the first change that needs the "missing required dependency" half of that validator, previously a stub.

## Risks / Trade-offs

- [Changing `providesApis`/`consumesApis`'s target from `API` to `CatalogEntity` is a schema-shape change on an existing M2M table] → Retarget the M2M directly to `CatalogEntity` in one migration; no backfill needed (see Non-Goals).
- [If `atlas.apis` is ever deselected after entities of kind `api` already exist, Component's `providesApis` M2M rows become dangling references to now-providerless entities] → This is exactly the Unavailable Entity scenario `introduce-plugin-lifecycle-and-failure-isolation` formalizes; until that change lands, treat "deselecting `atlas.apis` with existing API entities" as unsupported and out of scope for this change's guarantees.
- [Two real independently-built plugins now exist, so CI import-boundary enforcement (Standard Catalog must not import `atlas_plugin_apis`, and vice versa except via the declared manifest dependency) needs to actually run, not just be planned] → Add the CI check now rather than waiting for `introduce-plugin-distribution-and-composer`'s full monorepo tooling, scoped to this pair, the same way `extract-standard-catalog-plugin` did for its own boundary.

## Migration Plan

1. Scaffold `plugins/apis/backend/` and `plugins/apis/frontend/`, declaring the manifest dependency on `atlas.standard-catalog`, contributing nothing yet.
2. Retarget `Component.providesApis`/`consumesApis` to `CatalogEntity` in one migration; add the kind-restriction validator (`kind='api'`).
3. Move `ApiDetails`/`ApiKindHandler`/spec-resolution logic and API's frontend contributions (list/detail/form, Specification tab) into the new plugin; verify `api-spec-documents` and API `catalog-web-ui` scenarios.
4. Delete `API` model/table remnants from `server.apps.catalog` if any remain (change 1's `*Details` split should have already isolated `ApiDetails`, so this should mostly be an import-path cleanup, not a new migration).
5. Add manifest-dependency validation to the composition validator; add a test asserting composition fails if `atlas.apis` is selected without `atlas.standard-catalog` (a synthetic/impossible-in-practice case, since Standard Catalog is required, but the validator must still enforce it generally for future optional-on-optional dependencies).

## Resolved

- **Capability vs. hard-coded kind check for `providesApis`/`consumesApis`**: `extract-c4-plugin` builds the general entity-capability mechanism this question was deferring to. Decision: keep the `kind='api'` check as-is for now rather than retrofitting a new `api.provider.v1` capability — `atlas.apis` remains the only plugin ever expected to provide API-shaped entities, so introducing a capability with exactly one declarer buys no real flexibility yet. Revisit only if a second plugin genuinely wants to appear in these fields; until then this is intentionally simpler than the capability-targeting pattern change 7 establishes elsewhere.
