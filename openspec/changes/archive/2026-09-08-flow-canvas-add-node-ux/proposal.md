## Why

Reviewing the current `FlowCanvasEditor` surfaced three concrete authoring problems: (1) adding a step via the toolbar's "Add Step" control drops the new, still-unconnected node at whatever coordinate ELK's autolayout happens to compute for a second disconnected root — in practice this frequently lands directly on top of the flow's first step, visually merging the two cards, which also violates `visual-flow-editor`'s existing "steps without a stored position autolayout ... instead of stacking at a default coordinate" guarantee; (2) the only way to add a step that's already connected to an existing one is to add it unconnected and then drag a connection to it — there's no one-click "add the next step from here"; (3) a transition label longer than a few words is rendered as raw, non-wrapping SVG text and simply overflows past the edge instead of staying legible. None of these need a data-model change — all three are canvas rendering/interaction fixes to shared frontend code (`flowLayout.ts`, `FlowCanvasEditor.tsx`, `FlowNodes.tsx`).

## What Changes

- Fix the "Add Step" toolbar control so a newly added, unconnected step is placed at a deterministic, non-colliding position (a new row below the flow's existing bounding box, left-aligned to it) and the canvas re-fits to show it, instead of relying on autolayout to place a disconnected node and panning the camera to wherever that landed.
- Add a persistent (always visible, not hover-only) "+" control to every node's header, alongside the existing remove control (which also becomes persistent to match). Activating it opens the same node-type picker "Add Step" already uses, and on save wires the new step as an outgoing transition from that node (a new branch if the node already has one) and positions it one layout-step past its source, in whichever direction the canvas is currently laid out.
- Add a dashed, semi-transparent "add next step" placeholder card, shown only next to a step with no outgoing transition, occupying the slot its next step would take. Activating it behaves identically to that step's own header "+" — same picker, same wiring, same position — it is a shortcut for the single most common case, not a separate code path. It never appears for a step that already has an outgoing transition.
- Existing drag-to-connect (wiring two already-placed nodes together) is unchanged and remains available alongside these two new "create and connect a new step" affordances.
- Replace the diagram's transition-edge label rendering so a long label wraps onto multiple lines within a fixed-width box instead of rendering as one non-wrapping line, on both the editable canvas and the read-only detail-page diagram (shared rendering code).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `flow-management`: "Client-side Flow diagram and Flow authoring UI" changes so an unconnected step added via the toolbar control lands at a deterministic non-overlapping position instead of an autolayout-computed one; adding a step gains two additional entry points (a node's own persistent add control, and a terminal step's add-next placeholder); a transition's label rendering gains wrapping instead of unbounded single-line text.
- `visual-flow-editor`: "Visual Flow step authoring" gains the two additional ways to add a step described above (connected-from-a-node add, and the add-next placeholder on a step with no outgoing transition), and its per-node add/remove controls are specified as always visible rather than hover-only.

## Impact

- `core/frontend/src/lib/flowLayout.ts`: deterministic placement for an unconnected new step; a custom edge type (or edge label renderer) that wraps label text instead of the default non-wrapping SVG label; `estimateLabelSize()` updated to reserve ELK layout space for wrapped, multi-line labels.
- `core/frontend/src/components/FlowNodes.tsx`: persistent (non-hover) add/remove header controls; a new ephemeral "add next step" placeholder node type, shown only for steps with no outgoing transition.
- `core/frontend/src/components/FlowCanvasEditor.tsx`: wiring for the node-header add control and the placeholder card (both opening `FlowStepModal` and, on save, connecting + positioning the new step relative to their source); toolbar "Add Step" placement/fit-view fix.
- No backend or `steps` JSON schema changes — everything here is presentation/interaction only, in the same category as the prior `polish-flow-canvas-editor` change.
