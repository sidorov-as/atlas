## 1. Base entity type

- [x] 1.1 Publish a base entity type in `atlas_plugin_api` standing in for `server.apps.catalog.models.base.CatalogEntity`: a `Protocol` for static typing, a `get_catalog_entity_model()` runtime accessor via Django's app registry, and the FK string-reference idiom for `*Details` models (see design.md Decisions — `atlas_plugin_api` cannot import the concrete model, `core/backend` is `package-mode = false`).
- [x] 1.2 Migrate every plugin model currently subclassing `server.apps.catalog.models.base.CatalogEntity` (and importing `KIND_*`/`CatalogEntity` from `server.apps.catalog.models`) onto the published type.
- [x] 1.3 Remove `server.apps.catalog.models`/`server.apps.catalog.models.base` from `ALLOWED_CORE_SUBMODULES`; run the full backend suite.

## 2. Entity Kind registration

- [x] 2.1 Publish a `register_kind`/kind-handler-facing function and the `ValidateDeleteError` type in `atlas_plugin_api`, standing in for `server.apps.catalog.kinds.{registry,handler}`.
- [x] 2.2 Migrate every plugin's Entity Kind handler registration onto the published function/type.
- [x] 2.3 Remove `server.apps.catalog.kinds`/`kinds.handler`/`kinds.registry` from `ALLOWED_CORE_SUBMODULES`; run the full backend suite.

## 3. Entity service access

- [x] 3.1 Publish an entity read/write protocol in `atlas_plugin_api`, wrapping `server.apps.catalog.services.entity_service` without exposing the singleton directly.
- [x] 3.2 Migrate every plugin's `entity_service` usage onto the published protocol.
- [x] 3.3 Remove `server.apps.catalog.services`/`services.entity_service` from `ALLOWED_CORE_SUBMODULES`; run the full backend suite.

## 4. Auth and permission registration

- [x] 4.1 Publish a permission-registration function in `atlas_plugin_api`/`@atlas/plugin-api`, standing in for `server.apps.plugins.permissions.registry` and `server.apps.catalog.authorization.policy_evaluator`.
- [x] 4.2 Migrate `atlas_plugin_c4`'s permission registration and any plugin using `policy_evaluator` onto the published function.
- [x] 4.3 Remove `server.apps.plugins.permissions` and `server.apps.catalog.authorization` from `ALLOWED_CORE_SUBMODULES`; run the full backend suite.

## 5. Remaining Core surface (refs, relations, api helpers)

- [x] 5.1 Audit every plugin's remaining `server.apps.catalog.{refs,relations,api.auth,api.filters,api.helpers,api.schemas,models.relation,models.architecture_relationship,models.audit,models.tag,models.external_identity,models.flow}` import (the last six are `server.apps.catalog.models` submodules outside task 1's base-entity/KIND_* scope, e.g. `Relation`/`ArchitectureRelationship`/`EntityAuditRecord`/`Tag`) and publish the matching re-export or thin wrapping type in `atlas_plugin_api` for each one actually used.
- [x] 5.2 Migrate every plugin onto the published equivalents.
- [x] 5.3 Remove `server.apps.catalog.refs`/`relations`/`api.*` from `ALLOWED_CORE_SUBMODULES`; confirm it's empty (or document any remaining entry with rationale if extraction genuinely isn't warranted for it); run the full backend suite.

## 6. Plugin contract packages — pure type/schema edges

- [x] 6.1 Publish `atlas_plugin_standard_catalog`'s declared contract-only package (types/schemas only, no Django models) covering the surface `ingestion`/`apis`/`c4`/`database-schema` need from it.
- [x] 6.2 Publish `atlas_plugin_apis`'s declared contract-only package covering `ApiIn`/`ApiSpecPatch` and any other type `ingestion` needs.
- [x] 6.3 Migrate `ingestion`'s and `apis`'s pure type/schema imports (`atlas_plugin_apis.api.schemas.*`, `atlas_plugin_standard_catalog.api.schemas.*`) onto the two contract packages.
- [x] 6.4 Remove the migrated entries from `ALLOWED_PLUGIN_TO_PLUGIN_EDGES`; run the full backend suite.

## 7. ORM cross-plugin edges

- [x] 7.1 Add `atlas_plugin_apis`'s contract-package function for ingestion's periodic spec-refresh job (e.g. `due_for_spec_refresh()`), keeping the `ApiDetails` ORM query inside `atlas_plugin_apis`.
- [x] 7.2 Migrate `atlas_plugin_ingestion.pipeline`'s periodic job onto the new function; remove its `atlas_plugin_apis.models`/`atlas_plugin_apis.spec_fetch` imports.
- [x] 7.3 Restructure `atlas_plugin_apis`'s `validate_delete` check (currently querying `atlas_plugin_standard_catalog.models.ComponentDetails` directly) as an extension point `atlas_plugin_standard_catalog` registers against, reusing the existing `EntityKindHandler.validate_delete`-style mechanism.
- [x] 7.4 Remove `atlas_plugin_apis`'s `atlas_plugin_standard_catalog` import entirely; confirm `atlas_plugin_ingestion` → `atlas_plugin_apis`/`atlas_plugin_standard_catalog` and `atlas_plugin_apis` → `atlas_plugin_standard_catalog` are gone from `ALLOWED_PLUGIN_TO_PLUGIN_EDGES`; run the full backend suite.

## 8. Verification and cleanup

- [x] 8.1 Confirm `ALLOWED_PLUGIN_TO_PLUGIN_EDGES` contains only the two documented test-only fixture edges (`atlas_plugin_c4`, `atlas_plugin_database_schema` → `atlas_plugin_standard_catalog.models` in `tests/conftest.py`); update their inline rationale to reflect this design's decision to leave them as-is. **Found**: `atlas_plugin_c4` no longer imports `atlas_plugin_standard_catalog` at all (only a stale docstring comment referenced it) — that edge was removed rather than documented, leaving `('database-schema', 'atlas_plugin_standard_catalog')` as the sole remaining entry (real import in `tests/test_views.py`, not `conftest.py`).
- [x] 8.2 Confirm `ALLOWED_CORE_SUBMODULES` is empty (or every remaining entry carries an explicit rationale for why extraction isn't warranted).
- [x] 8.3 Run the full backend and frontend spec-scenario test suites end-to-end; confirm no behavior change.
- [x] 8.4 Rebuild `distributions/default/`'s lock file and regenerate `SELECTED_PLUGINS`/`installedFrontendPlugins` via the composer; confirm the rebuilt default distribution still passes the full suite.
