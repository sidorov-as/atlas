## 1. Verify the coordinate-space assumption

- [x] 1.1 Confirm, against a real `elk.layout()` result, that `result.edges[].sections[].bendPoints`/`startPoint`/`endPoint` share the same coordinate space as `result.children[].x/y` (both root-relative), so Decision 2's per-axis translation needs no extra transform. Record the finding as a code comment at the call site rather than assuming it silently.

## 2. Track per-node alignment deltas

- [x] 2.1 In `flowLayout.ts`, change `alignSiblingColumns` to also build and return a `Record<stepId, number>` of the net "along-axis" delta applied to each node (0 for a node never shifted), alongside its existing in-place mutation of `along`.
- [x] 2.2 Thread this delta map out of `alignFlowPositions` as a second return value (e.g. `{ positions: FlowPositions, deltas: Record<string, number> }`), updating its own signature and its existing unit tests in `flowLayout.test.ts` for the new return shape.

## 3. Compute per-edge routing

- [x] 3.1 In `flowLayout.ts`, capture each edge's raw `bendPoints` (`startPoint`, `bendPoints`, `endPoint`) from `elk.layout()`'s result inside `computeFlowAutolayout`, keyed the same way `buildElkGraph` keys edges (`${sourceId}->${targetId}`).
- [x] 3.2 Add a function that, given the raw per-edge points and the per-node delta map from task 2.2, returns `Record<edgeKey, {x, y}[]> | undefined` per edge: translate every point by the shared delta along the layering axis when `deltas[sourceId] === deltas[targetId]`; otherwise omit that edge's entry (signaling fallback).
- [x] 3.3 Change `computeFlowAutolayout`'s return type from `FlowPositions` to `{ positions: FlowPositions, edgeRouting: FlowEdgeRouting }` (new exported type), updating its own tests and every call site's types.

## 4. Render routed edges

- [x] 4.1 In `FlowEdges.tsx`, extend `FlowTransitionEdge` to check `data?.routing` (a point array): when present, build the path as a polyline through those points (straight segments between consecutive points) instead of calling `getSmoothStepPath`; when absent, keep today's `getSmoothStepPath(...)` call unchanged.
- [x] 4.2 Add a label-position helper that finds the point at the midpoint of the routed path's total length (arc-length walk over the polyline's segments), used in place of `getSmoothStepPath`'s built-in `labelX`/`labelY` only on the routed branch. Unit-test it in isolation against hand-fed point arrays.
- [x] 4.3 Verify the routed branch preserves today's arrowhead (`markerEnd`), label wrapping/box styling, and hover/selection appearance — no new visual language, only a different path/label-position computation.

## 5. Thread routing through both diagram views

- [x] 5.1 In `FlowCanvasEditor.tsx`'s passive layout effect and its `handleAutoLayout`, destructure `computeFlowAutolayout`'s new `{ positions, edgeRouting }` return, and attach each edge's routing to its `Edge.data.routing` in `buildFlowNodesAndEdges`'s output (or the call site building the final `edges` array), keyed by `${sourceId}->${targetId}`.
- [x] 5.2 Do the same in `FlowGraph.tsx`'s canvas effect (the read-only detail-page view), so routed edges render identically on both the editor and the read-only page.
- [x] 5.3 Confirm manual mode (`autolayoutEnabled: false`) never calls `computeFlowAutolayout` (unchanged from `flow-autolayout-modes`), so no edge in that mode ever has `data.routing` set, and `FlowTransitionEdge` falls back to `getSmoothStepPath` for all of them — no explicit mode check needed in the rendering path itself.

## 6. Tests

- [x] 6.1 Add `flowLayout.test.ts` coverage for the delta-tracking change (task 2.1/2.2): a fan-out where all children land in the same layer (delta 0 for all) vs. one requiring a real shift.
- [x] 6.2 Add coverage for the routing-translation function (task 3.2): a uniform-delta edge gets its points translated by the shared delta; a mismatched-delta edge gets `undefined`.
- [x] 6.3 Add coverage for `FlowTransitionEdge`'s two branches (task 4.1) and the label-midpoint helper (task 4.2).
- [x] 6.4 Regression-check the existing `flowLayout.test.ts`/`FlowCanvasEditor`-related suites still pass unmodified in behavior for flows with no autolayout at all (manual mode) and for flows where `edgeRouting` is empty.

## 7. Manual verification

- [x] 7.1 In the running app, verify `test-uneven-branch-lengths` and `test-skip-level-bypass` (elk-layout-tests system) now render every edge routed cleanly around intervening steps, with no visible crossing.
- [x] 7.2 Verify `test-branch-within-branch`: confirm the edges that hit the mismatched-delta case render exactly as before (a direct curve, not broken/detached), and that this doesn't regress any other edge in the same diagram.
- [x] 7.3 Spot-check the remaining seeded `test-*` flows (fan-out/fan-in variants, the lattice, the binary tree, the disconnected pair) and the pre-existing `cancellation-flow`/`notification-delivery-flow` demo Flows for any visual regression.
- [x] 7.4 Confirm manual mode (`autolayout_enabled: false`) is visually unchanged: toggle a flow to manual, drag nodes, and confirm edges still render exactly as they do today.
- [x] 7.5 Confirm `Flow.steps[].position` in the saved JSON is unaffected — save a Flow in both autolayout modes and diff the persisted `steps[]` payload against pre-change behavior; no routing data should appear anywhere in it.
