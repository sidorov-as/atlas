## Context

Atlas wraps the app in Gravity UI's `<ThemeProvider theme="system">`, so the shell, tables, and forms already switch with the OS. Gaps:

- C4 diagrams are rendered by PlantUML on the backend and delivered as SVG/PNG via `<img>`. Their palette lives in `_ATLAS_PLANTUML_TAGS` and `_ATLAS_PLANTUML_RELATIONSHIP_TAGS` in `c4.py`; the viewer container forces `background: '#fff'`. The frontend cannot recolor an image, so the palette must be chosen at render time. There is no server-side diagram cache.
- Rendering options already travel as query parameters (`layout`, `show_title`, `show_legend`, ...), built into `DiagramRenderingSettings` at three call sites in `api/views.py` (entity diagram, landscape, custom view) and validated in `api/schemas.py`.
- Flows and ER diagrams are `@xyflow/react` canvases already styled with `--g-*` tokens, but their image export hard-codes `'#ffffff'`.
- Redoc (OpenAPI) and `@asyncapi/react-component` (AsyncAPI) ship light styles only; the AsyncAPI stylesheet is global.
- The Monaco code editor already picks a light/dark theme from the `g-root_theme_dark` body class.

## Goals / Non-Goals

**Goals:**
- User-selectable light/dark/system with browser-only persistence and a footer switcher.
- Dark C4 diagrams from the backend, with exports matching what is on screen.
- Flow and ER canvases and exports, Redoc, and AsyncAPI follow the theme.
- No behavior change for consumers that do not pass `theme` (MCP and any other).

**Non-Goals:**
- Docs site theming, per-user server-side theme storage, custom palettes beyond light/dark, a `theme` field on saved Views, MCP changes.

## Decisions

**1. A single theme context owns the mode; Gravity's ThemeProvider consumes it.**
A `ThemeContext` in `core/frontend/src/lib/` (next to `SessionContext`) holds `mode` (`light|dark|system`), exposes `resolved` (`light|dark`), and persists `mode` in `localStorage` under a versioned key (matching the existing `atlas.c4-diagram-preferences.v1` style). `App.tsx` passes `mode` straight to `<ThemeProvider theme={mode}>`; Gravity already resolves `system`. `resolved` is derived from `mode` plus a `prefers-color-scheme` media query listener. Exported through `package.json` like other shared libs so plugins can use it.
*Alternative:* read `document.body.classList` everywhere (as `codeEditorTheme.ts` does). Rejected for new code because it cannot trigger React re-renders on change; the Monaco helper can be moved to the context later but is left working as is.

**2. No-flash bootstrap in `index.html`.**
A tiny inline script reads the stored mode, resolves it, and sets the document background and color-scheme before React mounts. Storage errors are swallowed and fall back to system. The script duplicates the storage key and validation by necessity; a unit test pins the key so the two cannot drift.

**3. Switcher in the `AsideHeader` footer.**
Rendered in `renderFooter` above User and Log out. Expanded: a three-option segmented control (sun / moon / auto icons). Compact: one icon button cycling system → light → dark. This reuses the existing footer slot and needs no layout change, unlike the content header where global search currently sits.

**4. C4 dark palette is selected on the backend by a `theme` setting.**
Add `theme: Literal["light","dark"] = "light"` to `DiagramRenderingSettings`; add it to the query schema and pass it at all three call sites. The tag tuples become per-theme palettes, selected in `diagram_payload`. Tag identifiers, stereotypes, shapes, line styles, thickness, and legend text stay shared; only colors differ, so light output is byte-identical to today's. Dark colors are chosen for contrast against the dark background while keeping each role's hue family.
*Alternative A:* CSS `filter: invert()` on the `<img>`. Rejected: distorts semantic colors and leaves downloads light.
*Alternative B:* leave diagrams on a white card. Rejected by the product decision; kept only as a fallback if the spike fails.

**5. Background and text come from diagram-level options, with a spike first.**
Diagram background and default text color need diagram-wide control, not just tag colors. The renderer library offers `SetSketchStyle(bg_color, font_color, ...)` and boundary styles (`BoundaryStyle`, `SystemBoundaryStyle`, ...) via `render_options.styles`. Before writing the palette, a spike confirms (a) the validated payload accepts these options, (b) `SetSketchStyle` colors without enabling a hand-drawn look (no `LAYOUT_AS_SKETCH`), (c) title, legend, and boundary text become legible, and (d) PNG output matches SVG. If `SetSketchStyle` is unsuitable, fall back to emitting equivalent PlantUML `skinparam` lines through whatever extension point the renderer exposes, or, failing that, to explicit per-element font colors plus a solid background rectangle.

