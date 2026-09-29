## Context

Refs throughout this app are `kind:name` strings (e.g. `api:payments-api`), where `kind` is the lowercase Django `model_name` (`system`/`component`/`resource`/`api`/`group`/`user`). `refName()` strips the prefix for display, but nothing resolves a ref back to a routable id — so anywhere a ref is the only data available (Component's `providesApis`/`consumesApis`, every Relations tab's `target`), the frontend can only show text, never a link.

Separately, two "related-entity table" components already fetch full entity objects (with real `.id`s) but were never wired to the click-to-navigate behavior `EntityListPage`/`TeamsListPage` already have via `useEntityRowActivation`: `ChildTable` (`SystemDetailPage.tsx`) and Team's `OwnedTable` (`TeamDetailPage.tsx`) — two near-duplicate components with the same gap.

`TeamDetailPage` is also the one detail page not built on the shared `EntityDetailPage` chrome (breadcrumb, header, tab bar, right rail) that System/Component/Resource/API all use — it's a bespoke two-column layout with sections stacked via `marginTop`, which is what reads as inconsistent and "slipping together."

The backend already resolves the full target object — id and kind, not just its ref — inside `entity_relations()` (`apps/catalog/relations.py`) before serializing; `_relations_out()` (`apps/catalog/api/views.py`) discards everything but `target.ref` when building `RelationOut` (`apps/catalog/api/schemas.py`).

## Goals / Non-Goals

**Goals:**
- Any related-entity table on a detail page supports the same click-to-select / fast-second-click-to-navigate behavior as the top-level list pages.
- Any ref-only field that has a corresponding relation row (Relations tab targets, Component's Provides/Consumes API) becomes a real link.
- `TeamDetailPage` is rebuilt on `EntityDetailPage`, so it gets the same header/tab/rail chrome and spacing as every other entity kind for free.
- Each detail page's rail Owner field (and System field, where the kind has one) becomes a real link to that entity's detail page.

**Non-Goals:**
- Making ref labels clickable on list-page columns (Owner/System shown in the Systems/Components/Resources/APIs list tables) — those aren't backed by the routable id data this change adds to the *detail-page* entity response; doing so would need the same `ownerId`/`systemId` treatment on the list endpoint, a separate change.
- Making Component's `dependsOn` display or Group member labels clickable — unchanged by this change.
- Adding a User detail page/route — Group member refs stay plain labels; there's nowhere to link them to.
- Changing anything about how relations are *derived* (`relations.py`'s edge computation) — only what's serialized out.

## Decisions

### 1. Add `targetKind`/`targetId` to `RelationOut` instead of a separate resolve endpoint
`entity_relations()` already does `target = target_model.objects.get(pk=row.object_id)` — it has the full object, just narrows it to `target.ref` on return. Changing its return type from `list[tuple[str, str]]` (`predicate`, `target_ref`) to include `target.kind`/`target.id` is a same-sized change, avoids a new endpoint, and gives every consumer (Relations tab, Provides/Consumes API) one shared source of truth instead of two.

Alternative considered: client-side resolve (fetch the entity list filtered by name, match on exact name). Rejected — N+1 requests per row, and fragile if names aren't unique across namespaces (not the case today, but not a guarantee to lean on).

### 2. Component's Provides/Consumes API reads from the relations endpoint, not `spec.providesApis`/`consumesApis`
`componentsApi.relations(id)` filtered to `providesAPI`/`consumesAPI` predicates now carries the same `targetKind`/`targetId` as any other relation row, so both sections use the exact same rendering path as the Relations tab (one link component, not two). The raw `spec.providesApis`/`consumesApis` arrays remain the write path (unchanged) — only the *read/display* side moves to relations data.

Trade-off: this couples the Overview tab's Provides/Consumes API display to relations having been recomputed. Relations are recomputed synchronously on write (per `entity-relations` spec's targeted-recompute requirement), so this is not a staleness risk in practice.

### 3. A small `kindToPath` map lives in the frontend, keyed by lowercase model kind
```ts
const KIND_TO_PATH: Record<string, string> = {
  system: '/systems',
  component: '/components',
  resource: '/resources',
  api: '/apis',
  group: '/teams',
}
```
`user` is intentionally omitted — there's no detail route, so a `targetKind === 'user'` relation row (shouldn't occur from the entity kinds this change touches, but defensively) renders as plain text rather than a broken link.

