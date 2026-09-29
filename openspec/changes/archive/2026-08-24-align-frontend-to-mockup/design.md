## Context

The frontend (React + Gravity UI `^7.48.1`) was built functionally correct against the `catalog-web-ui` spec but was never visually reconciled with the approved mockups in `design/`. Nine gaps were catalogued by walking the mockups against the running app: no brand theme, no logo, no icons anywhere (despite `@gravity-ui/icons` being an installed, unused dependency), a fixed non-collapsible sidebar, three rendering bugs, uncolored tags, and list rows that hard-navigate instead of previewing. This design covers all nine as one change, since most touch the same files (`AppShell`, the shared `EntityListPage`/`FilterBar`/`Table` usages).

## Goals / Non-Goals

**Goals:**
- Bring the running app visually and behaviorally in line with `design/services-list.png` and the visual-bug screenshots in `design/visual_bugs/`.
- Fix the three rendering bugs at their shared root cause (not per-page patches), since they recur across 5+ call sites.
- Add tag color configuration as a real, if minimal, feature: model, API, Settings page.
- Add the row-click preview panel to all four entity list pages uniformly, since they already share `EntityListPage`.

**Non-Goals:**
- No change to `catalog-info.yaml` shape or ingestion behavior — tags stay plain strings from YAML's point of view; color is a backend-managed overlay, not a manifest field.
- No general theming system / dark mode — one fixed brand palette.
- No per-Group or per-user tag color overrides — colors are global.
- No redesign of the detail pages' own tab content (Overview/Relations/C4 Diagram) beyond the two known label/value bugs.

## Decisions

### 1. Theme via Gravity CSS custom-property overrides, not a custom design system
Gravity UI is themed through `--g-color-*` CSS custom properties. We add a small stylesheet (loaded after `@gravity-ui/uikit/styles/styles.css` in `main.tsx`) that overrides the brand-relevant tokens (`--g-color-base-brand`, `--g-color-base-selection`, etc.) to `#1c73e3` / `#edf4fb`. Rejected alternative: forking/replacing Gravity's styles wholesale — far more work for no benefit, since the app otherwise wants Gravity's defaults.

### 2. Sidebar rebuilt on `@gravity-ui/navigation`'s `AsideHeader`, replacing the hand-rolled `AppShell` nav
The current `AppShell.tsx` is a hand-rolled flex/div with no collapse behavior. Gravity's own answer for a collapsible, icon-bearing sidebar is `AsideHeader` from the separate `@gravity-ui/navigation` package (not currently installed). Adopting it gets logo slot, per-item icons, and collapse/expand together, rather than hand-building collapse state and animation ourselves. Trade-off: a new dependency and a rewrite of how `NAV_ITEMS` maps to `AsideHeader`'s item model (including translating the current `NavLink`-based active-route highlighting). Considered alternative: add collapse state to the existing hand-rolled nav — rejected, it would leave us hand-maintaining what Gravity already ships, and drifts further from "using Gravity as intended."

