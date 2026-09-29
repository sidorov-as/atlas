## 1. Shared download utility

- [x] 1.1 Add a small shared util (e.g. `downloadDiagramExport(dataUrl, format, filename)`) that triggers a file download from a captured `dataUrl` for a given `'svg' | 'png'` format — the only piece shared between the two views.
- [x] 1.2 Update both existing `handleExport` implementations to call it instead of their current inline download code, without otherwise changing their behavior yet (a refactor-only step, verified against current export output before layering in new options).

## 2. ER Diagram export popup (`ErDiagramView.tsx`)

- [x] 2.1 Replace the two "SVG"/"PNG" `Button`s with a single `Button` using the `ArrowUpRightFromSquare` icon (`@gravity-ui/icons`) and tooltip "Export", following the ref-anchor + `Popup` pattern from `FlowCanvasSettings` (`FlowCanvasEditor.tsx`).
- [x] 2.2 Build the popup content: `SegmentedRadioGroup` (SVG/PNG, default SVG), `Checkbox` "Transparent background" (default checked), `Checkbox` "Grid" (default checked), and an "Export" action button — all as local component state that resets to these defaults every time the popup opens (e.g. reinitialize state in the `onOpenChange`/open handler rather than lifting it).
- [x] 2.3 Extend `handleExport`/`inlineEdgeStrokeStyles` to accept `{ format, transparent, showGrid }`: pass `backgroundColor: transparent ? undefined : '#ffffff'` to `toSvg`/`toPng`; when `!showGrid`, locate `.react-flow__background` via `querySelector`, set `style.display = 'none'` before capture and restore it in `finally` (no-op if the element is not found).
- [x] 2.4 Wire the popup's "Export" action to call the extended `handleExport` with the popup's current selections, then close the popup.

## 3. Flow diagram export popup (`FlowGraph.tsx`)

- [x] 3.1 Replace the two "SVG"/"PNG" `Button`s with the same Export button + popup pattern as 2.1–2.2, implemented independently in this file (no shared component with `ErDiagramView.tsx`).
- [x] 3.2 Extend `handleExport`/`inlineEdgeExportStyles` with the same `{ format, transparent, showGrid }` handling as 2.3, independently in this file.
- [x] 3.3 Wire the popup's "Export" action the same way as 2.4.
- [x] 3.4 Confirm no export control is added to `FlowCanvasEditor.tsx` (the editable canvas) — out of scope for this change.

## 4. Verification

- [x] 4.1 Manually verify on the ER Diagram tab: default export (SVG, transparent, grid) matches prior behavior; toggling each checkbox independently changes only the downloaded file, not the live canvas at any point; reopening the popup after an export shows defaults again, not the last-used choices.
- [x] 4.2 Manually verify the same four checks on the read-only Flow page (`/flows/:id`).
- [x] 4.3 Verify PNG and SVG both honor the white-background option (not only transparent, which was already default behavior).
- [x] 4.4 Verify the editable Flow canvas (`/flows/:id/edit`) is unchanged — still no export control present.