### 4. `ChildTable` and `OwnedTable` both get `onRowClick={handleRowClick}` from `useEntityRowActivation`, not merged into one component
The hook is already the shared piece; merging `ChildTable`/`OwnedTable` themselves is a larger refactor (different filter sets — `ChildTable` filters by `system`, `OwnedTable` by `owner`) that this change doesn't need to take on to fix the reported bug. Noted as a follow-up, not done here.

### 5. `TeamDetailPage` becomes tabs: Overview / Members / Systems / Components / Resources / APIs
Mirrors how System's detail page organizes Components/Resources/APIs as tabs rather than stacking them. Overview carries the markdown description (today's center-column top content); Members becomes its own tab instead of a fixed block above the owned-entity sections. The right rail (`LinksRail`, "About" fields via `teamRailFields`) comes from `EntityDetailPage` itself, same as every other entity — Team gains a real "About" rail it doesn't have today.

Alternative considered (raised during exploration): keep the current single-scrolling-page layout and add visual separation (dividers/cards) between sections. Rejected in favor of matching the established tab pattern — reuses `EntityDetailPage` wholesale instead of inventing a one-off layout pattern that only Teams would use.

### 6. Rail Owner/System links via new `ownerId`/`systemId` response fields, not a second relations fetch
`owner`/`system` are Django FK fields already dereferenced in `_system_out`/`_component_out`/`_resource_out`/`_api_out` (`apps/catalog/api/views.py`) to build the existing `owner`/`system` ref strings. Adding `owner_id`/`system_id` (`instance.owner.id` / `instance.system.id`, with the same `if instance.system_id else None` null-guard Resource's `system` ref already uses) costs no new query and is the same shape as the already-shipped `RelationOut.targetKind`/`targetId` addition (Decision 1). The frontend renders both via the existing `RelationTargetLink` component (Decision 3) inside the existing `Label` chip — the same building block already used by the Relations tab and Component's Provides/Consumes API links, not a new one.

Alternative considered: derive rail Owner/System links from a second `relations()` fetch per detail page (the `ownedBy`/`partOf` rows already exist there). Rejected — matching by predicate string is more indirect than a same-response field, and adds a redundant request to every detail-page load.

## Risks / Trade-offs

- **[Risk]** Rewriting `TeamDetailPage`'s layout is a visible, all-at-once UI change for anyone with the Teams page open/bookmarked to a specific tab-less URL. → **Mitigation**: no deep-linking to a scroll position exists today (it's one page, one URL), so there's no URL contract to preserve; a default-selected tab (Overview) covers the current "land on the page and see the description" behavior.
- **[Risk]** `RelationOut` is a public API response shape; adding fields is additive/non-breaking for existing consumers, but any consumer doing strict schema validation on the relations endpoint would need to tolerate new fields. → **Mitigation**: purely additive (new optional-in-practice fields alongside the existing `target` string, which is unchanged), no field removed or retyped.
- **[Trade-off]** Provides/Consumes API display now depends on the relations table being in sync rather than reading `spec` directly. → Acceptable per Decision 2 — relations are recomputed synchronously on every write that would change these fields.

## Migration Plan

1. Backend: extend `entity_relations()`'s return shape and `RelationOut`/`_relations_out()` — additive, no migration, no data backfill (relations are derived on read from existing `Relation` rows plus a live lookup of the target object, not stored denormalized).
2. Frontend: add the `kindToPath` helper and a small ref-link rendering piece used by both `RelationsTab` and Component's Provides/Consumes API section.
3. Frontend: wire `useEntityRowActivation` into `ChildTable` and `OwnedTable`.
4. Frontend: rebuild `TeamDetailPage` on `EntityDetailPage`.
5. No feature flag — this is a same-release UI/API change with no external consumers of the relations endpoint to stage against (internal SPA only).
6. Backend: extend `System`/`Component`/`Resource`/`API` `*SpecOut` with `ownerId`/`systemId` — additive, no migration, sourced from FK objects already resolved on the same code path.
7. Frontend: `railFields.tsx`'s Owner/System fields render via `RelationTargetLink` instead of plain `Label` text.

## Open Questions

- None outstanding — Options were decided during exploration (backend enrichment over client-side resolve; tabs-based Team layout over dividers-on-current-layout).