**6. Frontend sends the resolved theme, not the mode.**
`diagramUrls.ts` and `customView.ts` accept `theme` alongside rendering options and always send the resolved value (`light` or `dark`); `system` never reaches the backend. Because the URL changes, the existing `<img>` reload and re-fit path handles the switch. The same builders produce the download URLs, so SVG/PNG exports match the screen with no extra code. The default of `light` stays only as a backend default for callers that omit it.

**7. Export background from the live token.**
For flows and ER, a non-transparent export reads the computed value of `--g-color-base-background` from the viewport element at export time and passes it as `backgroundColor`, replacing `'#ffffff'`. Reading at export time means it follows the theme and any brand override without a lookup table. Transparent export is untouched.

**8. xyflow follows the theme via `colorMode`.**
Pass the resolved theme as `colorMode` to `<ReactFlow>` so built-in controls, minimap, and attribution follow it; verify the `Background` grid color against tokens and override if needed.

**9. API viewers: Redoc through its theme option, AsyncAPI through scoped CSS.**
Redoc receives a theme object derived from the resolved theme (colors for background, text, and code blocks); it remounts on change since Redoc reads options once. For AsyncAPI, a stylesheet scoped under the theme class overrides its global light CSS variables/colors; both viewers are lazy-loaded already, so the cost is paid only when opened. Visual verification in a browser is part of the task list because these libraries are the least predictable.

## Risks / Trade-offs

- [PlantUML sketch-style macro changes the look beyond colors] → Spike first (decision 5); fallback paths listed there.
- [Dark palette loses semantic distinctions or has weak contrast] → Pair every light role with a dark counterpart in one table, review all roles in a rendered "kitchen sink" diagram (every tag and relationship kind, boundary, legend, title) in both themes, and add backend tests that assert every tag has both palettes.
- [Light output drifts] → Tests assert the default (no `theme`) payload equals the current light payload, so MCP and other consumers are unaffected.
- [Theme duplicated between `index.html` script and the context] → Shared storage key pinned by a test; fallback behavior identical.
- [AsyncAPI global CSS bleeds into the app in dark mode] → Scope overrides under the viewer's container and test that surrounding UI is unchanged.
- [Redoc remount on theme change loses scroll position] → Accepted; theme switches are rare, and the viewer re-renders from the already loaded spec.
- [Browser-only storage means the theme differs across devices] → Accepted by product decision.

## Open Questions

- Whether to migrate `codeEditorTheme.ts` onto the new context now or leave it reading the body class; default is leave as is.

## Resolved by the spike

- `SetSketchStyle` validates but is unusable: the vendored C4-PlantUML applies `SET_SKETCH_STYLE` colors only together with `LAYOUT_AS_SKETCH` (hand-drawn look), so the background stayed white. Boundary styles (`BoundaryStyle`, `SystemBoundaryStyle`) work through `render_options.styles`.
- Chosen mechanism (the skinparam fallback of decision 5): `render` inserts plain PlantUML lines after the tag definitions, before the layout macro: `skinparam backgroundColor`, `titleFontColor`, `defaultFontColor`, legend skinparams, and the `$LEGEND_TITLE_COLOR`/`$LEGEND_FONT_COLOR` variables the legend reads at `SHOW_LEGEND` time. SVG and PNG both come out dark and match.
- The theme travels from `diagram_payload` to `render` as a reserved top-level payload key `atlas_theme`, present only for dark (so the light payload is unchanged) and removed before validation.
- Dark colors (background, font, border): selected `#12355f/#e3f2fd/#64b5f6`; component `#16341c/#c8e6c9/#81c784`; database `#3b2f10/#ffe082/#ffb300`; queue `#34173d/#e1bee7/#ba68c8`; endpoint `#102a47/#bbdefb/#64b5f6`; external endpoint `#2b2d31/#d0d0d0/#9e9e9e`; person `#47260a/#ffcc80/#fb8c00`. Relationships (text, line): synchronous `#90caf9/#64b5f6`; asynchronous `#ce93d8/#ba68c8`; data access `#bcaaa4/#a1887f`; manual and derived `#b0bec5/#90a4ae`. Diagram background `#221d22` (Gravity dark base), text `#e6e6e6`, boundary border `#9aa0a6`.
