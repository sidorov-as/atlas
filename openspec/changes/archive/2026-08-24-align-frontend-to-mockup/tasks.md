## 1. Brand theme

- [x] 1.1 Add a theme stylesheet overriding Gravity's brand-relevant `--g-color-*` tokens to accent `#1c73e3` / secondary `#edf4fb`, imported in `main.tsx` after `@gravity-ui/uikit/styles/styles.css`
- [x] 1.2 Visually spot-check buttons, active nav state, and selection highlighting against `design/services-list.png`

## 2. Rendering bug fixes

- [x] 2.1 Fix label/value inline-collapse in `ComponentDetailPage.tsx`'s Overview tab (`Text` subheader immediately followed by `RefList`) by giving the label its own block-level line with margin
- [x] 2.2 Fix the same pattern in `EntityDetailPage.tsx`'s rail fields (`railFields.map`)
- [x] 2.3 Grep the frontend for the same adjacent-`Text` pattern elsewhere and fix any other instance found
- [x] 2.4 Add a shared card-frame + row-separation style and apply it to all 5 `Table` usages: `EntityListPage.tsx`, `RelationsTab.tsx`, `SystemDetailPage.tsx`'s `ChildTable`, `TeamDetailPage.tsx`'s `OwnedTable`, `TeamsListPage.tsx`
- [x] 2.5 Cap `FilterBar.tsx`'s `TextInput` width so it stays in the same row as the Owner/Type/Lifecycle `Select` filters instead of wrapping; verify against `design/visual_bugs/search-bar.png`

## 3. Navigation shell

- [x] 3.1 Add `@gravity-ui/navigation` as a dependency, pinned to a version compatible with `@gravity-ui/uikit ^7.48.1`
- [x] 3.2 Confirm the icon mapping table from `design.md` (nav items, Component `spec.type`, owner) against `@gravity-ui/icons`' actual exports, adjusting names as needed
- [x] 3.3 Rewrite `AppShell.tsx` on `AsideHeader`: logo (`design/atlas-logo.svg`) + "Atlas" wordmark in the header slot, one item per current `NAV_ITEMS` entry with its mapped icon, active-route highlighting equivalent to the current `NavLink` behavior
- [x] 3.4 Add collapse/expand behavior via `AsideHeader`'s built-in support; verify it persists/behaves consistently across route changes
- [x] 3.5 Add a "Settings" nav entry (route wired up in task 6.2)
- [x] 3.6 Manually QA every existing nav item (Systems/Components/Resources/APIs/Teams) still routes correctly after the rewrite

## 4. List row icons

- [x] 4.1 Add entity-type icon to the Name column's `template` in `ComponentsListPage.tsx` (and sibling list pages where a type exists)
- [x] 4.2 Add an owner icon to `EntityListPage.tsx`'s `ownerCell` (or its per-page column usage)
- [x] 4.3 Visually compare against `design/services-list.png`'s Name/Owner columns

## 5. Backend: Tag model

- [x] 5.1 Add a `Tag` model (`name` unique, `color`) to `apps/catalog`, with a default color constant for auto-created rows
- [x] 5.2 Generate and apply the migration
- [x] 5.3 `get_or_create` a `Tag` row for every tag string wherever an entity's `tags` array is written: the manual-entity PATCH path (`apps/catalog/api/views.py`) and the ingestion upsert path (`apps/ingestion/upsert.py`)
- [x] 5.4 Add an admin API to list all `Tag`s (color + name) and update a `Tag`'s color, restricted to `is_superuser` for writes, following the existing `catalog-auth` superuser pattern; reads follow the existing "any authenticated user" rule
- [x] 5.5 Extend `schemas.py` / entity read responses so tag color is available wherever `tags` are returned

## 6. Frontend: Settings page and colored tags

- [x] 6.1 Build a `SettingsPage.tsx` listing all tags with an inline color editor, calling the new admin API
- [x] 6.2 Wire the `/settings` route (guarded like other authenticated routes) and link it from the new sidebar Settings entry
- [x] 6.3 Update every tag-rendering site (starting with `EntityDetailPage.tsx`'s tag `Label` list) to look up and apply each tag's configured color as the `Label` background
- [x] 6.4 Verify a tag with no explicit color falls back to the default color rather than rendering unstyled

## 7. Entity list preview panel

- [x] 7.1 Extract each detail page's `railFields` construction (or an equivalent summary field list) into a form reusable by both the full detail page and the preview panel, per entity kind
- [x] 7.2 Add `selectedId` state to `EntityListPage.tsx`; change `onRowClick` to set it instead of calling `navigate()` directly
- [x] 7.3 Render a fixed-width `<aside>` preview panel alongside the table (flex layout) when a row is selected, showing the entity's title, key fields, and description
- [x] 7.4 Add a link-through button in the panel that navigates to the full detail page (reusing the existing `rowTo` prop)
- [x] 7.5 Add a close control that clears `selectedId` without navigating
- [x] 7.6 Confirm this works uniformly across all four list pages (Systems, Components, Resources, APIs) since they share `EntityListPage`

## 8. Verification

- [x] 8.1 Run the frontend through its existing test suite / linter after all changes
- [x] 8.2 Manually walk every list and detail page against the relevant `design/` screenshot (`services-list.png`, `service-details.png`) and the three `design/visual_bugs/` screenshots, confirming each is resolved
- [x] 8.3 Confirm no change to `catalog-info.yaml` ingestion shape — existing ingestion tests still pass unmodified
