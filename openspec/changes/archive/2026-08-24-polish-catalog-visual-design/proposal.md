## Why

Several UI surfaces added ad hoc since the initial catalog-web-ui/tag-management builds have drifted from the Gravity UI patterns they were meant to follow: tag colors are picked freely and can render unreadable text, the entity preview panel carries an oversized call-to-action, entity tables shrink-wrap to their content instead of filling their column, and the Team detail page — built without the shared detail-page shell — visibly breaks (tables float inline next to their section headers) and shows plain-text descriptions with no way to link out to team resources. Fixing these now, together, removes a set of known layout inconsistencies before more pages are built on top of the same patterns.

## What Changes

- Replace the free-form tag color `<input type="color">` in Settings with a fixed palette of ~8-10 preset colors, each a paired background+text token guaranteed to be readable together. **BREAKING**: `Tag.color` stops accepting arbitrary hex; existing tag rows are reset to the default preset and must be recolored by an admin from the new palette.
- Replace the `EntityPreviewPanel`'s full-width "View full details" button with a small `ArrowUpRightFromSquare` icon-button placed next to the entity title in the panel's header row.
- Make `.entity-table-frame` a full-width block (`display: block; width: 100%`) instead of `display: inline-block`, so every table fills its column consistently instead of shrink-wrapping to its content.
- Rebuild `TeamDetailPage` on the same two-column shell pattern used by System/Component/Resource/API detail pages: center column shows the (now markdown-rendered) description followed by the Members/Systems/Components/Resources/APIs sections; right rail shows the team's `metadata.links` as clickable link-outs (mirroring the existing Links section in `EntityDetailPage`).
- Render `description` as markdown (via `react-markdown`) everywhere it's shown — Team detail and the shared `EntityDetailPage` — instead of as plain text. `@gravity-ui/markdown-editor`'s read-only viewer path was measured at +330KB gzip for this alone (its dependency tree ships the full ProseMirror/CodeMirror editor engine even for read-only rendering); design.md's own mitigation named `react-markdown` (+35KB gzip) as the fallback for exactly this case. Editing forms are unchanged in this change (still a plain textarea); switching the edit form to a WYSIWYG markdown editor is an explicitly deferred follow-up.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `tag-management`: tag colors come from a fixed named palette instead of an arbitrary hex value, and the palette guarantees readable text-on-background contrast for every preset.
- `catalog-web-ui`: the entity list preview panel's link-through action moves from a full-width button to a header icon-button; entity tables render at a consistent full-column width instead of content-driven width; the Teams (Groups) detail page gains a two-column layout with a markdown-rendered description and a Links rail, matching the other entity detail pages.

## Impact

- Frontend: `frontend/src/pages/SettingsPage.tsx`, `frontend/src/components/EntityListPage.tsx`, `frontend/src/index.css`, `frontend/src/components/EntityTable.tsx`, `frontend/src/pages/TeamDetailPage.tsx`, `frontend/src/components/EntityDetailPage.tsx`, `frontend/src/lib/types.ts`.
- New frontend dependency: `react-markdown` (see design.md Decision 4 / tasks.md 4.1 for why this replaced the originally-proposed `@gravity-ui/markdown-editor`).
- Backend: `backend/apps/catalog/models/tag.py` (`Tag.color` becomes a constrained palette key) plus a data migration resetting existing rows to the default preset.
- No changes to entity data models beyond `Tag.color`'s accepted values; `GroupEntity.metadata.links` is already present and only newly rendered.
