## Why

The frontend has drifted from the approved design mockups (`design/services-list.png` and related). It runs Gravity UI's default theme instead of the Atlas brand colors, has no logo, uses no icons anywhere despite `@gravity-ui/icons` being installed, has a fixed non-collapsible sidebar, carries several rendering bugs (labels running into their values, tables with no visual frame, a search bar that wraps onto its own row), renders tags with no color, and navigates straight to a detail page on row click instead of showing a preview. These were tracked as nine separate observations but overlap enough in the touched files (`AppShell`, list pages, detail pages) that they're being scoped as one consolidated pass.

## What Changes

- Apply the Atlas brand palette (accent `#1c73e3`, secondary/background `#edf4fb`) via Gravity UI theme token overrides.
- Add `design/atlas-logo.svg` + "Atlas" wordmark to the sidebar header.
- Rebuild the sidebar navigation on Gravity UI's `AsideHeader` (new dependency: `@gravity-ui/navigation`): per-item icons, collapse/expand, and a new "Settings" nav entry.
- Fix inline label/value collapse rendering — adjacent Gravity `Text` elements render as unspaced inline spans (e.g. "Provides APIsNone") on the Component overview tab and the entity detail rail.
- Give every table a bordered card frame with visible row separation, applied consistently across all 5 current table usages (list pages, relations tab, system/team child tables) instead of per-page.
- Cap the `FilterBar` search input's width so it stays in the same row as the Owner/Type/Lifecycle filters instead of wrapping onto its own line.
- Add entity-type and owner icons to list-page table rows (Name and Owner columns).
- **New**: Tag color management — a `Tag` model (name + color), an admin API to list/create/update colors, and a Settings page to configure them; every tag render site picks up the configured color instead of a plain, uncolored `Label`.
- **New**: Right-side slide-over preview panel on all four entity list pages (Systems, Components, Resources, APIs) — clicking a row opens a panel with overview content and a link-through button to the full detail page, replacing today's immediate navigation on row click.

## Capabilities

### New Capabilities
- `tag-management`: Tag color configuration — a `Tag` model/table, an admin API to list/create/update tag colors, a Settings page in the web UI to manage them, and colored tag rendering everywhere tags are shown across the catalog.

### Modified Capabilities
- `catalog-web-ui`: adds a branded, collapsible navigation shell (logo, per-item icons, Settings entry) in place of the current plain-text fixed sidebar; changes list-page row-click behavior from an immediate navigate to opening a right-side preview panel with a link-through button to the full detail page; and fixes three rendering defects (label/value text collapsing together, tables with no card frame, search bar wrapping off the filter row) that fall short of the capability's existing list/detail page requirements.

## Impact

- **Frontend**: `AppShell.tsx` (rewritten on `AsideHeader`), `FilterBar.tsx`, `EntityListPage.tsx` (new preview panel), `ComponentDetailPage.tsx`, `EntityDetailPage.tsx`, `RelationsTab.tsx`, `SystemDetailPage.tsx`, `TeamDetailPage.tsx`, `TeamsListPage.tsx`, `ComponentsListPage.tsx` and sibling list pages (row icons), `main.tsx` / `index.css` (theme tokens), new `SettingsPage.tsx` + route.
- **New dependency**: `@gravity-ui/navigation`.
- **Backend**: new `Tag` model + migration in `apps/catalog`, new admin API endpoints for tag colors, `schemas.py` additions for tag color lookup in entity responses.
- **No ingestion changes**: tags remain plain strings in `catalog-info.yaml`; colors are an admin-managed overlay on top, consistent with the existing convention that admin-only concerns (like Group/User) stay outside YAML ingestion (see `[[0001-yaml-is-source-of-truth]]`).
