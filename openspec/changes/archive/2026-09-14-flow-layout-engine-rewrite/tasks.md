## 1. Backend: persisted `layout_engine` field

- [x] 1.1 Add `layout_engine` field to `Flow` in `plugins/flows/backend/atlas_plugin_flows/models.py` (choices `dagre`/`elk`, default `dagre`), mirroring how `layout_direction` is declared
- [x] 1.2 Generate and review the migration for the new field (default-backfilled, additive, no data loss)
- [x] 1.3 Add `LayoutEngine = Literal["dagre", "elk"]` to `plugins/flows/backend/atlas_plugin_flows/api/schemas.py` and add the field to `FlowIn` (default `"dagre"`), `FlowPatch` (optional), `FlowOut` (required)
- [x] 1.4 Wire `layout_engine` through `plugins/flows/backend/atlas_plugin_flows/api/views.py` create/update/read paths, same as `layout_direction`
- [x] 1.5 Extend `plugins/flows/backend/atlas_plugin_flows/tests/test_flow_crud.py`: create/update a Flow with an explicit `layout_engine`, confirm the default (`dagre`) on a Flow created without one, confirm `FlowPatch` can change it independently of other fields

## 2. Frontend: rewrite `flowLayout.ts`'s layout engine

- [x] 2.1 Add `dagre` as a frontend dependency if not already present (check `plugins/flows/frontend/package.json` — `flowDebugLayout.ts` already imports it, confirm it's a real dependency, not dev-only)
- [x] 2.2 Add `export type FlowLayoutEngine = 'dagre' | 'elk'` to `flowLayout.ts`
- [x] 2.3 Implement `layoutWithDagre(nodeIds, edges)` and `layoutWithElk(nodeIds, edges)` in `flowLayout.ts`, porting `flowDebugLayout.ts`'s two functions: one node per step at `FLOW_NODE_WIDTH`/`FLOW_NODE_HEIGHT`, one edge per transition via `edgesOf`, label size reserved via the existing `estimateLabelSize` — no ports, no `FIXED_POS`, no bendpoint/section extraction
- [x] 2.4 Change `computeFlowAutolayout(steps, direction, engine)` to dispatch to the selected engine and return `{ positions: FlowPositions }` only — remove the `edgeRouting` return value entirely
- [x] 2.5 Delete `buildElkGraph`'s port declarations (`portId`, `stepIdFromPort`, `PORT_SUFFIX`, `FIXED_POS` layoutOptions) — ELK path no longer needs per-node ports
- [x] 2.6 Delete `alignFlowPositions`, `alignSiblingColumns`, `computeEdgeRouting`, `handleAnchor`, `RawEdgeRoute`, `FlowEdgeRouting`, `FlowAlignmentDeltas`, `FlowEdgePoint` (keep `FlowEdgePoint` only if still referenced elsewhere after the edge rewrite in section 3 — otherwise delete)
- [x] 2.7 Update `buildFlowNodesAndEdges` to drop the `edgeRouting`/`staleNodeIds` parameters and the `data.routing` field on each edge
- [x] 2.8 Update `mergeStepPositions` call sites' signatures if `engine` needs to flow through them (check `FlowCanvasEditor.tsx`/`FlowGraph.tsx` usage)
- [x] 2.9 Rewrite `flowLayout.test.ts`: remove all bendpoint/`alignSiblingColumns`/`computeEdgeRouting` test cases; add coverage that `computeFlowAutolayout` with `engine: 'dagre'` and `engine: 'elk'` both return a position for every step id, and that `buildFlowNodesAndEdges`'s output edges never carry a `routing` field

## 3. Frontend: rewrite `FlowEdges.tsx`

- [x] 3.1 Remove `FlowTransitionEdge`'s `routing`/polyline branch and `polylinePath`/`polylineMidpoint` helpers — always compute via `getSmoothStepPath`
- [x] 3.2 Port `FlowDebugEdges.tsx`'s label treatment: HTML div via `EdgeLabelRenderer` that grows up to `FLOW_NODE_WIDTH`/`FLOW_NODE_HEIGHT`, `-webkit-line-clamp` past that cap, wrapped in a `Tooltip` showing the full label, `pointerEvents: 'all'` with `onClick` opening the transition modal
- [x] 3.3 Thread an `onOpenTransitionModal` callback into each edge's `data` from `buildFlowNodesAndEdges` (or its call sites), mirroring `FlowDebugPage.tsx`'s wiring, so the label's click handler has something to call
- [x] 3.4 Update `FlowEdges.test.ts`/`FlowTransitionEdge.test.tsx`: drop routing-path assertions, add coverage for the grow/clamp/tooltip behavior and the label's click opening the modal

## 4. Frontend: wire the engine setting into the editor

- [x] 4.1 `FlowCanvasEditor.tsx`: add a `layoutEngine`/`onLayoutEngineChange` prop pair (mirroring `layoutDirection`), pass `engine` into every `computeFlowAutolayout` call
- [x] 4.2 `FlowCanvasSettings`: add a `SegmentedRadioGroup` (Dagre / ELK.js) beneath the autolayout `Switch`, mirroring `FlowDebugPage.tsx`'s `DebugSettingsPopup`
- [x] 4.3 Replace the passive layout effect's stale-diff logic for the drag-stop path: `handleNodeDragStop`, while `autolayoutEnabled` is on, calls `computeFlowAutolayout` directly and writes the result back (mirroring `FlowDebugPage.tsx`'s `applyLayout`/`handleNodeDragStop`), instead of relying on the effect's diff-and-correct
- [x] 4.4 Delete `edgeRouting`/`staleNodeIds` state, and all code paths that set or read them, from `FlowCanvasEditorGraph` (already gone as a byproduct of section 2/3's rewrite — verified no remaining references)
- [x] 4.5 Update `handleAutoLayout` (the manual "Tune layout" control) to pass `layoutEngine` through and stop touching the now-deleted routing state
- [x] 4.6 `FlowFormPage.tsx`: add `layoutEngine` state sourced from `existing.layoutEngine` (defaulting to `'dagre'` for a new Flow), pass it to `FlowCanvasEditor`, include it in the `handleSubmit` payload

## 5. Frontend: wire the engine setting into the read-only canvas and fix export

- [x] 5.1 `FlowGraph.tsx`: add a `layoutEngine` prop, pass it into `computeFlowAutolayout`
- [x] 5.2 `FlowDetailPage.tsx`: pass the Flow's `layoutEngine` through to `FlowGraph`
- [x] 5.3 Investigate whether `inlineEdgeExportStyles`'s `.react-flow__edge-textbg`/`.react-flow__edge-text` selectors currently match anything given the custom `EdgeLabelRenderer`-based label (both before and after this change) — confirm with a quick manual export test
- [x] 5.4 Fix `inlineEdgeExportStyles` to target the label `<div>`/`<Text>` DOM this change's `FlowTransitionEdge` actually renders, so PNG/SVG export inlines its style correctly

## 6. Frontend: types and API client

- [x] 6.1 Add `layoutEngine` to the Flow entity type wherever `autolayoutEnabled`/`layoutDirection` are typed (`frontend/lib/types` or equivalent) and to `flowsApi`'s create/update payload types (pulled forward from section 6 — needed for section 4's `FlowFormPage.tsx` wiring to type-check)

