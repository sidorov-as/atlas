## 1. Shared graph shell

- [x] 1.1 Create `CompactDependencyGraph.tsx` under `plugins/apis/frontend/src/components/`: owns loading `Skeleton`, error `Alert`+retry, empty-state placeholder (`emptyMessage` + optional `canLinkService`/`onLinkService`), the `height/border/borderRadius` wrapper, the `<ReactFlow>` element with the shared read-only props (`nodesDraggable={false}`, `nodesConnectable={false}`, `elementsSelectable`, `fitView`, `minZoom={0.2}`), `<Background/>`, `<Controls showInteractive={false}/>`, and the compact-view overflow `<Panel position="top-right">`.
- [x] 1.2 Add a "Full screen" control to `CompactDependencyGraph` that opens a Gravity UI `Dialog` (matching `LinkServiceDialog.tsx`'s convention: `hasCloseButton`, `onClose`) sized near-viewport via `modalClassName`/inline style (no built-in fullscreen `size`/`maxWidth` tier exists — confirmed against `Dialog.d.ts`).
- [x] 1.3 `CompactDependencyGraph` accepts a second, uncapped `nodes`/`edges` pair for the fullscreen `<ReactFlow>` instance, distinct from the capped inline pair — no new data fetch, both come from the same already-loaded graph data.

## 2. Endpoint consumers graph

- [x] 2.1 Update `EndpointConsumersGraph.tsx`'s `buildGraph()` to accept an optional limit (used for the inline/capped call; omitted for the fullscreen/uncapped call), keeping `MAX_GRAPH_SERVICES` as the inline default.
- [x] 2.2 Refactor `EndpointConsumersGraph.tsx` to build both the capped and uncapped graphs and render via `CompactDependencyGraph`, removing the now-duplicated shell JSX.
- [x] 2.3 Update `EndpointConsumersGraph.test.tsx`: existing cap-behavior assertions now target the inline graph specifically; add coverage for full-screen open/close and for the uncapped node count when full-screen is open.

## 3. Operation consumers graph

- [x] 3.1 Update `OperationConsumersGraph.tsx`'s `buildGraph()`/`arcNodes()` the same way — optional limit for inline, uncapped for fullscreen — keeping `MAX_GRAPH_PARTICIPANTS` as the inline default and preserving the publisher/subscriber arc split at any node count.
- [x] 3.2 Refactor `OperationConsumersGraph.tsx` to render via `CompactDependencyGraph`, removing the now-duplicated shell JSX.
- [x] 3.3 Update `OperationConsumersGraph.test.tsx`: same additions as 2.3, for participants instead of Services.

## 4. Endpoint Overview layout

- [x] 4.1 Restructure `EndpointOverviewTab.tsx`'s top section into a CSS grid (`grid-template-columns: minmax(0, 2fr) minmax(360px, 1fr)`): left column keeps Documentation + Details; right column holds `EndpointConsumersGraph`.
- [x] 4.2 Move Path/Query/Header parameter tables and the Responses table out of the grid row into a full-width section below it.
- [x] 4.3 Add the collapse-to-single-column behavior under ~1200px viewport width (graph falls below the summary content).
- [x] 4.4 Update `EndpointOverviewTab.test.tsx` for the new section grouping (graph no longer full-width; parameters/responses no longer share a column with Details).

## 5. Operation Overview layout

- [x] 5.1 Apply the equivalent grid restructuring to `OperationOverviewTab.tsx` (left column: existing summary/message content; right column: `OperationConsumersGraph`; full-width section below for whatever currently shares the left column with Details).
- [x] 5.2 Add the same ~1200px single-column collapse behavior.
- [x] 5.3 Add `OperationOverviewTab.test.tsx` (no existing test file for this component) covering the new layout grouping, mirroring `EndpointOverviewTab.test.tsx`'s coverage.

## 6. Verification

- [x] 6.1 Run the frontend test suite for `plugins/apis/frontend` and confirm all updated/added tests pass.
- [x] 6.2 Manually verify both Overview tabs at a wide viewport (graph docked right, same height as summary content) and a narrow viewport (<1200px, graph collapses below), for an Endpoint/Operation with 0, a few, and >12 linked Services/participants.
- [x] 6.3 Manually verify full-screen open/close on both graphs, confirming the uncapped node count and that closing returns to the Overview tab without navigation.
