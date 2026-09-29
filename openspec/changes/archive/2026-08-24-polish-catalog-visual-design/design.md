## Context

Four independent visual issues were identified against the current frontend (`frontend/src/`), each traced to a specific root cause:

1. **Tag colors** — `TagColorEditor` (`pages/SettingsPage.tsx`) uses a raw `<input type="color">`; the chosen hex is stored on `Tag.color` (`backend/apps/catalog/models/tag.py`, `CharField(max_length=32)`) and applied via `--tag-color` (`components/EntityDetailPage.tsx:95`) through `index.css:19-22`:
   ```css
   .tag-label.g-label { background-color: var(--tag-color); box-shadow: none; }
   ```
   Only `background-color` is set — text color is whatever `Label`'s `theme="clear"` default is, so arbitrary background choices can produce unreadable text. Gravity UI's own `Label` ships only 8 fixed themes (`normal, info, success, warning, danger, utility, unknown, clear`), too few to distinguish many tags the way Notion's ~10 status-color presets do.

2. **EntityPreviewPanel CTA** — `EntityListPage.tsx`'s `EntityPreviewPanel` (lines ~109-161) has a header row (title + close button) and a separate full-width "View full details" button at the bottom, both wired to the same `onOpen`/`onClose` handlers already passed in.

3. **Table width** — `EntityTable.tsx` wraps `Table` in `.entity-table-frame`, and `index.css:8-15` sets `display: inline-block`, which shrink-wraps the frame to its content instead of filling its container. This is why tables of different length end up different widths across sections on the same page.

