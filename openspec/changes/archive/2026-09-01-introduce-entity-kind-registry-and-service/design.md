## Context

`backend/server/apps/catalog/api/views.py` currently has one DRF viewset per kind (System, Component, Resource, API), each independently calling permission checks, then `serializer.save()`. There's no shared transaction boundary, no audit trail, and no single point where "is this kind known" is answered — an unknown kind currently just isn't routable. `plugin-architecture.md`'s Entity Kind Handlers section (lines 137-163) specifies the exact protocol and pipeline this change implements; ADR 0012 ("centralize-catalog-entity-lifecycle") is the corresponding decision record.

This change assumes `introduce-catalog-entity-identity` has landed: `CatalogEntity` and `*Details` models exist.

## Goals / Non-Goals

**Goals:**
- One `EntityService` is the only path that creates, updates, or deletes a `CatalogEntity`.
- Kind-specific behavior is expressed as an `EntityKindHandler` implementation, registered by `kind_id`.
- Every lifecycle change produces an audit record.
- System/Component/Resource/API continue to behave identically from the REST client's perspective.

**Non-Goals:**
- Discovering handlers via Python entry points / plugin packages — this change registers the four existing kinds in-process at Django app startup. Entry-point discovery is `introduce-plugin-registries`.
- Rewiring ingestion onto `EntityService` — ingestion keeps its current write path until `extract-ingestion-plugin`.
- Capability declarations (`provides=[...]`) on Entity Kinds — that's part of `extract-c4-plugin`, which is the first change that needs them.

## Decisions

**`EntityService` methods are `create(kind_id, spec, metadata, actor)`, `update(entity_id, spec, metadata, actor)`, `delete(entity_id, actor)`** — kind-agnostic signatures; the service resolves the handler internally. Alternative considered: give each viewset its own thin service subclass — rejected because it reintroduces per-kind duplication of the transaction/audit wrapper, which is exactly what's being centralized.

**Handler registration happens in each kind's Django `AppConfig.ready()`**, calling `registry.register(SystemKindHandler())`. This is the same mechanism `introduce-plugin-registries` will later generalize to entry-point-discovered plugins — using it now, scoped to in-tree code, avoids a throwaway registration mechanism that gets replaced immediately.

**Audit records are append-only rows: `entity_id`, `kind`, `action` (create/update/delete), `actor`, `timestamp`, `diff` (JSON).** Kept intentionally minimal — this change needs *a* durable trail to satisfy the pipeline contract in `plugin-architecture.md:153-161`, not a full audit-log product. Retention/querying UI is out of scope.

**Common-metadata validation (name/title/description/labels/tags/links) lives in `EntityService`, not in each handler.** Handlers only validate/persist `spec` (kind-specific fields), matching the split in `plugin-architecture.md`'s pipeline (`validate common metadata` is a step before `resolve Entity Kind handler`). This is what lets a future third-party kind avoid re-implementing envelope validation.

**`validate_delete` is called synchronously inside the same transaction as the delete**, not as a pre-check outside it — avoids a TOCTOU window between "checked deletable" and "deleted" under concurrent requests (e.g. a Resource gaining a new dependent between check and delete).

## Risks / Trade-offs

- [Wrapping four existing viewsets' worth of behavior into one generic service risks losing kind-specific edge cases (e.g. API's `spec_source`/`spec_url` resolution)] → Kind-specific side effects that aren't pure data validation (like API's synchronous spec fetch on save, per `api-spec-documents` spec) stay inside the handler's `create_details`/`update_details`, not in `EntityService`; `EntityService` only owns the generic envelope + transaction + audit shell.
- [A single shared transaction across common-metadata + kind-details write increases lock contention if a kind handler does slow I/O inside it] → Flag any handler doing synchronous external I/O (API's URL spec fetch is the existing example) as a known trade-off; resolving it (e.g. moving fetch to async) is out of scope for this change and can be revisited per-kind later.
- [Introducing an audit table is a new migration and a new write on every mutation] → Keep the audit write in the same transaction so it can never silently diverge from the entity state, and index it by `entity_id` only (no reporting requirements yet).

## Migration Plan

1. Add `EntityKindHandler` protocol, `EntityKindRegistry`, `EntityService`, and the audit model/migration. No existing code path changes yet.
2. Implement and register `SystemKindHandler`/`ComponentKindHandler`/`ResourceKindHandler`/`ApiKindHandler` against the existing `*Details` models from change 1.
3. Switch `api/views.py` create/update/delete actions to call `EntityService` one kind at a time, running the full `entity-catalog`/`catalog-auth` spec-scenario suite after each.
4. No contract/rollback step needed — this change adds a layer in front of existing storage; it can be reverted by reverting the viewset change alone if the service has a defect, since no data shape changes.

## Resolved

- **Delete-time relation checking**: `validate_delete` is the primary, user-facing check (it can name exactly what's blocking the delete — "2 Components still depend on this Resource" — before the transaction even attempts the delete). The DB's `on_delete=PROTECT` FKs stay in place underneath as a defense-in-depth backstop, not duplicated application logic to remove: if a `validate_delete` implementation misses a case, the database still refuses the delete rather than silently succeeding, it just surfaces as a less friendly `ProtectedError` in that fallback case. No code needs to treat these as mutually exclusive.
