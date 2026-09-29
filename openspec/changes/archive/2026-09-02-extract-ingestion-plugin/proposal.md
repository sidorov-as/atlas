## Why

`server.apps.ingestion` currently writes catalog entities directly (per `catalog-ingestion`/`entity-claim-arbitration` specs' description of upsert behavior), independent of whatever write path the REST API uses — it doesn't go through `EntityService` at all today, and after change 2 it still doesn't (deliberately deferred there). `plugin-architecture.md` requires ingestion to be an optional platform plugin whose connectors/parsers produce `EntityIntent`s that flow through the *same* core Entity Service used by manual/API writes (ADR 0017), so a manifest upsert and a UI edit share identical validation, permission, and audit behavior. This is also the first change that exercises a plugin owning its *own* extension points for sub-contributors (`SourceConnector`, `DocumentParser`) — `GitHubConnector` becomes one connector implementation among a documented extension point, not the only possible one hard-coded into the pipeline.

## What Changes

- Create `plugins/ingestion/` (backend `atlas_plugin_ingestion`), declaring a manifest dependency on `atlas.standard-catalog` (and implicitly whatever other kind plugins are installed, since ingestion must be able to intend entities of any registered kind).
- Move `RegisteredRepository`, the discovery/scheduling loop, `GitHubConnector`, and manifest parsing out of `server.apps.ingestion` into the new plugin.
- Add `atlas.ingestion.connectors.v1` and `atlas.ingestion.parsers.v1` as plugin-owned extension points (ADR 0014) that `GitHubConnector` and the `catalog-info.yaml` parser register against, from within the same plugin package for now (no separate connector plugin yet — that's future work per `plugin-architecture.md`'s non-goals).
- Rewrite the ingestion pipeline as: `SourceConnector` → fetched Artifact → `DocumentParser` → `EntityIntent` → the Entity Kind's own spec validation → **core `EntityService`** — replacing today's direct-write upsert with a call into `EntityService.create`/`.update` per intended entity, carrying `source_kind=yaml`/`ingested_from` through as Entity Service-recognized fields (already on `CatalogEntity` since change 1).
- Preserve every `catalog-ingestion`/`entity-claim-arbitration`/architecture-relationship-ingestion scenario's *behavior* (first-claim arbitration, per-manifest failure isolation, multi-document manifests, conflict recording, adoption) exactly, now implemented as arbitration-before-`EntityIntent` rather than arbitration-before-direct-write.
- Confirm manual/API entity management continues working with `atlas.ingestion` deselected (already true today, since ingestion is a separate app, but this change must not regress it while rewiring the write path).

## Capabilities

### New Capabilities
- `ingestion-plugin`: ingestion is an optional platform plugin that discovers manifests via pluggable connectors, parses them via pluggable parsers, and applies every resulting change through the core Entity Service as `EntityIntent`s — never by writing `CatalogEntity` or kind-details rows directly.

### Modified Capabilities
- `catalog-ingestion`: requirement text is unchanged (discovery, upsert, per-manifest failure isolation, multi-document manifests, relationship declarations all behave identically) — flagged modified only in that "ingestion SHALL create or update every entity" now explicitly routes through the Entity Service; added as a delta purely to state that routing explicitly as a requirement, since it's a genuine (if behavior-invisible) architectural guarantee worth locking in as a spec.
- `entity-claim-arbitration`: same treatment — arbitration behavior is unchanged, but now explicitly happens before constructing an `EntityIntent`, gating whether `EntityService` is even called for a given ref.

## Impact

- **Backend**: new `plugins/ingestion/backend/`; ingestion's write path changes from direct model saves to `EntityService` calls; `RegisteredRepository`/conflict-record models move with it.
- **Behavior preserved**: every `catalog-ingestion`, `entity-claim-arbitration`, and the ingestion-relationship scenarios in `architecture-relationships` must keep passing unmodified.
- **First plugin-owned extension points**: `atlas.ingestion.connectors.v1`/`atlas.ingestion.parsers.v1` are the first extension points not owned by core — proves ADR 0014's "any plugin may own versioned extension points for others" independent of the core-owned contribution contract from change 4.
- **Dependents**: none directly, but this is the last change before `introduce-auth-provider-extension` and the distribution/lifecycle changes, and the first to prove that a kind-agnostic writer (ingestion) can intend entities of *any* currently-registered kind without importing kind-specific code.
