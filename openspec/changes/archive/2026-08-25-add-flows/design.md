## Context

Atlas's catalog (`apps/catalog`) models System/Component/Resource/API as `CatalogEntity` subclasses with a shared envelope (name/namespace/title/description/labels/tags/links, unique per kind), plus a derived `Relation` table recomputed from each entity's `spec` reference fields (`dependsOn`, `providesApis`, ...). Cross-entity references elsewhere in the codebase use a `kind:name` ref string, parsed and resolved by `apps/catalog/refs.py`.

C4 diagrams (`diagram-stub` spec, ADR 0002) are a **separate, unrelated** concern: server-rendered SVG, generated fresh per request from the derived `Relation` graph, no client rendering, no cache. Flows do not touch this pipeline at all — they are hand-authored narrative content, not a computed topology view.

The frontend already uses `@gravity-ui/uikit`, `@gravity-ui/navigation`, and `@gravity-ui/icons`; generic list-page infrastructure (`FilterBar`, `EntityTable`) and a markdown renderer (`MarkdownDescription`) already exist and are reusable as-is.

## Goals / Non-Goals

**Goals:**
- Let a team document a cross-system process as an ordered, branching sequence of steps, each optionally pointing at a real catalog entity.
- Render that sequence as a left-to-right tree diagram, editable via a JSON editor with live preview.
- Reuse existing UI/API patterns (FilterBar, ref grammar, markdown rendering) wherever they already fit.

**Non-Goals:**
- No relation to the C4/diagram-stub pipeline, no shared rendering code, no shared data model.
- No support for steps rejoining after a branch (DAG reconvergence) in v1 — strict tree only.
- No YAML ingestion for Flows, no `owner`/tags/labels envelope — Flows are not a `CatalogEntity`.
- No general-purpose auto-layout dependency (dagre/elk) — a tree-only layout is hand-written instead.
- No structured/form-driven step builder — the JSON editor is the authoring surface for v1.

## Decisions

**1. `Flow` lives in `apps/catalog` as a plain (non-`CatalogEntity`) model, not a new Django app.**
It needs `System` and `refs.py` from `catalog` regardless; a new app would only add boilerplate (app config, migrations dir, API routing) for a single model with no independent lifecycle. Rejected: separate `apps/flows` app — more ceremony, no isolation benefit since it's tightly coupled to `catalog` anyway.

**2. `Flow` does not inherit `CatalogEntity`.**
`CatalogEntity` brings `namespace`+unique-name identity, `labels`, `tags`, `links`, and (via `IngestibleEntity`) YAML-ingestion source tracking — none of which apply to Flows (no YAML source, no independent identity anything else refs *into*). Modeling it as a plain model with just `system` (FK), `name`, `description`, `steps` avoids inheriting machinery that would sit unused. Rejected: making Flow a `CatalogEntity` subclass — would need to explain away ingestion/labels/tags fields that don't apply, and would misleadingly suggest Flows participate in the `kind:name` ref namespace the way System/Component do (nothing needs to reference *a Flow*, only the reverse).

**3. Step entity references (`entity_ref`) are validated strings, not FK/M2M columns, and do not feed the derived `Relation` table.**
This is a deliberate departure from how `Component.dependsOn`/`providesApis` work. Those are structural, single-valued-per-relationship-type reference fields that define the entity's own topology. A step's `entity_ref` is different in kind: a step can point at any entity of any kind, the same entity can appear in many steps of many flows, and Flow topology (which step follows which) is orthogonal to catalog topology (which entity depends on which). Modeling every `entity_ref` as an M2M would only buy "which flows mention entity X" queries, which nothing in this proposal needs; it can be added later as a derived index without changing the `steps` JSON shape, the same way `Relation` was layered on top of Component's reference fields without changing `Component` itself.
Validation still resolves each `entity_ref` through `refs.py`'s `resolve_ref()` at save time and rejects the save if it doesn't resolve — this catches typos/dangling refs without requiring a stored FK.

