## Context

Today: `CatalogEntity` and `IngestibleEntity` (`backend/server/apps/catalog/models/base.py`) are Django `abstract = True` base classes. `System`, `Component`, `Resource`, `API` inherit `IngestibleEntity`; `Group` inherits `CatalogEntity` directly. Each is its own concrete table with its own auto `id`. `Relation` (`backend/server/apps/catalog/models/relation.py`) stores `subject_kind`/`subject_id`/`object_kind`/`object_id` as plain `CharField`/`BigIntegerField` — there is no database-level FK, so referential integrity across kinds is enforced only by application code in `apps.catalog.relations.recompute_relations`.

`docs/plugin-architecture.md` (§ "Catalog data model") requires the opposite shape: one concrete `CatalogEntity` row is the only global identity; kind-specific data attaches via `OneToOne`. This is ADR 0001, and the conversation that produced it (`docs/conversation.txt`, exchange on "единая concrete-модель `CatalogEntity`") was explicit that the cost is an extra join plus an application-level check that (e.g.) `DatabaseSchema` is only attached where `kind=resource`, in exchange for real FKs, uniform permissions/audit/search, and no ambiguous `(kind, id)` pairs after a kind is removed.

## Goals / Non-Goals

**Goals:**
- One physical `CatalogEntity` table is the sole source of global identity for every catalog record.
- Kind-specific data lives in a `OneToOne` "details" model per kind, with no fields duplicated onto `CatalogEntity`.
- `Relation` references `CatalogEntity.id` via real FKs in both directions.
- Every existing behavioral requirement in `entity-catalog`, `entity-identity`, `entity-relations`, `entity-claim-arbitration`, and `catalog-auth` continues to pass unchanged against the new storage model.

**Non-Goals:**
- Introducing the `EntityKindHandler` protocol or Entity Service transaction — this change only reshapes storage; `introduce-entity-kind-registry-and-service` adds the behavior layer on top.
- Making entity kinds pluggable/removable — `System`/`Component`/`Resource`/`API`/`Group` remain compiled into `server.apps.catalog` in this change; extraction into a Standard Catalog plugin happens later.
- Changing any REST route, response field (other than adding `id`), or permission rule.
- Preserving existing catalog data across the migration. This project has no production deployment yet; the schema change ships against an empty database, with `seed_booking_demo.py` updated to populate a test catalog on the new models. If a production deployment exists by the time this change lands, this Non-Goal must be revisited and an expand/contract data migration designed before proceeding.

## Decisions

**`CatalogEntity.id` is a UUID, not the existing per-table integer PK.** A UUID is stable across a details model losing its provider entirely (Unavailable Entity, added later) and never collides between two kinds' formerly-independent integer sequences. Alternative considered: keep `BigAutoField` and rely on `(kind, id)` staying unique — rejected because that's exactly the polymorphic-pair shape ADR 0001 is replacing.

**One `*Details` model per kind, not a shared side table.** `SystemDetails`, `ComponentDetails`, `ResourceDetails`, `ApiDetails`, `GroupDetails` are separate Django models, each `OneToOneField(CatalogEntity, primary_key=True, on_delete=models.CASCADE)`. Matches the illustrative `ApiDetails` in `plugin-architecture.md:124-133` and is what later plugin extraction (change 5/6) will physically move into separate apps — doing it as one shared JSON side table now would have to be undone.

**Kind-specific FKs point at `CatalogEntity` filtered by kind in application code, not at the `*Details` table.** E.g. `ComponentDetails.system` becomes `ForeignKey(CatalogEntity, on_delete=models.PROTECT)` with a `CHECK`/clean-time assertion that the referenced row has `kind='system'`, mirroring `plugin-architecture.md`'s note that the core doesn't know `DatabaseSchema` is only valid for `Resource` — that check belongs to the owner, not the database schema. Alternative (a Django `GenericForeignKey`) was rejected: it can't carry a real DB-level FK constraint at all, which is worse than what exists today.

