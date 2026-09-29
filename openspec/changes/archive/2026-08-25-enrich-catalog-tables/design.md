## Context

Every entity list table today (`frontend/src/components/EntityListPage.tsx` for Systems/Components/Resources/APIs, plus `TeamDetailPage.tsx`'s `OwnedTable` and `SystemDetailPage.tsx`'s owned-entity tables, all built on the shared `frontend/src/components/EntityTable.tsx`) renders Type and Lifecycle as bare text (`ComponentsListPage.tsx:24-25`) and never renders tags at all. List data is fetched in full and rendered client-side: `fetchList: (filters: ListFilters) => Promise<T[]>` (`EntityListPage.tsx:18`, backed by `componentsApi.list()` etc. in `frontend/src/lib/entities.ts:69-125`), and the backend list controllers (`backend/apps/catalog/api/views.py`, e.g. `ComponentListController.get` at line 330) return a bare `list[XOut]` with no paging.

Two things discovered during exploration materially simplify this change:

1. **Tags are a Postgres array column, not a join table.** `CatalogEntity.tags` (`backend/apps/catalog/models/base.py:19`) is `ArrayField(CharField)` — a plain list of tag-name strings on every System/Component/Resource/API row. The `Tag` model (`backend/apps/catalog/models/tag.py`) only exists to hold each tag name's *color*, auto-created via `ensure_tags_exist()`. So tag filtering with OR semantics is a single Postgres `ArrayField.overlap` lookup (`tags__overlap=[...]`) — no join, no subquery.
2. **The framework already ships an unused pagination helper.** `dmr.pagination` (`backend/.venv/.../dmr/pagination.py`) defines `Page`/`Paginated` dataclasses meant to wrap `django.core.paginator.Paginator`, but nothing in `apps/catalog` uses them yet. The `dmr` query parser already supports list-typed query params via `MultiValueDict.getlist` (`dmr/internal/django.py:105`) when a `Query` model field is typed `list[str]`, which covers `?tags=a&tags=b` for free.

## Goals / Non-Goals

**Goals:**
- Type and Lifecycle render as colored `Label` badges in every table, using Gravity UI's native `theme` values — no new CSS palette (contrast with the Tag rework, which needed one).
- Every `EntityTable`-backed table (list pages + owned-entity sub-tables) gains a Tags column and a tag filter (OR semantics).
- Every list endpoint and every `EntityTable` consumer gains real, server-driven pagination via Gravity UI's `Pagination` component.

**Non-Goals:**
- Type and Lifecycle do *not* become dynamic/admin-configurable (explicitly decided during exploration) — no new models, no migrations, no Settings UI for either.
- Lifecycle does not expand beyond `Component` (its only existing home today) to System/Resource/API.
- No change to the `Tag` model, its palette, or its Settings-page editor (`polish-catalog-visual-design`, already shipped).
- No cursor-based pagination — offset/page-number pagination only, matching Gravity UI's `Pagination` contract (`page`, `pageSize`, `total`).

## Decisions

### 1. Type/Lifecycle badges: static frontend lookup tables, no backend change

Both stay exactly what they are today — fixed Django `choices` per model (`Component.TYPE_CHOICES`/`LIFECYCLE_CHOICES` at `component.py:13-23`, `Resource.TYPE_CHOICES` at `resource.py:11-17`, `Api.TYPE_CHOICES` at `api.py:11-16`). Add plain TS lookup objects, one per kind, mapping each existing choice value to a Gravity UI `Label` `theme`:

```ts
// frontend/src/lib/badges.ts
export const LIFECYCLE_THEME: Record<string, LabelProps['theme']> = {
  production: 'success',
  experimental: 'warning',
  deprecated: 'unknown',
}
export const COMPONENT_TYPE_THEME: Record<string, LabelProps['theme']> = {
  service: 'info', website: 'utility', library: 'normal', worker: 'clear',
}
// ...RESOURCE_TYPE_THEME, API_TYPE_THEME similarly, drawn from the
// remaining non-semantic themes (danger/normal/info/utility/clear)
```
Table columns replace `template: (item) => item.spec.type` with a small `<Label theme={...}>{value}</Label>` cell. Rejected alternative: reuse the Tag palette's custom-CSS-variable approach (`--tag-bg`/`--tag-fg` from `polish-catalog-visual-design`) — unnecessary since Gravity's built-in themes already cover the semantics needed (success/warning/unknown for lifecycle; the remaining themes are enough for each kind's small type set), and reusing built-in themes means zero new CSS.

### 2. Tags in tables and tag filtering: read the existing `tags: string[]` field, no new join

- **Column**: add a `tags` `TableColumnConfig` to each list page rendering `item.metadata.tags.map(tag => <Label theme="clear" className={tagPresetClass(tag)}>...)`, reusing the exact rendering already built for the detail page (`EntityDetailPage.tsx:112-117`) via a small shared helper rather than duplicating the class-name logic.
- **Filter**: extend `ListFilters` (`frontend/src/lib/entities.ts:14-19`, backend `schemas.py:353-357`) with `tags?: string[]`. Backend: `filters.py` gains `filter_by_tags_overlap(queryset, tags)` using `queryset.filter(tags__overlap=tags)` when non-empty — a direct Postgres array-overlap lookup, giving OR semantics natively, no new helper abstraction needed beyond this one function.
- **Filter UI**: `FilterBar.tsx` currently only renders single-select `Select` (`filter.value[0]`). Add a second config variant, `MultiSelectFilterConfig` (`value: string[]`, `onChange: (values: string[]) => void`), rendered via the same `Select` component with `multiple` (already supported per `Select/types.d.ts:91`) — additive, doesn't change the existing single-select `SelectFilterConfig` path used by Owner/Type/Lifecycle filters.
- **Options source**: the multi-select's option list comes from `tagsApi.list()` (`entities.ts:132-133`), already fetched for the Settings page — reused here, not refetched per table.

### 3. Pagination: adopt `dmr.pagination.Paginated`, page/pageSize/total contract end-to-end

- **Backend**: each list controller (`SystemListController.get`, `ComponentListController.get`, `ResourceListController.get`, `ApiListController.get` — `views.py:207,330,444,556`) adds `page: int = 1` and `page_size: int = 20` to `ListFilters`, applies existing filters to build the `QuerySet` as today, then wraps it in `django.core.paginator.Paginator(queryset, page_size).page(page)` and returns `dmr.pagination.Paginated[XOut]` (`count`, `num_pages`, `per_page`, `page.number`, `page.object_list`) instead of a bare list. Component/Resource/API lists additionally apply the existing `filter_by_system` to a `system` query parameter, so System Detail never paginates a client-side filtered global result. This is a **breaking response-shape change** (proposal's Impact section) — the frontend is the only consumer, updated in the same change.
- **Frontend**: `fetchList` signatures move from `Promise<T[]>` to `Promise<Paginated<T>>` (a matching TS type mirroring the backend dataclass). `EntityListPage` (`EntityListPage.tsx`) and `TeamDetailPage`'s `OwnedTable`/`SystemDetailPage`'s owned-entity tables all gain local `page`/`pageSize` state, pass them into `fetchList`, and render Gravity UI's `<Pagination page={page} pageSize={pageSize} total={data.count} onUpdate={(p, ps) => {...}} pageSizeOptions={[10,20,50]} showInput />` below the `EntityTable`.
- **Filter changes reset to page 1**: changing search/owner/type/lifecycle/tags resets `page` to 1 (existing precedent: `EntityListPage.tsx`'s `filters` `useMemo` already recomputes on every filter change — the new page-reset effect hooks off the same dependency array, minus `page`/`pageSize` themselves).
- Rejected alternative: infinite "load more" (cursor-based). Explicitly rejected during exploration in favor of a classic numbered pager, and `dmr.pagination.Paginated` (offset/page-number shaped) is already sitting in the framework unused — using it is less work than building a cursor scheme from scratch.

## Risks / Trade-offs

- **[Risk] Response-shape break is silent for any non-frontend consumer** (scripts, another service) hitting `/api/{systems,components,resources,apis}/` expecting a bare array → **Mitigation**: none currently known to exist outside the frontend (confirmed via `Impact` review); flag in the PR description as a breaking API change regardless.
- **[Risk] `tags__overlap` on an unindexed `ArrayField` could get slow on large tables** → **Mitigation**: not a concern at current catalog scale; a GIN index on `tags` is a one-line follow-up (`ArrayField(..., db_index=True)` migration) if it becomes one — out of scope here since it doesn't change behavior, only performance.
- **[Risk] Duplicated `{value → theme}` maps per entity kind drift from the backend `choices` if someone adds a new Type value later** → **Mitigation**: same drift risk already exists today for `TYPE_OPTIONS`/`LIFECYCLE_OPTIONS` arrays hardcoded per list page (`ComponentsListPage.tsx:10-11`); not a regression, just an existing pattern this change extends rather than fixes.
- **[Trade-off] `page_size` max is unbounded server-side unless explicitly capped** — a caller could request `page_size=100000` and defeat pagination's purpose. Cap it in the `ListFilters` Pydantic field (e.g. `page_size: int = Field(default=20, le=100)`).

## Migration Plan

No data migration (no schema change — `page`/`page_size`/`tags` are query params, not columns; Type/Lifecycle color maps are frontend-only constants). Deploy is a single atomic backend+frontend release since the response-shape change is breaking between them; no phased rollout needed given the frontend is the sole consumer.

## Open Questions

None outstanding — all prior open questions (traffic-light mapping, Type dynamism, Lifecycle scope, pagination style, tag-filter semantics, owned-entity-table scope) were resolved during exploration and are reflected in the Decisions above.