### 3. Icon mapping is an explicit, reviewable table — not inferred
There's no existing icon convention in the codebase. This design proposes (for implementation-time confirmation, not further debate) using `@gravity-ui/icons`:
- Nav items: Systems→`Layers`, Components→`Cube`, Resources→`Database`, APIs→`Plug`, Teams→`Persons`, Settings→`Gear`.
- Component `spec.type`: `service`→`Cube`, `website`→`Compass`/`Globe`, `library`→`Book`, `worker`→`ArrowsRotateRight`.
- Owner cell: a generic `Shield` (or Group `type`-specific icon if that's cheap once the mapping exists), matching the mockup's shield glyph next to "Identity Team".
This keeps the icon choice a small, inspectable diff rather than a judgment call buried in a component.

### 4. Shared table styling via one wrapper, not five inline fixes
The "no background in table" bug and the "search bar wraps" bug are both instances of one class of problem: shared UI primitives (`Table`, `FilterBar`) styled ad hoc per call site. Fix: a single `EntityTable` style (card frame, row separation) applied by the shared components (`EntityListPage`, `RelationsTab`, and the two page-local `ChildTable`/`OwnedTable` helpers), and a width cap on `FilterBar`'s `TextInput`. This directly targets the risk raised during exploration — five call sites drifting out of sync — by fixing it in the shared layer.

### 5. Label/value bug fixed at the pattern level
Root cause: Gravity's `Text` renders as an inline `<span>`; two adjacent `Text` elements with no block wrapper or margin render flush against each other. Fix applies to both known sites (`ComponentDetailPage`'s Overview tab fields, `EntityDetailPage`'s rail fields) by giving the label its own block-level line with margin-bottom, not by special-casing the specific "Provides APIs" instance. Implementation should grep for the same `<Text ...>{label}</Text>` immediately followed by another `Text`/component pattern elsewhere before considering this done, since it's a latent bug class, not a single typo.

### 6. Preview panel: inline side panel, not a modal/overlay
The mockup shows the list at reduced width with the panel occupying the right ~30%, list still fully visible and interactive-looking underneath — not a dimmed modal overlay. Implementation: `EntityListPage` gains `selectedId` state; on row click, sets `selectedId` instead of navigating; renders the table and (conditionally) a fixed-width `<aside>` preview panel side-by-side via flex, mirroring `EntityDetailPage`'s existing rail pattern. The panel shows a trimmed summary (title, key rail fields, description) plus a button that calls the existing `rowTo`/navigate. Full tab content (Relations, C4 Diagram) stays exclusive to the full detail page — the panel is a preview, not a duplicate of the detail page.

### 7. Tag color model: new `Tag` table in `apps/catalog`, auto-created on write, superuser-managed
`Tag(name unique, color)` lives alongside the other catalog models. Rather than requiring an admin to pre-register every tag before it can be colored, `Tag` rows are `get_or_create`d wherever an entity's `tags` array is written — both the manual-entity PATCH path (`apps/catalog/api/views.py`) and the ingestion upsert path (`apps/ingestion/upsert.py`) — defaulting new rows to one fixed neutral color. This means the Settings page always reflects exactly the tags currently in use, with nothing to manually seed. Color *writes* (the Settings page's PATCH) require `is_superuser`, consistent with the existing `catalog-auth` ownership model, since tag color is global config with no natural owning Group. Read access follows the existing "any authenticated user" rule.

## Risks / Trade-offs

- **New dependency (`@gravity-ui/navigation`)** → version-mismatch risk against `@gravity-ui/uikit ^7.48.1`. Mitigation: pin to the version documented as compatible with that uikit major version before starting the `AsideHeader` migration.
- **`AsideHeader` rewrite touches every authenticated route's chrome at once** → high blast radius for a single PR. Mitigation: land it behind manual QA of every nav item before merging; no incremental rollout path exists for a shell component, so this should be reviewed as its own logical unit even within the one change.
- **Auto-creating `Tag` rows on every write** → a typo'd tag string becomes a permanent-looking row in the Settings list. Mitigation: acceptable for v1 (matches "tags are freeform strings" today); an unused `Tag` row is cosmetic clutter, not a data-integrity problem, and can be pruned later if it matters.
- **Preview panel duplicates some rail-field rendering logic from `EntityDetailPage`** → risk of the two drifting apart. Mitigation: factor the rail-field list (label/value pairs) into a small shared piece both consume, rather than copy-pasting per entity kind.

## Migration Plan

1. Theme tokens + logo + label/value + table + search-bar fixes (independent, no new deps) — low risk, land first.
2. `@gravity-ui/navigation` dependency + `AsideHeader` rewrite of `AppShell` (includes nav icons, collapse, Settings entry) — do this once step 1's icon mapping is confirmed, since `AsideHeader` items need icons immediately.
3. Backend `Tag` model + migration + admin API, gated behind existing superuser check.
4. Frontend Settings page (tag color list/edit) + colored `Label` rendering wired into existing tag-display sites.
5. Preview panel added to `EntityListPage`, applied to all four list pages since they share the component.

No data migration risk: `Tag` is additive (new table), and existing `tags` `ArrayField` values are untouched — the `get_or_create` backfill happens lazily on next write, not via a bulk migration. No rollback concerns beyond a standard revert, since nothing here changes persisted entity shapes.

## Open Questions

- Exact hex values beyond the two given (`#1c73e3` accent, `#edf4fb` secondary) — e.g. what the collapsed-sidebar background, hover states, and status colors (Production/Staging labels in the mockup) should be. Proposed: derive from Gravity's standard token set using the two given colors as `base-brand`/`base-selection`, confirm visually against the mockup during implementation rather than pre-specifying every token here.
- Default color for auto-created `Tag` rows — proposed: a neutral gray consistent with Gravity's default `Label` styling, final value TBD at implementation time.
- Whether the preview panel's "trimmed summary" field set should differ per entity kind (System vs. API) or use one generic field list — proposed: reuse each detail page's existing `railFields` construction so the panel and the full page never disagree on what "the summary" is.