**4. Steps are constrained to a strict tree (no reconvergence) in v1.**
Confirmed during exploration: divergence-only (a step has at most one incoming transition) is sufficient for the flows the team wants to document today. This directly enables Decision 5 (no layout library) — a general DAG would need Sugiyama-style layered layout (what dagre provides) to avoid drawing a reconverging step twice.

**5. Tree layout is hand-written, not dagre/elk.**
Because the topology is a guaranteed tree (Decision 4), layout reduces to a textbook two-pass algorithm: DFS to size each subtree, then a second pass assigning `x = depth * columnWidth` and stacking each node's children along `y` by cumulative subtree size. This is small (~50 lines), has no runtime dependency, and produces a deterministic left-to-right layout. If reconvergence is ever needed, this function is replaced by a dagre call (`rankdir: 'LR'`) without changing the `steps` JSON shape or the `@gravity-ui/graph` rendering step downstream of it.

**6. Rendering uses `@gravity-ui/graph`, driven by a JSON-editor-with-preview UX.**
`@gravity-ui/graph` is a natural fit given the frontend already standardizes on Gravity UI, and its block/connection model (explicit `x,y`, anchors, `sourceBlockId`/`targetBlockId`) is exactly what the tree-layout step (Decision 5) needs to produce. The authoring UX is a raw JSON editor over `steps` plus a live preview pane re-running layout+render on every edit — mirroring `@gravity-ui/graph`'s own playground pattern, and matching that a Flow's real content (the narrative: titles, summaries, branching) is the `steps` array, not hand-placed coordinates.

**7. `Flow.system` is required, `on_delete=PROTECT`.**
A Flow always has exactly one home system (confirmed during exploration), which also makes "filter by team" trivial (`Flow.objects.filter(system__owner=team)`, no new field). `PROTECT` rather than `CASCADE` because a flow's steps can reference entities in *other* systems too — deleting the home system shouldn't silently destroy documentation other teams may depend on; the deletion must be a deliberate, explicit action (delete or reassign the flow first).

## Risks / Trade-offs

- **[Dangling refs after entity rename/delete]** `entity_ref` isn't a real FK, so nothing stops a Component from being renamed or deleted out from under a Flow step after the Flow is saved → **Mitigation**: validate on every Flow save (catches authoring-time typos); accept that post-hoc drift is possible in v1, same tradeoff YAML manifests already accept for `owner:` refs (CONTEXT.md).
- **[No "flows mentioning X" query]** Because refs live inside JSON, a Component's detail page can't show "appears in these flows" without a JSON scan or a derived index → **Mitigation**: explicitly deferred (Decision 3); can be added later as a recomputed index table, same pattern as `Relation`, without a `steps` schema change.
- **[Strict-tree constraint may prove too restrictive]** A team documenting a saga where success/failure paths genuinely reconverge (e.g. both notify the same downstream step) will hit the validation rejection → **Mitigation**: confirmed acceptable for v1; Decision 5 is structured so relaxing this later (dagre swap-in) doesn't require a `steps` JSON migration.
- **[New client-rendering surface]** This is the first interactive canvas-rendered UI in the app; no precedent for its performance/bundle-size/testing patterns exists yet → **Mitigation**: `@gravity-ui/graph` already handles canvas/React hybrid rendering internally; flows are expected to be small (a handful of steps), well within what the library is built for.

## Migration Plan

1. Add `Flow` model + migration in `apps/catalog`.
2. Add serializer/viewset + URL routes for CRUD, filtered by `system` and `system__owner`.
3. Add step-validation logic (entity-ref resolution, strict-tree check) at the serializer level.
4. Add `@gravity-ui/graph` npm dependency.
5. Add the tree-layout utility (pure function, unit-testable independent of rendering).
6. Add `FlowsListPage`, `FlowDetailPage`, sidebar nav entry.
No data migration needed (new table, no backfill). No rollback concerns beyond a standard migration reversal — nothing else depends on `Flow` existing.

## Open Questions

- Should `Flow.name` be unique (globally, or per-system)? Not yet decided — needs a default before the spec is written.
- Exact shape of the validation error response when a step's `entity_ref` fails to resolve or the strict-tree rule is violated (single aggregated error vs per-step errors) — an API-contract detail, not a design blocker.
