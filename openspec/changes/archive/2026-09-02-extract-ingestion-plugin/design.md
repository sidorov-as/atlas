## Context

`server.apps.ingestion` today (per `catalog-ingestion`, `entity-claim-arbitration`, and the ingestion-relationship parts of `architecture-relationships`) discovers `catalog-info.yaml` files via `GitHubConnector`, parses multi-document manifests, arbitrates claims against `source_kind`/`ingested_from`, and upserts entities and relationships directly against the catalog models. None of this goes through `EntityService` — it predates it entirely, and `introduce-entity-kind-registry-and-service` explicitly deferred rewiring ingestion (see that change's Non-Goals). `plugin-architecture.md`'s Ingestion section (lines 458-471) and the pipeline diagram (`SourceConnector → Artifact → DocumentParser → EntityIntent → EntityKindHandler validation → core Entity Service`) is the target shape; ADR 0017 is "route ingestion through the entity service."

## Goals / Non-Goals

**Goals:**
- Every entity write ingestion performs goes through `EntityService`, identically to a manual/API write, carrying `source_kind=yaml`/`ingested_from`.
- `SourceConnector` and `DocumentParser` are plugin-owned extension points; `GitHubConnector` and the `catalog-info.yaml` parser are registered implementations, not hard-coded call sites.
- Every existing `catalog-ingestion`/`entity-claim-arbitration` scenario passes unmodified.
- Manual/API entity management is unaffected whether or not `atlas.ingestion` is selected.

**Non-Goals:**
- Adding a second connector (GitLab, catalog-info-in-a-different-format) — `plugin-architecture.md`'s own text says `GitHubConnector` remains the only v1 implementation; this change only makes it swappable in principle, not swapped in practice.
- Splitting connectors into their *own* separate plugins consuming `atlas.ingestion`'s extension points from outside the ingestion plugin package — `plugin-architecture.md`'s example layering (`Atlas Core → Ingestion Plugin → GitHub Connector`) is aspirational; this change keeps `GitHubConnector` inside `plugins/ingestion/` for now, with the extension point real and documented but only self-consumed.
- Changing arbitration semantics, conflict recording, or the adoption endpoint's behavior in any way.

## Decisions

**`EntityIntent` is a value type (`kind`, `namespace`, `name`, `metadata`, `spec`, `source_kind='yaml'`, `ingested_from`), constructed by the parser, consumed by the arbitration step, and only then passed to `EntityService.create`/`.update`.** This mirrors `plugin-architecture.md:15-17`'s definition exactly ("a proposed state... submitted for validation and reconciliation through the Entity Service"). Arbitration happens *before* `EntityService` is called — a rejected claim never reaches the service at all, so `EntityService` doesn't need arbitration-awareness; it just knows "an ingestion writer is asking to create/update kind X with source_kind=yaml."

**`EntityService` gains an explicit `source` parameter (`manual` vs `yaml`) rather than ingestion setting `source_kind` directly on the entity after the fact.** Keeping `source_kind` assignment inside the service (not a post-write patch by the caller) preserves the "one transaction, one commit" guarantee from change 2 — a caller-side patch after `EntityService.create` returns would be a second, unaudited write.

**Per-manifest failure isolation (an invalid document doesn't block others in the same run) is implemented by catching a failed `EntityIntent`/`EntityService` call per-document inside the run loop**, not by wrapping the whole run in a single transaction. This is unchanged from today's behavior in spirit but now the isolation boundary is explicitly "one `EntityService` call per document," which is a cleaner unit than the current ad hoc per-model save.

**Discovery runs are scheduled via `django-apscheduler`**, the program's chosen background-job runtime (resolving the "background job runtime and scheduling technology" item `plugin-architecture.md` leaves as an open implementation detail). `atlas.ingestion` registers its discovery-run job with APScheduler under a job id the plugin owns; `introduce-plugin-lifecycle-and-failure-isolation`'s disable semantics pause that job (via APScheduler's `pause_job`) rather than needing bespoke scheduling-suspend logic.

**`atlas.ingestion.connectors.v1`/`atlas.ingestion.parsers.v1` are `keyed` extension points** (per `plugin-architecture.md`'s cardinality model from change 4's design) — keyed by connector/parser id, so a future second connector registers alongside `GitHubConnector` without either needing to know about the other.

## Risks / Trade-offs

- [Rewiring the write path is the highest-regression-risk part of this change — arbitration, conflict recording, and relationship reconciliation are intricate existing behavior] → Convert one write path at a time behind the existing test suite: first plain entity upsert (System/Component/Resource/API), verified against `catalog-ingestion` and `entity-claim-arbitration` scenarios, then Architecture Relationship reconciliation (the `architecture-relationships` ingestion scenarios), each gated on full scenario-suite passage before moving to the next.
- [`EntityService`'s transaction-per-entity model may be slower than today's potential batch-upsert if the current implementation does any batching] → Acceptable: `plugin-architecture.md`'s pipeline is explicit that ingestion "does not duplicate validation" and routes through the same single-entity service; if a real performance regression appears in practice, address it as a follow-up (e.g. Entity Service supporting a bulk mode) rather than reintroducing a parallel direct-write path.
- [Extension points owned by a non-core plugin are new territory — no prior art for "does the DAG resolve correctly when the owner is itself optional"] → Since `atlas.ingestion` is optional and currently the sole consumer of its own extension points, there's no cross-plugin ordering scenario to get wrong yet; the design is proven structurally, and a real second consumer would be the next thing to validate it against.

## Migration Plan

1. Scaffold `plugins/ingestion/backend/`; move `RegisteredRepository`, conflict-record models, and `GitHubConnector` as-is (no behavior change), declaring the manifest dependency on `atlas.standard-catalog`.
2. Add `EntityIntent`, the `atlas.ingestion.connectors.v1`/`atlas.ingestion.parsers.v1` extension points, and register `GitHubConnector`/the YAML parser against them.
3. Add the `source` parameter to `EntityService`; rewire plain entity upsert (no relationships yet) through it one kind at a time, verifying `catalog-ingestion` and `entity-claim-arbitration` scenarios for that kind after each.
4. Rewire Architecture Relationship reconciliation through the same `EntityIntent`/`EntityService` path (relationships aren't `CatalogEntity` writes themselves, but their reconciliation depends on entity upsert having already happened via the new path) — verify `architecture-relationships`' ingestion scenarios.
5. Delete the old direct-write upsert code from `server.apps.ingestion`; confirm nothing remains there once the plugin package fully replaces it.
6. Rollback: steps 1-2 are additive; steps 3-4 are the risk-bearing cutover and should each be independently revertible per-kind if a scenario regresses.

## Resolved

- **`EntityIntent` validation split**: two passes, not one. The `DocumentParser` validates syntactically (is this valid YAML matching the manifest schema — the same check `catalog-ingestion`'s "per-manifest failure isolation" already performs today), producing the `EntityIntent`. The target kind's `EntityKindHandler.spec_schema` then validates semantically (do reference fields resolve, are kind-specific constraints satisfied) as part of the normal `EntityService` pipeline — identical to how a manual/API write's `spec` is validated. This matches `plugin-architecture.md`'s pipeline diagram (`EntityKindHandler` validates spec as a step after `EntityIntent` exists) and requires no new validation surface beyond what changes 2 and this change already build.
