## Context

Six pages render an entity list table today, in three different shapes:

- **`EntityListPage`** (Systems/Components/Resources/APIs, via `frontend/src/components/EntityListPage.tsx`): `FilterBar` + `EntityTable` + `Pagination`, with `onRowClick` setting `selectedId` and rendering an inline `EntityPreviewPanel` (the right-side rail) next to the table. No row actions, no double-click.
- **`FlowsListPage`** / **`TeamsListPage`**: their own hand-rolled shell (`FilterBar` + `EntityTable`, no rail, `TeamsListPage` has no pagination or filters at all), with `onRowClick` calling `navigate()` straight to the detail page.
- **Inert sub-tables**: `RelationsTab`, `SystemDetailPage`'s local `ChildTable`, `TeamDetailPage`'s local `OwnedTable`, and `SettingsPage`'s tags table — plain `EntityTable`, no `onRowClick` at all.

All six sit inside `.entity-table-frame` (`frontend/src/index.css`): a bordered, rounded, `width: 100%` box. `catalog-web-ui`'s "Consistent entity table width" requirement currently mandates that full-width fill; this change reverses it to a capped max-width, and removes the border/radius entirely.

Rail content today (`frontend/src/lib/railFields.tsx`) exists only for System/Component/Resource/API, shared between each entity's detail-page rail and its list-page preview panel. Flow and Team have no rail content yet.

`Table` from `@gravity-ui/uikit` (confirmed by reading its `.d.ts`) exposes `onRowClick`, `onRowMouseEnter/Leave/Down` — no `onRowDoubleClick`. Row actions come from the `withTableActions` HOC (`getRowActions`), which already `stopPropagation()`s its own clicks, so an actions-menu click will not also fire `onRowClick`.

## Goals / Non-Goals

**Goals:**
- One shared implementation of "click opens/updates the preview panel, a fast second click on the already-open row navigates to the detail page" used identically by all six list pages.
- One shared implementation of the row-actions menu (Edit, Remove), with a gating hook for entity kinds that can be YAML-managed.
- A single visual treatment (no border/radius, capped width, spacing-based separation) applied via `EntityTable`/`.entity-table-frame` so all tables — interactive and inert — pick it up automatically.
- Zero added latency on the common single-click path.

**Non-Goals:**
- No change to the inert tables' behavior (`RelationsTab`, `ChildTable`, `OwnedTable`, Settings tags table) beyond the shared visual restyle.
- No redesign of the preview panel's own layout/content beyond adding Flow and Team summaries.
- No new Settings sections beyond adding the "Tag colors" subheader — the page stays a single route.
- Not attempting pixel parity with `temp/landing`'s `TablePreview` (a different project using `@gravity-ui/page-constructor`); it's a visual reference for spacing/density, not a component to port.

## Decisions

### 1. Extract a shared `useEntityRowActivation` hook instead of generalizing `EntityListPage` itself

`EntityListPage` currently bundles filtering, pagination, *and* the rail together, and is generic over a `railFields`/`rowTo` pair — but `FlowsListPage` and `TeamsListPage` don't share its filter/pagination shape closely enough to be swallowed into it wholesale (`TeamsListPage` has neither today). Instead, pull just the activation logic into a small hook:

```ts
function useEntityRowActivation<T>(getId: (item: T) => string, onOpenDetail: (item: T) => void) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const lastClickRef = useRef<{ id: string; time: number } | null>(null)

  function handleRowClick(item: T) {
    const id = getId(item)
    const now = Date.now()
    const isFastSecondClick = lastClickRef.current?.id === id && now - lastClickRef.current.time < 400
    lastClickRef.current = { id, time: now }
    setSelectedId(id) // always fires immediately — no debounce on the panel-open path
    if (isFastSecondClick) onOpenDetail(item)
  }

  return { selectedId, setSelectedId, handleRowClick }
}
```

`EntityListPage`, `FlowsListPage`, and `TeamsListPage` each call this hook and render `EntityPreviewPanel` (already generic over `railFields`) themselves. This is more repetition across the three pages than a single mega-component, but each page's surrounding shell (filters, pagination, presence/absence thereof) stays exactly as different as it already legitimately is — the hook only unifies the one piece of logic that must be identical everywhere: click-vs-fast-second-click.

**Alternative considered**: generalize `EntityListPage` to also cover Flows/Teams. Rejected — `TeamsListPage` has no filters/pagination today and forcing it through `EntityListPage`'s filter-bar-shaped props would mean threading empty/no-op configs through, and `EntityListPage` also carries selection/removal wiring the other two don't have yet.

### 2. Double-click is additive, never delays the single click

The hook above sets `selectedId` unconditionally on every click, then separately checks whether this click qualifies as a fast second click on the same row to *also* call `onOpenDetail`. This means:
- First click on any row: panel opens/retargets immediately, no `setTimeout`.
- Second fast click on the same, already-open row: panel is (harmlessly) re-set to the same id, and navigation additionally fires.

**Alternative considered**: the classic debounce (delay the single-click action ~250-400ms to see if a second click follows). Rejected — it taxes every single click, which is the dominant case, to support the rarer double-click.

