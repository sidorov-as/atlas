## 1. Deterministic placement for an unconnected new step (`pages/FlowFormPage.tsx`, `components/FlowCanvasEditor.tsx`)

- [x] 1.1 Add a helper (e.g. `nextRowPosition(steps, resolvedPositions)`) that computes the bounding box of every step's resolved position (stored `position`, falling back to the canvas's current autolayout positions) and returns `{x: minX, y: maxY + gap}`, with `gap` matching the vertical spacing `computeFlowAutolayout` uses between layers
- [x] 1.2 Have `FlowFormPage.handleStepModalSave`'s add branch set the new step's `position` to that computed value before appending it to `steps`
- [x] 1.3 In `FlowCanvasEditor`, drop the `focusStepId`/`setCenter` pan for the toolbar-add path and call `fitView({ duration: 200 })` (already used by `handleAutoLayout`) instead, once the new node lands in `nodes`
- [x] 1.4 Update/extend `flowLayout.test.ts` with a unit test for the bounding-box placement helper (empty flow, single-root flow, multi-row flow)

## 2. Shared connected-add logic (`components/FlowCanvasEditor.tsx`, `components/flowSteps.ts`)

- [x] 2.1 Add `addConnectedStep(sourceId, newStep)` (or equivalent) that calls the existing `addTransition(steps, sourceId, newStep.id)` and additionally sets the new step's `position` to one layout-step past the source — transposed for `LAYOUT_TOP_DOWN` vs `LAYOUT_LEFT_RIGHT` — using `FLOW_NODE_WIDTH`/spacing constants already in `flowLayout.ts`
- [x] 2.2 Wire this function so both the node-header add control (task 3) and the add-next placeholder (task 4) call it via `FlowStepModal`'s save callback, passing the clicked node's id as `sourceId`
- [x] 2.3 Add a unit test in `flowSteps.test.ts` (or a new test alongside `addConnectedStep`'s definition) covering: adding to a childless step sets `next_step`; adding to a step that already has `next_step`/`next_steps` appends a branch; the new step's position lands adjacent to its source

## 3. Persistent node header add/remove controls (`components/FlowNodes.tsx`)

- [x] 3.1 Change `NodeDeleteButton`'s visibility from hover-only to always-visible
- [x] 3.2 Add a new always-visible "add" button next to it in both `PaletteNodeCard` and `StepNode`, calling a new `data.onAddNext` `FlowNodeData` field (parallel to the existing `data.onDelete`)
- [x] 3.3 Wire `data.onAddNext` in `FlowCanvasEditor`'s node-building code to open `FlowStepModal` in "add" mode with the clicked node recorded as the connect-from source, so its save handler routes through `addConnectedStep` (task 2.1)

## 4. Add-next placeholder card (`components/FlowNodes.tsx`, `lib/flowLayout.ts`, `components/FlowCanvasEditor.tsx`)

- [x] 4.1 Add a new synthetic node type (e.g. `'add-placeholder'`) to `FLOW_NODE_TYPES`: a dashed, semi-transparent card with a centered "+", no title/kind/tooltip, not draggable
- [x] 4.2 In `FlowCanvasEditor`'s layout effect, emit one placeholder node for every step where `transitionTargets(step).length === 0`, positioned via the same "one layout-step past the source" calculation `addConnectedStep` uses for the resulting real node
- [x] 4.3 Wire the placeholder's click handler to open `FlowStepModal` with that step as the connect-from source, identical to the node-header add control (task 3.3) — same code path, not a duplicate
- [x] 4.4 Update `handleNodesDelete`/selection logic (and any other code iterating `nodes`) to skip nodes of type `'add-placeholder'` — give them `deletable: false` and `selectable: false` at creation as a first line of defense
- [x] 4.5 Confirm a step that already has an outgoing transition never gets a placeholder, and that a placeholder for a step disappears (replaced by the real connection) once that step gains one

## 5. Wrapping transition labels (`lib/flowLayout.ts`)

- [x] 5.1 Add a custom edge component (e.g. `FlowTransitionEdge`) using `getSmoothStepPath()` + `<BaseEdge>` for the path/marker, and `<EdgeLabelRenderer>` to render the label as an HTML `<div>`/Gravity `Text` with a fixed max-width and normal CSS wrapping, instead of the default `smoothstep` type's SVG label
- [x] 5.2 Register it in a new `FLOW_EDGE_TYPES` map and pass `edgeTypes={FLOW_EDGE_TYPES}` to both `FlowCanvasEditor`'s and the read-only `FlowGraph`'s `<ReactFlow>` (shared code — verify both consume the same map)
- [x] 5.3 Update `buildFlowNodesAndEdges` to set each edge's `type` to the new custom type instead of `'smoothstep'`
- [x] 5.4 Update `estimateLabelSize()` to estimate wrapped line count from the label length and the renderer's fixed max-width (`Math.ceil(label.length / charsPerLine)`) and reserve `height = lines * lineHeight` instead of a single-line height
- [x] 5.5 Update `flowLayout.test.ts`'s coverage of `estimateLabelSize`/ELK label-space reservation for a long label that now spans multiple estimated lines

## 6. Spec-visible behavior verification

- [x] 6.1 Run the frontend test suite for touched files (`flowLayout.test.ts`, `flowSteps.test.ts`, `FlowFormPage.test.tsx`, plus any new tests from tasks 1-5)
- [x] 6.2 Manually verify on the edit page: toolbar "Add Step" lands a new row below the existing diagram with no overlap and the view fits to show it; a node's header "+" adds and connects a step in one action, growing `next_steps[]` into a branch on a second use; a childless step's placeholder does the same and disappears once connected; a step with an existing transition shows no placeholder; drag-to-connect between two existing nodes still works unchanged; a long transition label wraps onto multiple lines instead of overflowing
- [x] 6.3 Confirm the Flow detail page (`FlowDetailPage.tsx`) still renders correctly via `FlowGraph` and shows wrapped long transition labels too (shared edge-rendering code), with no placeholder cards or add controls (read-only canvas has no `onAddNext`/`onDelete` wired)
