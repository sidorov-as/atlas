## 1. Diagram rendering (`lib/flowLayout.ts`)

- [x] 1.1 Add `markerEnd: { type: MarkerType.ArrowClosed }` (import `MarkerType` from `@xyflow/react`) to every edge built in `buildFlowNodesAndEdges`
- [x] 1.2 Add an `'elk.spacing.nodeNode'` entry to `buildElkGraph`'s `layoutOptions`, sized relative to `FLOW_NODE_WIDTH`/`FLOW_NODE_HEIGHT` so sibling nodes in the same layer no longer render edge-to-edge
- [x] 1.3 Update/extend `flowLayout.test.ts` to assert edges carry a `markerEnd` and that `buildElkGraph`'s layout options include the new spacing key

## 2. Node visuals (`components/FlowNodes.tsx`)

- [x] 2.1 Wrap the kind-label, title, and subtitle `<Text ellipsis>` elements in a `Tooltip` showing the full untruncated value
- [x] 2.2 Restyle `PaletteNodeCard`'s kind label to a theme-aware secondary color/weight distinct from the node's fixed-palette title color (not just reduced opacity on the same color)
- [x] 2.3 Add the matching per-kind icon (reusing `FlowStepModal.tsx`'s `KIND_TILES` icon set: Person/Cube/Database/PlugConnection/Layers/Persons/Compass/Flag) next to the kind label in both `PaletteNodeCard` and `StepNode`
- [x] 2.4 Extract the kind→icon mapping into a shared constant (e.g. alongside `FLOW_NODE_KIND_LABELS` in `flowNodeKind.ts`) so `FlowStepModal.tsx`'s tile picker and `FlowNodes.tsx` consume the same source instead of duplicating the icon list

## 3. Transition edit/delete (`components/FlowCanvasEditor.tsx`)

- [x] 3.1 Add an `onEdgeClick` handler to the canvas's `<ReactFlow>` that opens a new edge modal (e.g. `FlowTransitionModal.tsx`) for the clicked edge's source step and target id
- [x] 3.2 Build the edge modal: a `label` text field pre-filled from the transition's current label, a Save action, and a "Delete transition" action, following `FlowStepModal.tsx`'s `Dialog` structure
- [x] 3.3 Wire Save to update the source step's `next_step.label` or the matching `next_steps[]` entry's `label`
- [x] 3.4 Wire Delete to remove the transition from the source step's `next_step`/`next_steps` without touching either endpoint step, reusing the existing single-transition-removal logic pattern from `removeStepIds`
- [x] 3.5 Make `FlowLayoutSettings`'s `onChange` call `handleAutoLayout()` immediately after updating the layout preference

## 4. Edit page restructuring (`pages/FlowFormPage.tsx`)

- [x] 4.1 Replace the "Preview" panel's `FlowGraph` with `FlowCanvasEditor`, full width; remove the `FlowGraph` import from this file only (`FlowDetailPage.tsx` keeps using it, no change there)
- [x] 4.2 Remove the `mode` state, `switchMode`, and the Visual/JSON toggle button; the "Steps" panel becomes a JSON-only rail
- [x] 4.3 Keep the rail's open/closed toggle on the existing `isEditorOpen` state and `LayoutSideContentRight`/`LayoutColumns` buttons, now controlling the JSON rail instead of the whole "Steps" panel
- [x] 4.4 Keep JSON→canvas sync unconditional (drop the `mode === 'json'` gate on the `parsedSteps` sync effect) so JSON edits always flow into the canvas, whether or not the rail is open
- [x] 4.5 Simplify `scrollToStep`: always applicable to the canvas (open the step's edit modal is already the canvas's own node-click behavior); additionally scroll/select the JSON block only when the rail is open
- [x] 4.6 Update `handleAddStep` for the single-canvas model — "Add Step" always opens `FlowStepModal`'s node-type picker; drop the JSON-mode append-and-scroll branch (or keep it, gated on the rail being open, if the JSON rail should retain its own quick-append affordance — decide during implementation and note the choice)
- [x] 4.7 Update `FlowFormPage.test.tsx` for the new structure (no mode toggle, canvas always present, JSON rail toggle) — replace the existing `FlowGraph` mock/usage with `FlowCanvasEditor` assertions where the test currently exercises the old "Preview" panel

## 5. Verification

- [x] 5.1 Run the frontend test suite for the touched files (`flowLayout.test.ts`, `flowSteps.test.ts`, `FlowFormPage.test.tsx`, and any new test file for the transition edit/delete modal)
- [x] 5.2 Manually exercise the edit page: add/edit/retype/connect/reposition/remove a step; edit and delete a transition label; toggle the JSON rail open/closed and confirm two-way sync; change the layout-direction setting and confirm the canvas re-lays out immediately; hover a long node title/subtitle for a tooltip; confirm arrowheads and node spacing on a flow with several sibling branches
- [x] 5.3 Confirm the Flow detail page (`FlowDetailPage.tsx`) still renders correctly via `FlowGraph`, unaffected by the edit-page changes, and also shows the new arrowheads/spacing/tooltip/icon improvements (shared layout/node code)
