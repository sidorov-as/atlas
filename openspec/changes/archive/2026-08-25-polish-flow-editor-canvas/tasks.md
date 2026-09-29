## 1. Dependency

- [x] 1.1 Add `@monaco-editor/react` to `frontend/package.json`, install, confirm it doesn't eagerly load into the main app bundle (only on the Flow edit route)

## 2. Shared editor support (`frontend/src/lib`)

- [x] 2.1 Add `frontend/src/lib/flowStepSchema.ts` — a JSON Schema describing `FlowStep[]` (`id` required string; `title`, `summary`, `entity_ref` optional strings; `next_step` as `{id, label}`; `next_steps` as an array of `{id, label}`), matching the `FlowStep` type in `frontend/src/lib/flowLayout.ts`
- [x] 2.2 Add `frontend/src/lib/monacoFlowTheme.ts` — two `monaco.editor.defineTheme()` definitions (light and dark) using Atlas's resolved Gravity UI token colors (reference `frontend/src/theme.css` and Gravity UI's default light/dark palettes), plus a helper to pick the theme based on the app's current `.g-root_theme_*` class
- [x] 2.3 Add a `findStepRange(text: string, stepId: string)` utility (text-scan for the step's `"id"` field, analogous to the reference playground's `findBlockPositionsMonaco`) for scroll-to-step navigation

## 3. `FlowGraph.tsx`: zoom toolbar + node-click hook

- [x] 3.1 Add a floating zoom toolbar component (zoom in, zoom out, fit-to-viewport) using `Button view="raised"` and `@gravity-ui/icons` (`MagnifierPlus`, `MagnifierMinus`, `SquareDashed`), calling `graph.zoom({scale})` / `graph.zoomTo('center')`, with zoom in/out disabled at `graph.cameraService.getCameraState().scaleMin`/`scaleMax`
- [x] 3.2 Render the toolbar inside `FlowGraph`'s canvas container; add `position: relative` to `.flow-graph` in `frontend/src/index.css` and floating-pill styles for the toolbar (absolutely positioned, vertically centered, seamless stacked buttons)
- [x] 3.3 Add an optional `onBlockClick?: (stepId: string) => void` prop to `FlowGraph`; wire it to the graph's block-selection/click behavior, calling it with the clicked step's `id`
- [x] 3.4 Confirm `FlowDetailPage.tsx` needs no changes — it renders `<FlowGraph>` without `onBlockClick` and automatically gains the zoom toolbar

## 4. `FlowFormPage.tsx`: editor swap and new controls

- [x] 4.1 Replace the `<TextArea>` for `steps` with the Monaco editor, configured with `language="json"`, the schema from 2.1, and the theme from 2.2
- [x] 4.2 Preserve existing live-update behavior: editor `onChange` continues to drive `parseSteps`/`useMemo` exactly as today — no staging/Apply step
- [x] 4.3 Surface Monaco's inline validation markers as visible errors in the existing error-display area (in addition to, not replacing, the current `jsonError` display)
- [x] 4.4 Wire `FlowGraph`'s `onBlockClick` (from 3.3) to call the editor's scroll-to-step (via `findStepRange` from 2.3), revealing and selecting that step's JSON block
- [x] 4.5 Add an "Add Step" button: appends `{ "id": "step-N", "title": "New step" }` (id generated to avoid colliding with existing step ids) to the parsed `steps`, updates the editor's text, and scrolls to the new step; disable while current JSON is invalid
- [x] 4.6 Add a JSON-panel collapse/expand toggle button that hides/shows the editor column and lets the preview pane take full width

## 5. Verification

- [x] 5.1 Manually confirm: typing invalid JSON shows an inline Monaco error without discarding the last valid diagram preview, and does not allow save
- [x] 5.2 Manually confirm: zoom in/out/fit-to-viewport work on both the Flow detail page (read-only) and the edit page's preview pane
- [x] 5.3 Manually confirm: clicking a step node in the edit page's diagram scrolls/selects that step's JSON block
- [x] 5.4 Manually confirm: "Add Step" appends a valid, unconnected step and the diagram shows it as a disconnected node
- [x] 5.5 Manually confirm: the editor panel collapse toggle works and the diagram expands to fill the freed width
- [x] 5.6 Manually confirm the editor is legible and correctly themed in both light and dark app themes (if dark mode is reachable in the running app)
- [x] 5.7 Confirm existing Flow create/edit/save flows (including server-side validation-error display on save) still work unchanged
