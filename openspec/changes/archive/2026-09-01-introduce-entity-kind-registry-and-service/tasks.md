## 1. Protocol and registry

- [x] 1.1 Define `EntityKindHandler` Protocol (`kind_id`, `spec_schema`, `create_details`, `update_details`, `serialize_details`, `validate_delete`).
- [x] 1.2 Implement `EntityKindRegistry` with `register`/`resolve`, rejecting duplicate `kind_id` registration and returning a typed not-found result for unknown kinds.
- [x] 1.3 Add the audit record model (`entity_id`, `kind`, `action`, `actor`, `timestamp`, `diff`) and its migration.

## 2. Entity Service

- [x] 2.1 Implement `EntityService.create/update/delete` owning the transaction: authorize → validate common metadata → resolve handler → mutate `CatalogEntity` → invoke handler → write audit → commit.
- [x] 2.2 Move common-metadata validation (name/title/description/labels/tags/links) out of per-kind serializers and into the Entity Service.
- [x] 2.3 Ensure `validate_delete` runs inside the same transaction as the delete.

## 3. Register existing kinds

- [x] 3.1 Implement `SystemKindHandler`, `ComponentKindHandler`, `ResourceKindHandler`, `ApiKindHandler` against the `*Details` models from `introduce-catalog-entity-identity`.
- [x] 3.2 Register each handler in its app's `AppConfig.ready()`.
- [x] 3.3 Move API's synchronous spec-URL resolution (per `api-spec-documents`) into `ApiKindHandler.create_details`/`update_details`.

## 4. Cut over the API layer

- [x] 4.1 Switch System create/update/delete in `api/views.py` to call `EntityService`; run `entity-catalog`/`catalog-auth` scenarios for System.
- [x] 4.2 Repeat for Component, Resource, API, verifying each kind's spec-scenario suite after cutover.
- [x] 4.3 Remove now-dead direct-save logic from the viewsets.
