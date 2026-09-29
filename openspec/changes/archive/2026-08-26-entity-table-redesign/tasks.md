## 1. Shared table framing (visual)

- [x] 1.1 Update `.entity-table-frame` in `frontend/src/index.css`: remove `border` and `border-radius`, replace forced `width: 100%` behavior with a capped `max-width` (start at 1120px per design.md)
- [x] 1.2 Verify inert tables (`RelationsTab`, `SystemDetailPage`'s `ChildTable`, `TeamDetailPage`'s `OwnedTable`, `SettingsPage`'s tags table) render correctly with the new frame and no click/action regressions
- [x] 1.3 Verify `TeamDetailPage`'s four stacked `OwnedTable` sections read as separated by subheading + spacing, not as touching boxes

## 2. Row activation hook (click / double-click)

- [x] 2.1 Add `useEntityRowActivation` hook (design.md Decision 1/2): tracks `selectedId`, exposes `handleRowClick(item)` that immediately opens/retargets the preview panel and additionally navigates on a fast (<400ms) second click on the same row
- [x] 2.2 Wire the hook into `EntityListPage.tsx`, replacing its current inline `selectedId`/`onRowClick` logic
- [x] 2.3 Confirm existing Systems/Components/Resources/APIs preview-panel behavior (open, dismiss, link-through icon button) is unchanged after the swap

## 3. Row-level Edit/Remove actions

- [x] 3.1 Add a shared `entityRowActions` builder (design.md Decision 3) producing exactly two `TableAction` entries: Edit, Remove
- [x] 3.2 Wire `getRowActions`/`withTableActions` into `EntityListPage.tsx` for Systems/Components/Resources/APIs, gating actions to `[]` (no menu) on non-manual (YAML-managed) rows using the same predicate as `EntityDetailPage.tsx`'s `isManual`
- [x] 3.3 Confirm clicking Edit/Remove does not also trigger the row's preview-panel-opening click handler

## 4. Flow and Team rail content

- [x] 4.1 Add `flowRailFields` and `teamRailFields` to `frontend/src/lib/railFields.tsx`
- [x] 4.2 Update `FlowsListPage.tsx`: replace navigate-on-click with the shared row-activation hook + preview panel (using `flowRailFields`), add unconditional Edit/Remove row actions
- [x] 4.3 Update `TeamsListPage.tsx`: replace navigate-on-click with the shared row-activation hook + preview panel (using `teamRailFields`). **Scope change**: Edit/Remove row actions dropped — Groups have no edit/create/delete API or route anywhere in the app (managed only via Django admin); design.md wrongly assumed Team has the same CRUD as Flow. Revisit if/when Group gains a frontend CRUD.

## 5. Settings page section header

- [x] 5.1 Add a "Tag colors" `Text variant="subheader-2"` section heading above the tags table in `SettingsPage.tsx`
- [x] 5.2 Move the existing tag-specific description text to sit under the new subheading instead of under the page's `header-1` title

## 6. Verification

- [x] 6.1 Manually exercise all six list pages (Systems, Components, Resources, APIs, Flows, Teams): single click opens/retargets the panel with no visible delay, fast second click on the open row navigates to its detail page — verified live via browser automation (Components, Flows, Teams checked directly; Systems/Resources/APIs share the same `EntityListPage`/hook code path). Simulated two clicks 150ms apart on the same row → navigates; 600ms apart → panel re-opens, no navigation.
- [x] 6.2 Manually verify a YAML-managed System/Component/Resource/API row shows no row-actions control, while a manual one shows Edit/Remove — manual-row case verified live (Backend component shows Edit/Remove). No YAML-ingested entity exists in this dev environment's seed data to exercise the hidden-menu case live; verified instead by code inspection that `EntityListPage.tsx`'s `item.ingestedFrom ? [] : entityRowActions(...)` gate is the same predicate as `EntityDetailPage.tsx`'s `isManual = !ingestedFrom`.
- [x] 6.3 Manually verify Flow rows always show Edit/Remove (Team rows: no row actions — see 4.3 scope change) — verified live: Flow row's "..." menu shows exactly Edit/Remove; Team rows have no "..." control at all.
- [x] 6.4 Visual pass across all list/detail pages against `design/visual_bugs/table.png` for spacing/density; retune the max-width constant if needed — checked live: borderless tables, capped-width container, TeamDetailPage's four stacked `OwnedTable` sections read as separated by subheading + spacing (not touching boxes). 1120px constant reads fine against current seed data; left as-is.
- [x] 6.5 Run `frontend` test suite and linter (`npm test`, `npm run lint`) and fix any regressions — lint clean (pre-existing warnings only, none new); `tsc -b && vite build` clean; `npm test` has one pre-existing failure in `flowLayout.test.ts` (ELK layout spacing option mismatch), unrelated to this change and untouched by any of its tasks — not a regression, left as-is

## 7. Card-width layout (FilterBar + table + aside alignment)

Found during visual QA against `design/visual_bugs/table.png`: in the reference, search/filters, the "Add" button, and the table all share one fixed-width column, so "Add" sits flush with the table's right edge. In `EntityListPage.tsx`/`FlowsListPage.tsx` today, `FilterBar` is a full-width, uncapped row (only the table itself is capped via `.entity-table-frame`'s `max-width: 1120px`), so "Add" (pushed right via `marginLeft: 'auto'`) drifts to the window edge instead of the table's edge. The same uncapped-wrapper issue also pushes the row-click preview panel (`aside`) away from the table instead of letting it sit immediately beside it.

- [x] 7.1 Wrap title/FilterBar/table/pagination in a single container sharing one `max-width: 1120px` (matching `.entity-table-frame`) in both `EntityListPage.tsx` and `FlowsListPage.tsx`, so "Add" aligns with the table's right edge
- [x] 7.2 Apply that same `max-width: 1120px` to the table's flex wrapper itself (currently `flex: 1, minWidth: 0` with no cap of its own), so `flex-grow` stops stretching it past the table's capped width — this lets the preview panel `aside` sit immediately after the table instead of drifting toward the window edge when open
- [x] 7.3 Switch the FilterBar row's Add-button alignment from `marginLeft: 'auto'` on the button to `justifyContent: 'space-between'` on the row (matching `temp/landing/src/components/UISamples/TablePreview/TablePreview.tsx`'s reference pattern); verify no regression on narrow/wrapped layouts
- [x] 7.4 Visual check against `design/visual_bugs/table.png`: "Add" button flush with the table's right edge; with the preview panel open, `aside` sits directly beside the table with no gap — on `EntityListPage`-backed pages (Systems/Components/Resources/APIs) and `FlowsListPage` — verified live: "Add Component"/"Add Flow" now sit at the capped container's right edge instead of drifting to the window edge, and the preview panel sits immediately beside the table when open. Verified no wrap regression at 480px width too.
