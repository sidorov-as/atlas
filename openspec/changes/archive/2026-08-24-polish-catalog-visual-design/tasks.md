## 1. Entity table width (CSS-only, ship first)

- [x] 1.1 Change `.entity-table-frame` in `frontend/src/index.css` from `display: inline-block` to `display: block; width: 100%` (drop `vertical-align: top`, no longer relevant on a block element).
- [x] 1.2 Visually check every `EntityTable` usage after the change: `EntityListPage.tsx` (Systems/Components/Resources/APIs lists), `TeamDetailPage.tsx`'s `OwnedTable`, `RelationsTab.tsx` if it renders one — confirm none relied on shrink-wrapped width.

## 2. Preview panel: icon-button instead of full-width CTA

- [x] 2.1 In `frontend/src/components/EntityListPage.tsx`'s `EntityPreviewPanel`, remove the bottom full-width "View full details" `Button` (lines ~156-158).
- [x] 2.2 Add an icon-button using `ArrowUpRightFromSquare` from `@gravity-ui/icons` in the header row, between the title and the existing close (`Xmark`) button, wired to the existing `onOpen` handler.
- [x] 2.3 Give the new icon-button an `aria-label` (e.g. "Open full details"), matching the existing close button's pattern.

## 3. Tag colors: fixed palette

- [x] 3.1 Define the preset palette (8-10 entries) as CSS custom-property pairs (`--tag-bg`, `--tag-fg` per preset key), covering light and dark theme variants, in `frontend/src/index.css` (or a new `tag-palette.css`).
- [x] 3.2 Update `.tag-label.g-label` (and the `--tag-color` wiring in `frontend/src/components/EntityDetailPage.tsx:95`) to apply both the background and text tokens for the tag's preset key, instead of only `background-color`.
- [x] 3.3 Update `frontend/src/lib/types.ts`'s `DEFAULT_TAG_COLOR` to the default palette key (e.g. `"gray"`) instead of a hex value; update any other frontend reference to the old hex default.
- [x] 3.4 Replace `TagColorEditor`'s `<input type="color">` in `frontend/src/pages/SettingsPage.tsx` with a swatch picker over the fixed palette.
- [x] 3.5 Update `backend/apps/catalog/models/tag.py`: change `DEFAULT_TAG_COLOR` to the default palette key and validate `Tag.color` against the fixed set of palette keys (model-level `choices` or serializer-level validation on the admin API).
- [x] 3.6 Write a data migration resetting every existing `Tag.color` value to the default palette key.
- [x] 3.7 Update/add backend tests covering: color update rejected for a non-palette value, new tags default to the palette default.
- [x] 3.8 Update/add frontend coverage (if the project has component/integration tests for Settings or tag rendering) for the swatch picker and paired bg/text rendering.

## 4. Team detail page: shell, markdown description, links rail

(Depends on Group 1 landing first — the section-header/table inline-layout bug is partly caused by the table-width bug.)

- [x] 4.1 Add `@gravity-ui/markdown-editor` to `frontend/package.json`; confirm its read-only viewer export and check its bundle-size impact (design.md Open Questions) before proceeding — fall back to a lighter renderer if disproportionate. **Resolution:** measured +330KB gzip (213KB→544KB, more than doubling the JS bundle) plus an `eval()` bundler warning from a transitive dependency for wiring in just the read-only viewer path (`YfmStaticView` + `@diplodoc/transform`) — confirmed disproportionate per the documented mitigation, so used the named fallback (`react-markdown`, +35KB gzip) instead.
- [x] 4.2 Extract (or otherwise share) the Links-rail rendering from `frontend/src/components/EntityDetailPage.tsx:158-171` so it can be reused by `TeamDetailPage.tsx` without duplicating the markup.
- [x] 4.3 Add a shared markdown-description component wrapping the `@gravity-ui/markdown-editor` viewer, and use it everywhere `metadata.description` is currently rendered as plain `<Text>` — `EntityDetailPage.tsx` and `TeamDetailPage.tsx`. (Built on `react-markdown` per 4.1's resolution.)
- [x] 4.4 Rebuild `frontend/src/pages/TeamDetailPage.tsx` on a two-column layout: center column with title, markdown description, then the existing Members/Systems/Components/Resources/APIs sections (unchanged in content/behavior); right `<aside>` rendering `group.metadata.links` via the shared Links-rail from 4.2.
- [x] 4.5 Confirm `group.metadata.links` is already returned by the Groups API (per `GroupEntity.metadata: Metadata`); if not actually populated end-to-end, check the backend serializer for Groups exposes `links` the same way other entity kinds do. **Resolution:** confirmed — `_group_out` uses the same shared `_metadata_out` as every other entity kind; no backend change needed.
- [x] 4.6 Visually verify against `design/visual_bugs/team-details-page.png` (bug fixed) and the layout pattern referenced in `design/visual_bugs/team-details-wanna-be.png` (center content / right link rail). Verified live in the running app (light + dark theme): tables render below headers, markdown description renders (bold/italic/links/lists), Links rail shows in the right aside.

## 5. Final checks

- [x] 5.1 Run frontend lint/typecheck and backend tests. `tsc -b` and `oxlint` clean (no new warnings); backend suite 54/54 passing.
- [x] 5.2 Manually walk all four areas end-to-end in the running app: Settings tag palette, an entity list's preview panel, a list/detail page's table width, and the Team detail page. Verified live via browser in both light and dark theme.