**`User` is renamed to `Actor` as part of this migration, not left for a later change.** `Actor` was never a product catalog subject the way System/Component are — it has no detail page, no create/edit form, and is admin-managed only, existing purely so Architecture Relationships have a person to point at (`architecture-relationships` spec). Migrating it alongside the other four kinds now, rather than special-casing "four kinds plus one weird one" through this change and then renaming later, keeps the model shape uniform: `ActorDetails` is exactly as thin as `GroupDetails`, just with `display_name`/`email`/nullable `account` instead of `type`/`members`. The rename itself (not just the storage-model change) happens here because `introduce-auth-provider-extension` later introduces a `Principal` concept for login identity, and shipping a model still called `User` right up until that change would force a confusing simultaneous rename-and-refactor there instead of a clean one here.

**`Relation.subject_entity`/`object_entity` are added as non-null FKs to `CatalogEntity` directly, replacing the old `subject_kind`/`subject_id`/`object_kind`/`object_id` columns in one migration.** With no existing data to preserve (see Non-Goals), there's no need for the nullable-then-backfill-then-non-null sequencing a live migration would require; `apps.catalog.relations.recompute_relations` is rewritten against the new columns in the same change that drops the old ones.

## Risks / Trade-offs

- [Every viewset/serializer/permission check in `backend/server/apps/catalog/api/` touches the changed models] → Land the model change and the application-code rewrite (`api/views.py`, `api/schemas.py`, `api/filters.py`, `api/permissions.py`, `apps/catalog/relations.py`, `apps/ingestion/` claim logic) in one change, with the full existing test suite (`entity-catalog`, `entity-identity`, `entity-relations`, `entity-claim-arbitration`, `catalog-auth` spec scenarios) as the acceptance gate before merging — no phased/production rollout to sequence around, since the change ships against an empty database (see Non-Goals).
- [`Group.members` M2M and `Component.provides_apis`/`consumes_apis` M2M currently point at concrete kind tables] → These become M2Ms to `CatalogEntity`; application code must filter by `kind` where the field is kind-specific (e.g. `provides_apis` should only ever reference `kind='api'` rows) since the DB can no longer express that constraint via the target table alone.
- [Ownership FK (`owner`) currently points at `Group`; `Group` itself becomes `CatalogEntity`+`GroupDetails`] → `CatalogEntity.owner` becomes a self-referential FK (`ForeignKey('self', null=True, on_delete=models.PROTECT)`, matching the illustrative model in `plugin-architecture.md:117`), constrained at the application layer to rows with `kind='group'`.

## Migration Plan

1. **Models**: add `CatalogEntity` and all six `*Details` tables (including `ActorDetails`, renamed from `User`); replace `Relation`'s `subject_kind`/`subject_id`/`object_kind`/`object_id` with non-null `subject_entity`/`object_entity` FKs; drop `System`/`Component`/`Resource`/`API`/`Group`/`User` tables — all in one migration, since there is no existing data to preserve (see Non-Goals).
2. **Switch reads/writes**: rewrite `api/views.py`, `api/schemas.py`, `api/filters.py`, `api/permissions.py`, `apps/catalog/relations.py` (`recompute_relations`), and `apps/ingestion/` claim/arbitration code against `CatalogEntity`/`*Details` exclusively.
3. **Seed data**: update `backend/server/apps/catalog/management/commands/seed_booking_demo.py` to populate the new models.
4. **Verify**: run the full existing spec-scenario suite (`entity-catalog`, `entity-identity`, `entity-relations`, `entity-claim-arbitration`, `catalog-auth`) against the new models.
5. Remove the now-dead abstract `IngestibleEntity`/old `CatalogEntity` base classes and any code path still importing them.

If a production deployment with real data exists by the time this change is implemented, this plan is invalid and must be redesigned as an expand/contract migration (per the policy `introduce-plugin-lifecycle-and-failure-isolation` formalizes) before proceeding.

## Resolved

- **`User`/`Actor` and `CatalogEntity`**: resolved — `Actor` (renamed from `User`) is migrated into `CatalogEntity`/`ActorDetails` in this change, on equal footing with the other four kinds. See the Decisions section above. `Group.members` continues to reference `Actor` (formerly `User`) via M2M, now targeting `CatalogEntity` filtered to `kind='actor'` like every other kind-scoped reference in this change.
- **Backfill / production migration strategy**: resolved — not needed. The project has no production deployment; it runs on a clean database with `seed_booking_demo.py` providing test data. See the Non-Goals and Migration Plan above.