**Threshold**: 400ms (browser dblclick default is ~500ms per OS double-click settings; 400ms is comfortably inside the common range without being so long that two deliberate, unrelated single clicks on the same row get misread as a double-click).

### 3. Row actions: one `getRowActions` builder shared across the six pages, parameterized by an `isManual` predicate

```ts
function entityRowActions<T>(
  item: T,
  { onEdit, onRemove, disabled }: { onEdit: () => void; onRemove: () => void; disabled?: boolean },
): TableAction<T>[] {
  return [
    { text: 'Edit', icon: <Pencil />, theme: 'normal', disabled, handler: onEdit },
    { text: 'Remove', icon: <TrashBin />, theme: 'danger', disabled, handler: onRemove },
  ]
}
```

For Systems/Components/Resources/APIs, `disabled` is derived the same way `EntityDetailPage.tsx`'s `isManual` is (`!ingestedFrom`) — reusing that exact predicate rather than re-deriving it, so list-row actions and detail-page actions can never disagree about whether an entity is editable. Flow and Group have no `ingestedFrom` field (verified in `frontend/src/lib/types.ts`), so their rows pass `disabled: false` unconditionally.

**Alternative considered**: hide the actions menu entirely for non-manual rows instead of disabling it. Rejected in favor of matching the proposal's stated behavior ("hidden... on rows") — actually: proposal says "hidden", so implementation should omit the actions column content (return `[]` / no menu) for non-manual rows rather than showing a disabled menu. Design follows the proposal: `getRowActions` returns `[]` when non-manual, which `withTableActions` renders as no menu for that row.

### 4. Visual: `.entity-table-frame` drops border/radius, switches `width: 100%` to `max-width`

```css
.entity-table-frame {
  display: block;
  width: 100%;       /* still shrink-wraps within its column... */
  max-width: 1120px; /* ...but never grows past this */
}
```

1120px is a starting value (roughly: comfortable multi-column table + room for the widest current column set, e.g. Component's Name/Type/Lifecycle/Owner/System/Tags/Updated). It's a single constant in one place, easy to retune after visual QA. Stacked tables (`TeamDetailPage`'s four `OwnedTable`s) separate purely via their existing `Text variant="subheader-2"` title + `marginTop: 24` spacing — no new wrapper needed there.

This directly reverses `catalog-web-ui`'s current "Consistent entity table width" requirement (fill-column-width); the spec delta marks this as the requirement's replacement, not an addition.

### 5. Flow and Team rail content: new functions alongside the existing ones in `railFields.tsx`

```ts
export function flowRailFields(flow: FlowEntity): RailField[] {
  return [
    { label: 'System', value: <Label>{refName(flow.system)}</Label> },
    { label: 'Steps', value: String(flow.steps.length) },
  ]
}

export function teamRailFields(group: GroupEntity): RailField[] {
  return [
    { label: 'Type', value: <Label>{group.spec.type}</Label> },
    { label: 'Members', value: String(group.spec.members.length) },
  ]
}
```

Kept in the same file as the existing four, for the same reason the file's header comment already states: list-page preview and detail-page rail must never disagree on what "the summary" is. (Flow/Team detail pages don't currently render an "About" rail the way System/Component/Resource/API detail pages do — that's out of scope here; these two functions are only consumed by the new list-page preview panels for now.)

### 6. Settings page section header

Straightforward content change, no new pattern: `SettingsPage.tsx` gets a `Text variant="subheader-2"` ("Tag colors") between the page's `header-1` and the table, matching the subheader style `OwnedTable`/`TeamDetailPage` already use for sectioning. The existing description text moves from page-level to just below this subheader.

## Risks / Trade-offs

- **[Risk] 400ms double-click threshold feels arbitrary and may need tuning per real usage** → Single named constant, easy to adjust; not user-configurable, so no migration concern either way.
- **[Risk] Three pages (`EntityListPage`, `FlowsListPage`, `TeamsListPage`) each still own their own shell, so the hook extraction doesn't fully eliminate duplication** → Accepted per Decision 1; revisit a fuller merge only if a fourth divergent shell shows up.
- **[Risk] Fixed 1120px max-width may look cramped on ultra-wide monitors or too tight for tables with many columns (e.g. Components' 7 columns)** → Single constant; adjust after visual QA against real data, no architectural cost to changing it later.
- **[Risk] Reversing "Consistent entity table width" is a stated BREAKING spec change** → It only affects rendered width, no data/API shape; no migration beyond the CSS/spec edit itself.

## Migration Plan

No data migration. Rollout is a single frontend deploy:
1. Land the shared hook + row-actions builder + CSS change together (they're only meaningful combined).
2. Land Flow/Team rail fields + `FlowsListPage`/`TeamsListPage` switch to the shared hook.
3. Land the Settings subheader (independent, can go in the same deploy).
Rollback is reverting the deploy; no persisted state depends on any of this.

## Open Questions

- Exact `max-width` pixel value (1120px above is a starting point) — settle during visual QA against real seeded data rather than in the abstract.
- Whether Flow/Team detail pages should eventually gain their own "About" rail (matching System/Component/Resource/API) so `flowRailFields`/`teamRailFields` serve double duty like the existing four — not needed for this change, flagged for a future one.
