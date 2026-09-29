## Why

`flow-canvas-redesign` replaced the Flow editor's card-list with an interactive `@xyflow/react` canvas (`FlowCanvasEditor.tsx`), but the edit page still wires it up as a small side panel next to a separate, read-only preview, and several rendering/interaction gaps were never closed. Reviewing the result surfaced nine concrete usability problems — no arrowheads on transitions, cramped autolayout spacing, no tooltip on truncated node text, a kind label that visually blends into the node title, no icon differentiating node kinds, no way to edit or delete a transition without deleting a node, layout-direction changes that don't visually apply, and an editor/preview split that duplicates the diagram into two panels instead of editing the one the author is already looking at.

## What Changes

- Add arrowheads (`markerEnd`) to transition edges so direction is visible in both the read-only detail view and the edit canvas.
- Add `elk.spacing.nodeNode` to the ELK layout options so sibling nodes in the same layer no longer render edge-to-edge.
- Wrap truncated node title/subtitle/kind-label text in a `Tooltip` showing the full value.
- Visually separate a node's kind label from its title (distinct color/weight, not just opacity) and add a small per-kind icon, reusing the icon set already defined in `FlowStepModal.tsx`'s node-type picker.
- Add an edge-click interaction on the edit canvas: clicking a transition opens a small modal to edit its `label` or delete the transition, without deleting either endpoint step.
- **BREAKING** (edit-page layout only, no data/API change): restructure the Flow edit page so the interactive canvas (`FlowCanvasEditor`) is the primary, full-width panel — replacing the separate read-only `FlowGraph` preview — and the JSON/Monaco editor moves into a collapsible right-side rail toggled by the existing show/hide editor control. The Visual/JSON mode toggle is replaced by "canvas is always visible; JSON rail is optional."
- Changing the layout-direction setting (top-down / left-right) immediately re-runs Auto Layout and overwrites every visible step's position, instead of only taking effect the next time the separate Auto Layout button is pressed.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `flow-management`: "Client-side Flow diagram and Flow authoring UI" changes from a two-panel (editor + separate live-preview) layout to a single primary canvas with an optional JSON rail; "Flow diagram layout direction and manual node positioning" changes so a layout-direction change alone (not just the Auto layout control) triggers recomputed positions; diagram rendering gains arrowheads, node spacing, tooltips, and an edge edit/delete interaction.
- `visual-flow-editor`: "Synchronized Visual and JSON modes" changes from mutually-exclusive Visual/JSON panels to the canvas always being the primary view with JSON available as a togglable rail; node kind styling gains an icon and a visually distinct kind label.

## Impact

- `core/frontend/src/lib/flowLayout.ts`: edge `markerEnd`, ELK `elk.spacing.nodeNode` layout option.
- `core/frontend/src/components/FlowNodes.tsx`: tooltips, kind-label styling, per-kind icons.
- `core/frontend/src/components/FlowCanvasEditor.tsx`: `onEdgeClick` handler + edge edit/delete modal, layout-setting change triggering immediate Auto Layout.
- `core/frontend/src/pages/FlowFormPage.tsx`: panel restructuring (canvas primary, JSON as a rail); removes its use of the read-only `FlowGraph` preview.
- `core/frontend/src/components/FlowGraph.tsx`: confirm whether the read-only `FlowGraph` component is still needed elsewhere (e.g. the Flow detail page) before removing any now-unused code path from the edit page.
- No backend or `steps` JSON schema changes — everything here is presentation/interaction only.
- Explicitly out of scope: "Query"/"Event" step kinds referencing Endpoints/Operations — tracked as a separate change pending a core/plugin extension-point design.
