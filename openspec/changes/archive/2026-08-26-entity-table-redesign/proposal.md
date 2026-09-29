## Why

Every table in the catalog frontend is wrapped in its own bordered, rounded card and forced to fill 100% of its column, so pages with more than one table (e.g. a Team's Systems/Components/Resources/APIs sections) read as a stack of boxes squeezed against each other rather than one page, and a single table can stretch edge-to-edge on wide screens. Click behavior is also inconsistent: Systems/Components/Resources/APIs open a right-side preview panel on click, while Flows and Teams instead navigate away immediately with no preview and no way to get details without leaving the list. Neither list offers a quick per-row Edit/Remove action — both require opening the entity first.

## What Changes

- Remove the border and border-radius from every table's frame; separate stacked tables on the same page with spacing and their existing section subheaders instead of a card boundary.
- **BREAKING**: Replace the "fill full width of its containing column" table-width rule with a capped max-width, so a table stops growing past a comfortable reading width instead of always spanning its column.
- Add a two-item row context-actions menu (Edit, Remove) to every entity list table: Systems, Components, Resources, APIs, Flows, and Teams. For Systems/Components/Resources/APIs, Edit/Remove are hidden on rows for YAML-managed (non-manual) entities, matching the existing read-only rule on their detail pages. Flow and Team rows always show Edit/Remove (neither entity kind can be YAML-managed).
- Extend the existing right-side preview panel (currently Systems/Components/Resources/APIs only) to the Flows and Teams list pages, including new summary content for each.
- Add double-click-to-navigate on every entity list table row: a second, fast click on a row that's already open in the preview panel navigates to that entity's full detail page, without adding any delay to the existing single-click-opens-panel behavior.
- Reflect the same borderless/spacing visual treatment on every other table in the app (System/Team detail-page sub-tables, the Relations tab, the Settings tags table), with no change to their existing click behavior (they stay inert — no panel, no row actions).
- Settings page: add a "Tag colors" section subheader above the tags table, moving the page's current tag-specific description under it, so the page-level heading stays generic as more settings sections are added later.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `catalog-web-ui`: "Consistent entity table width" changes from fill-column-width to a capped max-width; "Entity list preview panel" extends to the Teams list page and gains double-click-to-navigate on the row itself; new requirement for row-level Edit/Remove actions (gated by manual/YAML-managed status) on Systems/Components/Resources/APIs/Teams; table framing (border/radius removal, spacing-based separation) becomes a stated requirement instead of an unspecified implementation detail.
- `flow-management`: the Flows list page gains the same right-side preview panel, double-click-to-navigate, and row-level Edit/Remove actions as the four entity list pages.
- `tag-management`: the Settings page's tag color table sits under a new "Tag colors" section subheader rather than being the page's only, unlabeled content.

## Impact

- `frontend/src/components/EntityTable.tsx` and `frontend/src/index.css` (`.entity-table-frame`): drop border/radius, cap width.
- `frontend/src/components/EntityListPage.tsx`: add row actions; generalize/extract its rail + click-vs-double-click logic so it can be reused by Flows/Teams instead of being EntityListPage-only.
- `frontend/src/pages/FlowsListPage.tsx`, `frontend/src/pages/TeamsListPage.tsx`: switch from navigate-on-click to preview-panel-on-click + double-click-to-navigate; add row actions.
- `frontend/src/lib/railFields.tsx`: add summary fields for Flow and Team (Group), alongside the existing System/Component/Resource/API ones.
- `frontend/src/components/EntityDetailPage.tsx` (`isManual` gate): reused/mirrored for row-level action gating on Systems/Components/Resources/APIs.
- `frontend/src/pages/SettingsPage.tsx`: add the "Tag colors" section subheader.
- No changes to `frontend/src/components/RelationsTab.tsx`, `SystemDetailPage.tsx`'s `ChildTable`, or `TeamDetailPage.tsx`'s `OwnedTable` beyond the shared visual restyle — their click/action behavior is explicitly unchanged.