## 7. Verification

- [x] 7.1 Manually verify against the 16 seeded `test-*` Flows on the `elk-layout-tests` System with both `dagre` and `elk` engines: layouts are clean and non-overlapping in the common case; note (don't block on) any recurring edge/node crossings as the accepted tradeoff
- [x] 7.2 Manually verify `cancellation-flow`/`notification-delivery-flow` demo Flows render sensibly under the new engines
- [x] 7.3 Verify the transition-label grow/clamp/tooltip/click behavior on a Flow with a short label, a long-but-under-cap label, and an over-cap label
- [x] 7.4 Verify PNG/SVG export from the detail page renders transition labels correctly after the `inlineEdgeExportStyles` fix
- [x] 7.5 Verify switching `layout_engine` in the settings popup persists on save and is reflected identically on the detail page for a second viewer
- [x] 7.6 Run the full frontend and backend test suites for the `flows` plugin

## 8. Spec reconciliation and archival

- [x] 8.1 Archive `flow-elk-edge-routing` together with this change
- [x] 8.2 Archive `flow-manual-mode-routing-retention` together with this change (or correct it first, per its own proposal's sequencing note) so the canonical `flow-management` spec never asserts obstacle-avoiding routing or per-node routing-staleness
- [x] 8.3 Sync this change's `flow-management` spec delta into `openspec/specs/flow-management/spec.md` and confirm the merged result reads coherently (no leftover routing/staleness language from the two superseded changes)