4. **Team detail page** — `TeamDetailPage.tsx` is hand-built rather than reusing `EntityDetailPage.tsx` (the shell every other entity's detail page uses, with a right rail, tabs, and a Links section). Its section headers (`<Text variant="subheader-2">`, an inline element) sit directly next to `<EntityTable>` (inline-block per issue 3), so the table renders on the same line as its header instead of below it — the visible bug in `design/visual_bugs/team-details-page.png`. Separately, `GroupEntity.metadata.links` already exists in the data model (same `LinkOut[]` shape `EntityDetailPage`'s Links rail already renders) but `TeamDetailPage` never reads it, and `description` is shown as plain text everywhere in the app (no markdown rendering exists yet anywhere, and `@gravity-ui/markdown-editor` isn't a dependency).

## Goals / Non-Goals

**Goals:**
- Guarantee readable tag text on any configured tag background.
- Match the Gravity UI-idiomatic pattern of a small link-through affordance in the preview panel header instead of a large secondary CTA.
- Make table width consistent and container-driven rather than content-driven.
- Bring `TeamDetailPage` onto the same two-column shell pattern as the other entity detail pages, surfacing the team's links and rendering its description as markdown.

**Non-Goals:**
- Fixed per-column widths within a table (e.g. `Name: 40%, Owner: 20%`). Only the table frame's overall width is fixed to its container; column sizing stays content-driven.
- A WYSIWYG markdown editing experience. `@gravity-ui/markdown-editor` is added for its read-only viewer only; `EntityFormShell.tsx`'s description field stays a plain textarea in this change.
- Restructuring `TeamDetailPage`'s owned-entity sections into tabs. They move into the shell's center column as stacked sections, unchanged in form.
- Migrating existing tag hex values to their closest preset automatically (see Decision 1).

## Decisions

### 1. Tag colors: fixed named palette, stored as a palette key

Replace the color `<input>` with a swatch picker offering a fixed set of presets (e.g. `gray, red, orange, yellow, green, blue, purple, pink` — 8 initially, matching Gravity UI's own theme count while being purpose-built for tags rather than semantic status). Each preset is a **pair** of CSS custom properties (`--tag-bg`, `--tag-fg`), defined once in `index.css` (or a small `tag-palette.css`) with light/dark-theme variants, so contrast is guaranteed by construction rather than computed at runtime.

`Tag.color` keeps its existing `CharField(max_length=32)` shape but now stores a palette key (`"yellow"`) instead of a hex string — no schema migration needed, only a data migration. The frontend maps the key to its CSS class/vars; unknown/legacy keys fall back to the existing `DEFAULT_TAG_COLOR` preset the same way missing tags already do.

**Existing rows**: reset every `Tag.color` to the default preset in a data migration rather than attempting an automatic nearest-color mapping. Nearest-color mapping is lossy and would silently pick colors nobody chose; a reset is honest about "this needs re-picking" and Settings already surfaces every tag for an admin to revisit. Admins are notified via the changelog/release notes, not in-app (out of scope here).

**Alternative considered**: keep storing raw hex but validate server-side against an allowed set. Rejected — it's the same constraint with a less legible stored value (`"#F5A623"` vs `"yellow"`), and complicates adding/renaming presets later (every stored hex would need updating instead of just the CSS token).

### 2. Preview panel: icon-button in the header row

Order in the header row becomes: title → `ArrowUpRightFromSquare` icon-button (`onOpen`) → close icon-button (`onClose`, existing `Xmark`). Keeping "open" nearer the title and "close" at the far right matches the read order (act on the thing named, dismiss the panel last) and keeps both icon-buttons visually grouped as panel-level controls rather than separating them across the panel.

**Alternative considered**: icon-button flush right, before the close button, with more spacing from the title. Rejected as a first pass — no strong signal either way from the codebase; revisit visually during implementation if the grouped placement looks cramped at `size="s"`.

### 3. Table width: block-level frame, content-driven columns

`.entity-table-frame` changes from `display: inline-block` to `display: block; width: 100%`. Every current usage already sits inside a block-level or flex (`flex: 1; min-width: 0`) container (`EntityListPage.tsx:91`, `TeamDetailPage.tsx`'s `OwnedTable`), so this fills exactly the space already allocated to it — no container-level changes needed beyond this one rule.

Column widths are intentionally left content-driven (not addressed in this change): the reported problem was tables of inconsistent *overall* width across sections on one page, which `width: 100%` fully resolves. Fixed-percentage columns are a separate, larger change (touching every `columns` config across five pages) with no reported problem to justify it yet.

### 4. Team detail page: adopt the two-column shell pattern, markdown viewer for description

Rebuild `TeamDetailPage.tsx` to follow `EntityDetailPage.tsx`'s layout: a center column (title, markdown-rendered description, then the existing Members/Systems/Components/Resources/APIs sections, unchanged in content) and a right `<aside>` rendering `group.metadata.links` via the same Links-section markup `EntityDetailPage.tsx:158-171` already uses. No new component is introduced solely for this — either the two pages share a small `LinksRail` extraction, or `TeamDetailPage` duplicates the ~12-line block; prefer extraction since it's now used in two places (implementer's call at `tasks.md` time, not a spec-level requirement).

Markdown rendering: add `@gravity-ui/markdown-editor` and use its read-only view export for `description` in **both** `TeamDetailPage` and `EntityDetailPage` (the field is shared across all entity kinds — fixing only Team would leave System/Component/Resource/API showing raw markdown source). The editing form (`EntityFormShell.tsx`) is untouched; `description` stays a plain `TextArea`-backed field there. Switching the edit experience to `@gravity-ui/markdown-editor`'s full WYSIWYG mode is deferred (see `tasks.md`) since it's a heavier bundle addition and a separate UX decision (inline WYSIWYG vs. a markdown textarea with a preview toggle) that doesn't block shipping readable rendering.

**Alternative considered**: a lighter markdown renderer (e.g. `react-markdown`) instead of `@gravity-ui/markdown-editor`'s viewer, to avoid pulling in an editor-oriented package for read-only display. Not chosen as the default here because the user specifically pointed at `@gravity-ui/markdown-editor` and staying within the Gravity UI ecosystem keeps styling/theme consistency (tokens, dark mode) automatic. Flagged as an open question below — worth a quick bundle-size check before committing.

## Risks / Trade-offs

- **BREAKING**: existing tag colors are reset, so every tag will momentarily show the default preset color until an admin revisits Settings → Mitigation: this is a one-time, low-stakes visual reset (not data loss), and Settings already lists every tag needing attention.
- [`@gravity-ui/markdown-editor` is a large package even in viewer mode] → Mitigation: verify actual bundle-size impact before merging (see Open Questions); fall back to a lighter markdown renderer if it's disproportionate for read-only display.
- [Removing `inline-block` from `.entity-table-frame` could affect a table usage not yet audited] → Mitigation: the change is a single shared CSS rule; grep all `EntityTable` usages (five list/detail pages) and visually check each after the change, since none currently rely on shrink-wrapped width intentionally (it was always the bug, never a feature).
- [Fixed tag palette may not offer enough distinct colors as tag vocabulary grows] → Mitigation: palette size (8-10) is a CSS-only constant; adding a preset later is a small, additive change.

## Migration Plan

1. Ship the CSS-only fixes (table width, preview panel button) first — no backend or data involved, zero migration risk.
2. Ship the tag palette change together with its data migration (reset `Tag.color` to default) in one deploy, since the frontend and backend must agree on valid `color` values simultaneously.
3. Ship the Team detail page rebuild + markdown dependency last, since it's the largest surface change and easiest to verify independently once the table-width fix (a dependency, see proposal) has already landed.
4. No rollback complexity beyond a standard revert: the `Tag.color` data migration is a reset to a known default, safely re-runnable.

## Open Questions

- ~~Confirm `@gravity-ui/markdown-editor`'s viewer-only bundle-size cost is acceptable before adding it as a dependency; fall back to a lighter renderer (e.g. `react-markdown` styled with existing `--g-` tokens) if not.~~ **Resolved during implementation (tasks.md 4.1):** measured +330KB gzip and an `eval()` bundler warning for `@gravity-ui/markdown-editor`'s read-only path — disproportionate; shipped with `react-markdown` (+35KB gzip) instead, styled via `.markdown-description` in `index.css`.
- Exact preset list/names for the tag palette (8 vs 10 colors, naming) — pick during implementation by sampling Gravity UI's own token palette for visually distinct, theme-aware options.
- Preview panel icon-button spacing/grouping (Decision 2's alternative) — confirm visually once implemented; low-stakes, easy to adjust.
