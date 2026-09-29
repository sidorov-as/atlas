## 1. Scaffold and dependency

- [x] 1.1 Create `plugins/apis/backend/` and `plugins/apis/frontend/` with empty descriptors declaring a manifest dependency on `atlas.standard-catalog`.
- [x] 1.2 Add manifest-dependency validation to the composition validator (missing required dependency fails composition); test against a synthetic missing-dependency fixture.

## 2. Decouple Component's API references

- [x] 2.1 Retarget `Component.providesApis`/`consumesApis` from `API` to `CatalogEntity` in one migration (no backfill — see design.md Non-Goals). (Already done by `introduce-catalog-entity-identity`'s migration `0012_catalog_entity_identity` — verified the M2M already targets `catalog.catalogentity`.)
- [x] 2.2 Add the kind-restriction validator (`kind='api'`) on the retargeted columns, owned by Standard Catalog. (Already in place: `ComponentSpecIn`/`Patch`'s `_ref_list_validator('api')`, owned by `atlas_plugin_standard_catalog/api/schemas.py`.)

## 3. Move API

- [x] 3.1 Move `ApiDetails`/`ApiKindHandler` and spec-source/spec-URL resolution logic into `plugins/apis/backend/`.
- [x] 3.2 Move API's frontend contributions (list/detail/form pages, Specification tab) into `plugins/apis/frontend/`.
- [x] 3.3 Verify `api-spec-documents` scenarios and API's `catalog-web-ui` scenarios against the moved code; verify Component's Provides/Consumes rail links.

## 4. Clean up

- [x] 4.1 Confirm `server.apps.catalog`/Standard Catalog no longer imports anything from `atlas_plugin_apis`.

## 5. Verify optionality

- [x] 5.1 Compose a distribution without `atlas.apis` selected; verify composition succeeds and Component's API reference fields are inert.
- [x] 5.2 Run the full backend + frontend test suite with `atlas.apis` selected (default) and confirm no regression.
