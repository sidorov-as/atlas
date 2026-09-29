## Context

Two read-only diagram views — the ER Diagram tab (`ErDiagramView.tsx`, database-schema plugin) and the read-only Flow page's diagram (`FlowGraph.tsx`, flows plugin) — each render a pair of "SVG"/"PNG" toolbar buttons. Both call `html-to-image`'s `toSvg`/`toPng` directly on the canvas's root element with no options object, so both today already capture a transparent background (no `backgroundColor` is passed) and always include the xyflow dot-grid `<Background/>`, since it renders unconditionally inside `<ReactFlow>`.

The two implementations are already independent, near-duplicate code (`inlineEdgeStrokeStyles` in `ErDiagramView.tsx` vs. `inlineEdgeExportStyles` in `FlowGraph.tsx` — same technique, different names), not a shared abstraction. The editable Flow canvas (`FlowCanvasEditor.tsx`) has its own, unrelated `FlowCanvasSettings` popup (Autolayout switch + layout-engine `SegmentedRadioGroup`) that establishes the Button-anchor + `Popup` pattern this change reuses, but has no export control and is out of scope.

## Goals / Non-Goals

**Goals:**
- One "Export" entry point per read-only diagram view, replacing the two-button pattern, offering format (SVG/PNG), transparent-vs-white background, and grid-dots-included-vs-excluded.
- Grid exclusion and background choice affect only the exported file — the live canvas is visually unaffected at every point in the interaction, including mid-export.
- Format and both checkboxes always reset to their defaults on popup open; nothing persists across exports or page loads.

**Non-Goals:**
- No shared popup component or shared React state between the ER Diagram and Flow implementations — each keeps its own popup, its own `handleExport`, and its own edge-style-inlining helper, to leave room for view-specific export options later.
- No change to the editable Flow canvas (`FlowCanvasEditor.tsx`) — it gets no export control.
- No new persistence (local storage, backend) for export preferences — this explicitly stays session-local and resets every time.

## Decisions

### Grid suppression via direct DOM mutation, not React state

**Decision**: Locate the grid element (`.react-flow__background`, xyflow's class for its `<Background/>` output) directly via `element.querySelector` inside the existing capture helper, toggle `style.display = 'none'` immediately before calling `toSvg`/`toPng` when the grid checkbox is unchecked, and restore `style.display = ''` in a `finally` block right after — mirroring the exact pattern `inlineEdgeStrokeStyles`/`inlineEdgeExportStyles` already use for edge stroke styles (mutate live DOM in place, capture, restore in `finally`).

**Why over the alternative** (drive grid visibility through the actual `showGrid` component state / conditionally render `<Background/>`): that approach would make the live viewer's grid genuinely disappear while the popup is set to "no grid" or during the async capture, since React needs an actual re-render (and thus a tick of delay) before `toSvg`/`toPng` can read the updated DOM. Direct, synchronous DOM mutation avoids both the live-view flicker and the render-cycle wait — the mutation, capture, and restore all happen within one synchronous-per-branch async function, with no intermediate React commit the user can observe.

**Alternative considered**: CSS class toggle instead of inline `style.display` — functionally equivalent; inline style is chosen only because it matches the exact technique already used by the neighboring `inlineEdge*Styles` helpers in both files, keeping the two capture functions internally consistent.

### Transparent/white via `html-to-image`'s existing `backgroundColor` option

**Decision**: Pass `backgroundColor: undefined` (or omit the key) when "Transparent background" is checked, and `backgroundColor: '#ffffff'` when unchecked, on both the `toSvg` and `toPng` calls. No new capture mechanism is needed — `html-to-image`'s `Options.backgroundColor` already does exactly this, and today's code simply never passes it.

### Minimal sharing: one small util, not a shared component

**Decision**: Extract only the generic tail of the export flow — given a captured `dataUrl` and a `format`, trigger the file download with the right extension/MIME — into a small shared function (e.g. `downloadDiagramExport(dataUrl, format, filename)`), reused by both `ErDiagramView.tsx` and `FlowGraph.tsx`. Everything upstream of that (the popup UI, the `handleExport` orchestration, the grid/background DOM mutation, the edge-style inlining) stays duplicated, one implementation per view.

**Why**: the two views' capture logic already differs in scope (edge-style inlining) and is expected to diverge further as view-specific export options are added later (per proposal). A shared popup or shared `handleExport` would need to be generalized prematurely for options neither view has yet; the download-triggering tail, by contrast, is genuinely identical (same two formats, same "make a link, click it" mechanism) and safe to share without constraining either view's future evolution.

### Popup structure mirrors `FlowCanvasSettings`

**Decision**: Each new Export control is `Button` (ref captured as `anchorElement`, toggles local `open` state) + `Popup` (`anchorElement`, `open`, `placement="bottom-end"`, `onOpenChange={setOpen}`) wrapping a fixed-width flex-column `div`, containing (top to bottom): a `SegmentedRadioGroup` for format, the two `Checkbox`es, and the "Export" action button. This is the same shape as `FlowCanvasEditor.tsx`'s existing `FlowCanvasSettings`, so no new popup pattern is introduced to the codebase — implemented independently in each file rather than factored into a shared component (see sharing decision above).

## Risks / Trade-offs

- **[Risk]** `.react-flow__background`'s exact DOM shape is an xyflow implementation detail, not a public API — a future xyflow upgrade could rename or restructure it, silently breaking grid suppression (the checkbox would do nothing, degrading gracefully to "grid always included" rather than erroring). → **Mitigation**: guard the `querySelector` result with a null check so a missing element is a no-op, not a thrown error; note the coupling in a code comment at the mutation site.
- **[Risk]** Two independent `handleExport` implementations means a future bug fix (e.g. a `html-to-image` quirk workaround) must be applied twice. → **Mitigation**: accepted deliberately per the proposal's stated preference for independent evolution over premature sharing.
- **[Trade-off]** No persistence of export preferences means a user who always wants "white, no grid" must reselect it every time. → Accepted: proposal explicitly requires this reset-to-default behavior.

## Open Questions

None outstanding — grid-suppression mechanism, sharing boundary, and defaults were resolved during exploration prior to this proposal.
