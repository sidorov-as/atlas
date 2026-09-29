## Context

`plugin-architecture.md`'s Facets-and-views section (lines 165-184) draws the exact example this change implements: `DatabaseSchema` Facet (dialect, source SQL, parsed schema, parse status) backing an "ER Diagram View" that's derived from it, not part of it. `docs/conversation.txt`'s later exchange ("Я предлагаю сузить `Facet`...") locks in the distinction: a Facet has data, schema, ownership, and lifecycle; a view contribution only displays or computes a representation; one facet can have several views; removing a view contribution never deletes facet data. Nothing in the current PoC has this shape — Resource today has no schema concept at all, and no existing spec describes SQL parsing or ER diagrams.

## Goals / Non-Goals

**Goals:**
- `DatabaseSchema` is a plugin-owned `OneToOne` model on `CatalogEntity`, with its own migration, API, and lifecycle independent of `ResourceDetails`.
- `schema.host.v1` is a capability, declared by whichever kind(s) can host the facet, and the ER Diagram tab is gated by `entitySupports('schema.host.v1')`, not a hard-coded `kind === 'resource'` check.
- Facet CRUD goes through a plugin-owned endpoint, not the core Entity Service (Facets are explicitly outside the kind's `spec`/lifecycle contract).
- Removing the `atlas.database-schema` plugin (conceptually, not exercised until change 12) must not delete a Resource's own data, and vice versa.

**Non-Goals:**
- Full SQL-dialect parsing fidelity — pick one dialect (PostgreSQL, matching the project's own database) for the initial parser, matching `plugin-architecture.md`'s own illustrative `ApiDetails.api_type` pattern of "start with one, extend later." Multi-dialect parsing is a follow-on, not required to prove the Facet/view architecture.
- A generic "any entity can carry any facet" UI — this change wires the editor and ER Diagram tab specifically for Resource; the mechanism is generic (any `CatalogEntity`), but this change doesn't build a facet-picker UI for arbitrary kinds.
- Any relationship between `DatabaseSchema`'s parsed tables and Architecture Relationships (e.g. an FK in the schema implying a data-access relationship) — that's plausible future work (`docs/conversation.txt` gestures at "operation-level dependency graph" as a separate future plugin) but out of scope here.

## Decisions

**`DatabaseSchema` is `OneToOneField(CatalogEntity, primary_key=True)`, not `OneToOneField(ResourceDetails, primary_key=True)`.** This is the literal architectural point being proven: a Facet attaches to the stable core identity, so it would keep working unmodified even if `ResourceDetails` were replaced by a different kind's details model with the same `schema.host.v1` capability. Attaching to `ResourceDetails` instead would recreate the cross-plugin-table-FK problem changes 5-7 spent effort avoiding.

**`schema.host.v1` is declared by `resource`, unconditionally (not scoped to `type=database` resources).** A `cache`/`queue`/`bucket` Resource carrying an (empty, unset) schema facet is harmless — the facet is optional per-entity regardless of kind-level capability declaration, matching `plugin-architecture.md:31` ("optional, structured aspect"). Scoping the *capability* by a Resource's own `type` field would require the capability registry to understand per-instance state, which `plugin-architecture.md`'s kind-level `provides=[...]` model doesn't support and shouldn't be stretched to support for this one case.

**Facet CRUD is `POST/GET/PATCH /api/plugins/atlas.database-schema/resources/{entityId}/schema`, not `PATCH /api/resources/{id}` with a `spec.databaseSchema` sub-object.** Keeping it a fully separate endpoint (not merged into the kind's own serializer) is what makes "Standard Catalog doesn't know this facet exists" actually true at the API level, not just the model level — mirrors the specialized-namespace convention `extract-c4-plugin` established.

**SQL parsing runs synchronously on facet save, storing `parse_status` (`ok`/`failed`) and the parsed structure**, mirroring `api-spec-documents`' existing synchronous-resolve-on-save pattern for API specs rather than inventing an async job pattern this program doesn't have yet (background job runtime is explicitly an open implementation detail in `plugin-architecture.md`'s "Open implementation details").

## Risks / Trade-offs

- [SQL parsing is new, non-trivial logic with real correctness risk (malformed SQL, dialect quirks)] → `parse_status=failed` must never block saving `source_sql` itself — mirrors `api-spec-documents`' "failed refresh preserves the last-good snapshot" pattern: a bad SQL edit is saved as-is with a visible failed-parse indicator, not rejected outright, so the user doesn't lose their draft.
- [This is the first Facet, so the "Facet CRUD doesn't go through the Entity Service" boundary is easy to get wrong by instinct (reusing Entity Service tooling would feel natural)] → Document explicitly in the plugin's own code (and in review) that Facet endpoints are a deliberate architectural exception, not an oversight, referencing ADR 0018.
- [An ER Diagram computed from freshly-parsed SQL on every tab open could be slow for a large schema] → Cache the parsed structure (already stored as `parsed_schema`, not re-parsed on read) and render the ER Diagram from that stored structure, not by re-parsing `source_sql` per request.

## Migration Plan

1. Scaffold `plugins/database-schema/backend/` and `plugins/database-schema/frontend/`, declaring the manifest dependency on `atlas.standard-catalog`.
2. Add the `DatabaseSchema` model/migration and the facet CRUD endpoint; add the PostgreSQL-dialect parser.
3. Declare `schema.host.v1` on the `resource` kind (in Standard Catalog's registration — this is the one place this change touches Standard Catalog code, adding a declaration, not a dependency).
4. Add the facet editor UI on Resource's detail page and the ER Diagram tab gated by `entitySupports('schema.host.v1')`.
5. Verify: create a Resource, attach a schema, confirm the ER Diagram renders; delete the facet, confirm the Resource itself is unaffected; (conceptually) confirm removing `atlas.database-schema` from selection leaves the Resource's own data intact (full removal-preserves-data guarantee is formalized and tested in change 12, but this change's data model must not violate it from day one).
6. Rollback: this is entirely additive new functionality with no existing behavior to preserve; revert is a straightforward plugin deselection plus migration rollback.

## Resolved

- **`parsed_schema` contract stability**: provisional/internal, no external contract promised — consistent with the whole internal Plugin API being `0.x` per `introduce-plugin-distribution-and-composer`. Free to reshape until a second consumer beyond the ER Diagram view exists.
