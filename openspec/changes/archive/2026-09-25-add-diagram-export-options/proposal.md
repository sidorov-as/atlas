## Why

The ER Diagram tab and the read-only Flow diagram each expose plain "SVG" and "PNG" export buttons that capture whatever is on screen with no control over background or grid dots. Users who want a clean image for docs or slides currently get the dot-grid baked in and no way to force a white background, and have no way to get a grid-free capture without visiting a design tool afterward.

## What Changes

- Replace the two "SVG"/"PNG" toolbar buttons on the ER Diagram tab (`/resources/:id?tab=er-diagram`) and on the read-only Flow page (`/flows/:id`) with a single "Export" button (`ArrowUpRightFromSquare` icon) that opens a popup.
- The popup offers a format choice (SVG / PNG), a "Transparent background" checkbox, and a "Grid" checkbox, plus an "Export" action that performs the download and closes the popup.
- Defaults on every popup open: SVG format, transparent background checked, grid checked — none of the three choices persist between exports or across sessions.
- The grid checkbox controls only the exported file's content; the live canvas/viewer is never affected by opening the popup, changing a checkbox, or exporting.
- The transparent/white background choice applies to both SVG and PNG output.
- The editable Flow canvas (`FlowCanvasEditor.tsx`) is untouched — it has no export control today and this change does not add one there.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `database-schema-plugin`: the ER Diagram view's export requirement changes from "downloadable SVG file and PNG file" to an Export popup offering format, transparent-background, and grid-visibility choices, each reset to its default on open.
- `flow-management`: the read-only Flow detail page diagram gains the same Export popup (format, transparent background, grid visibility), where today no export capability is specified at all.

## Impact

- `plugins/database-schema/frontend/src/components/ErDiagramView.tsx` — replace the two export buttons with the new Export button + popup; extend `handleExport`/`inlineEdgeStrokeStyles` to honor transparency and grid options.
- `plugins/flows/frontend/src/components/FlowGraph.tsx` — same UI and export-logic changes as above, independently implemented (`inlineEdgeExportStyles`, its own `handleExport`).
- A new small shared utility (exact location TBD in design.md) for the generic "capture element → dataURL → trigger file download" step, reused by both files above; no shared popup component or shared grid/background wiring.
- No backend, API, or persisted-data changes — this is entirely frontend, client-side capture behavior.
