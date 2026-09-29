## Why

After `introduce-catalog-entity-identity`, `CatalogEntity` is the identity model, but nothing yet governs *how* an entity kind's lifecycle (create/update/delete) is authorized, validated, and persisted uniformly. Today that logic is duplicated per-viewset in `backend/server/apps/catalog/api/views.py` — System, Component, Resource, and API each hand-roll their own authorize→validate→save flow. `docs/plugin-architecture.md` requires a single core Entity Service that owns the transaction (authorize → validate common metadata → resolve Entity Kind handler → open transaction → change `CatalogEntity` → invoke kind handler → write audit → commit) and an `EntityKindHandler` protocol that kind providers implement (ADR 0004, ADR 0012). Centralizing this now, before any kind is extracted into a plugin, means the extraction changes (5-7) move code into a stable contract instead of inventing the contract while also moving code.

## What Changes

- Add an `EntityKindHandler` Protocol (`kind_id`, `spec_schema`, `create_details`, `update_details`, `serialize_details`, `validate_delete`) matching `plugin-architecture.md:142-150`.
- Add a core `EntityKindRegistry` that kind providers register against at startup (in-process for this change; entry-point discovery is added in `introduce-plugin-registries`).
- Add a core `EntityService` that is the *only* code path allowed to create, update, or delete a `CatalogEntity`: it authorizes, validates the common envelope, resolves the kind handler from the registry, opens one transaction, updates `CatalogEntity`, invokes the handler for kind-specific data, writes an audit record, and commits.
- **BREAKING (internal)**: rewrite `System`/`Component`/`Resource`/`API` viewsets in `backend/server/apps/catalog/api/views.py` to call `EntityService` instead of calling `serializer.save()` directly. Register each existing kind as an `EntityKindHandler` implementation backed by its `*Details` model from change 1.
- Add an audit record model/table for entity lifecycle changes (create/update/delete), since the Entity Service's contract requires writing one on every change and none currently exists.
- Ingestion's upsert path (`backend/server/apps/ingestion/`) is *not* rewired onto `EntityService` in this change — that's `extract-ingestion-plugin`'s job, once ingestion itself becomes a plugin. This change only guarantees the Entity Service exists and that manual/API writes use it.

## Capabilities

### New Capabilities
- `entity-kind-registry`: kind providers register an `EntityKindHandler` (spec schema + create/update/serialize/validate-delete) against a stable `kind_id`; the registry rejects two handlers registering the same `kind_id`.
- `entity-lifecycle-service`: a single core service owns the authorize → validate → transaction → kind-handler → audit → commit sequence for every Catalog Entity create/update/delete, regardless of caller (UI-facing REST today; ingestion and other callers later).

### Modified Capabilities
- `entity-catalog`: System/Component/Resource/API create, update, and delete now happen through the shared Entity Service rather than per-kind viewset logic; behaviorally the CRUD requirements are unchanged, but a kind with no registered handler is now a distinguishable, uniform failure rather than a 404 from URL routing.

## Impact

- **Backend**: new `backend/server/apps/catalog/services/entity_service.py` (or similar), new `backend/server/apps/catalog/kinds/registry.py`, rewritten `api/views.py` create/update/delete actions, new audit model + migration.
- **Behavior preserved**: `entity-catalog`, `catalog-auth` (ownership permission check now runs inside the Entity Service's authorize step, same rule, same call site conceptually), `entity-claim-arbitration` (arbitration still happens before ingestion calls into whatever it calls — unaffected until ingestion is rewired in a later change).
- **Dependents**: `introduce-plugin-registries` (kind registry becomes one of several registries populated from entry points), `extract-standard-catalog-plugin`/`extract-apis-plugin` (kind handlers move into plugin packages using this exact protocol), `extract-ingestion-plugin` (ingestion becomes an `EntityService` caller).
