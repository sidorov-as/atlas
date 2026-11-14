## 1. C4 spike (blocks the palette work)

- [x] 1.1 Render a kitchen-sink diagram (every element tag, every relationship tag, boundary, title, legend) through the backend with `SetSketchStyle` and boundary styles in `render_options`; confirm the payload validates and the result is legible with no hand-drawn look, in both SVG and PNG
- [x] 1.2 Record the chosen mechanism (or the fallback from design decision 5) and the dark color table in `design.md` Open Questions, then resolve them

## 2. C4 backend theme option

- [x] 2.1 Add `theme: Literal["light","dark"] = "light"` to `DiagramRenderingSettings` in `c4.py`
- [x] 2.2 Split `_ATLAS_PLANTUML_TAGS` and `_ATLAS_PLANTUML_RELATIONSHIP_TAGS` into per-theme palettes sharing identifiers, stereotypes, shapes, line styles, and legend text; keep the light palette values unchanged
- [x] 2.3 Apply the dark diagram-level background, text, title, legend, and boundary styling in `render_options_payload`/`diagram_payload` per the spike outcome
- [x] 2.4 Add `theme` to the diagram query schema in `api/schemas.py` (reject invalid values) and pass it into `DiagramRenderingSettings` at the three call sites in `api/views.py` (entity, landscape, custom view preview/saved)
- [x] 2.5 Ensure `custom_view.py` builds with the settings theme and that `theme` is not part of saved View settings or their validation

## 3. C4 backend tests

- [x] 3.1 Test that a request without `theme` yields a payload identical to the current light payload
- [x] 3.2 Test that `theme=dark` selects the dark palette for every tag and relationship tag, and that every tag has both a light and a dark entry
- [x] 3.3 Test that an invalid `theme` is rejected before rendering on entity, landscape, and custom view endpoints
- [x] 3.4 Test dark SVG, PNG, and download requests, and deterministic output for repeated dark requests
- [x] 3.5 Extend the custom view contract and endpoint tests for `theme` on preview and saved-view endpoints, and that saved settings contain no theme

## 4. Theme context, switcher, and bootstrap

- [x] 4.1 Create `core/frontend/src/lib/ThemeContext.tsx` with `mode`, `resolved`, `setMode`, a versioned `localStorage` key, validation, try/catch fallback to `system`, and a `prefers-color-scheme` listener; export it in `core/frontend/package.json`
- [x] 4.2 Wire `App.tsx` to wrap with the theme provider and pass `mode` to Gravity's `ThemeProvider`
- [x] 4.3 Add the inline no-flash script to `core/frontend/index.html` using the same key and validation
- [x] 4.4 Add the theme switcher to `AppShell.tsx` footer: segmented control when expanded, single cycling icon button when compact
- [x] 4.5 Tests for the context (default system, stored value, invalid value, throwing storage, system change, persistence), the switcher (expanded and compact), and a test pinning the storage key shared with `index.html`

## 5. C4 frontend

- [x] 5.1 Add `theme` to `diagramUrls.ts` and `customView.ts` URL builders, always sending the resolved `light`/`dark`, including download URLs
- [x] 5.2 Update `DiagramTab.tsx`, `SystemMapPage.tsx`, `ViewDetailPage.tsx`, and `ViewEditorPage.tsx` to pass the resolved theme; remove the forced `background: '#fff'` so the backdrop follows the theme
- [x] 5.3 Ensure a theme change reloads the image and refits it to the viewport
- [x] 5.4 Update `DiagramTab`, `DiagramViewerFetch`, and view tests for the theme parameter, download URLs, and backdrop

## 6. Flows and ER

- [x] 6.1 Pass the resolved theme as `colorMode` to `<ReactFlow>` in the flows and database-schema plugins and verify the grid and controls against tokens
- [x] 6.2 Replace `'#ffffff'` in `FlowGraph.tsx` and `ErDiagramView.tsx` export with the computed `--g-color-base-background` at export time; keep transparent export unchanged
- [x] 6.3 Verify flow and ER node and edge styling in dark and fix any remaining hard-coded colors (for example box shadows)
- [x] 6.4 Tests for export background in light and dark and transparent export

## 7. API documentation viewers

- [x] 7.1 Pass a theme-derived configuration to `RedocStandalone` in `OpenApiViewer.tsx` and remount on theme change
- [x] 7.2 Add scoped dark overrides for the AsyncAPI viewer and confirm they do not affect surrounding UI
- [x] 7.3 Verify both viewers in dark with real specs in a browser; fix unreadable regions

## 8. Verification and docs

- [ ] 8.1 Walk every main page in light, dark, and system modes (catalog lists, entity detail, flows, ER, System Map and views, API docs, settings, login) and fix remaining light-only surfaces
- [x] 8.2 Run backend and frontend test suites, lint, and type checks
- [x] 8.3 Update the README or feature notes under `docs-site` only if they describe theming; leave the docs site's own theme untouched
