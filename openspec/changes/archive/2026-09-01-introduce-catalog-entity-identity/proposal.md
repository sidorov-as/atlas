## Why

Every catalog entity kind (`System`, `Component`, `Resource`, `API`, `Group`) is its own concrete Django table inheriting from the abstract `CatalogEntity`/`IngestibleEntity` base (`backend/server/apps/catalog/models/base.py`), and `Relation` stores edges as polymorphic `(subject_kind, subject_id)` / `(object_kind, object_id)` pairs (`backend/server/apps/catalog/models/relation.py`). There is no single row a plugin can attach data to, no way to represent an entity whose kind provider is absent, and no real foreign key between related entities. `docs/plugin-architecture.md` requires one concrete `CatalogEntity` identity with plugin-owned `OneToOne` detail models and real FK-based relations (ADR 0001). Every later plugin change — Entity Kind registry, Facets, capability-targeted views, Unavailable Entities — depends on this identity model existing first, so it has to land before any plugin extraction work.

## What Changes

- Add a concrete `CatalogEntity` model: `id` (UUID primary key), `kind`, `namespace`, `name`, `title`, `description`, `documentation`, `labels`, `tags`, `links`, `owner` (FK to the owning `CatalogEntity`, kind `group`), `created_at`/`updated_at`, `source_kind`, `ingested_from`. This model has no abstract subclassing — it is one physical table.
- **BREAKING**: Remove the abstract `CatalogEntity`/`IngestibleEntity` base classes. `System`, `Component`, `Resource`, `API`, and `Group` stop being concrete tables with their own primary keys and become `SystemDetails`, `ComponentDetails`, `ResourceDetails`, `ApiDetails`, `GroupDetails` — each a `OneToOne` to `CatalogEntity` holding only kind-specific fields (`type`, `lifecycle`, `system`, `spec_source`, etc.). Kind-specific FKs (`Component.system`, `Component.provides_apis`) become FKs/M2Ms to `CatalogEntity` filtered by `kind`, not to the other kind's table.
- **BREAKING**: Rename `backend/server/apps/catalog/models/user.py`'s `User` model to `Actor` (`ActorDetails` after the split), migrated to `CatalogEntity`/`OneToOne` identically to the other four kinds. The rename resolves a naming collision with Authentication Core's `Principal`/session concept (`introduce-auth-provider-extension`) and reflects what this record has always actually been: a named diagram/relationship endpoint (C4 Person), not a product catalog subject. `ActorDetails.account` (today's nullable link to the Django login user) carries over unchanged — an Actor with no linked account is a pure diagram actor that never logs in.
- **BREAKING**: Replace `Relation`'s `(subject_kind, subject_id)` / `(object_kind, object_id)` integer pairs with `subject` and `object` foreign keys to `CatalogEntity.id`.
- Write a one-time data migration that creates a `CatalogEntity` row for every existing `System`/`Component`/`Resource`/`API`/`Group`/`User` row (preserving `id`-equivalent identity via a mapping table or reused UUIDs), re-points `Relation` rows at the new `CatalogEntity` ids, and re-points every FK/M2M that currently targets a kind table at `CatalogEntity`.
- Update every serializer, viewset, filter, and permission check in `backend/server/apps/catalog/api/` that currently queries `System.objects`/`Component.objects`/etc. directly to query through `CatalogEntity` plus the matching `*Details` join.
- Keep REST paths, response shapes, and all currently-passing `entity-catalog`/`entity-relations`/`entity-identity`/`catalog-auth` behavior unchanged from the client's point of view — this change is a storage-model rewrite, not a product change.

## Capabilities

### New Capabilities
- `catalog-entity-identity`: every catalog record has one stable, kind-independent global identity (`CatalogEntity.id`); an entity kind's data lives in a plugin/module-owned `OneToOne` details model keyed by that id, never in a table of its own; relations reference `CatalogEntity.id` directly rather than a `(kind, local_id)` pair.

### Modified Capabilities
- `entity-catalog`: the entity envelope response gains a stable `id` field (previously entities were identified only by `kind`+`namespace`+`name` in routes; the numeric per-table primary key was kind-scoped and not globally comparable). Clients MAY now reference an entity by `id` in addition to `kind`/`name`.

## Impact

- **Backend**: `backend/server/apps/catalog/models/` (new `base.py`, one `*Details` model per kind, rewritten `relation.py`), a new large data migration, every file under `backend/server/apps/catalog/api/` (`views.py`, `schemas.py`, `filters.py`, `permissions.py`), `backend/server/apps/catalog/relations.py` recomputation logic, `backend/server/apps/ingestion/` claim/arbitration code that currently sets `source_kind`/`ingested_from` on the kind table.
- **Frontend**: none functionally, but `frontend/src/lib` response types gain a stable `id` field consumers can start relying on instead of route-scoped `(kind, name)` pairs.
- **Data**: requires a backfill migration on every environment; must follow the expand/contract discipline this program later formalizes in `introduce-plugin-lifecycle-and-failure-isolation` even though that change hasn't landed yet — do the expand/contract split manually here.
- **Dependents**: every other change in this program (`introduce-entity-kind-registry-and-service` onward) assumes `CatalogEntity` exists.
