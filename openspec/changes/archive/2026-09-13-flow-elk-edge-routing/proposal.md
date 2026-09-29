## Why

Flow diagram edges currently render via React Flow's generic `getSmoothStepPath()`, computed purely from each edge's two endpoint coordinates — it has no awareness of any other node or edge on the canvas. ELK, however, already computes a correct, obstacle-aware route for every edge (`bendPoints`) as part of the same layout pass that places the nodes; we discard that result and only keep each node's `x`/`y`. Confirmed by direct experiment (raw `elk.layout()` output, no app code involved) against three reported shapes — a bypass edge skipping two ranks, a short branch reconverging with a much longer one, and two sibling branches converging on a shared merge step — ELK's own `bendPoints` never cross a node or another edge in any of the three; the visible "edge cuts through/under an unrelated node" and "two edges cross" bugs users see today are entirely introduced by rendering through `getSmoothStepPath` instead.

## What Changes

- Capture each edge's `bendPoints` from `elk.layout()`'s result (`computeFlowAutolayout`), not just node `x`/`y`.
- Extend `alignSiblingColumns`'s post-ELK sibling-column alignment to also track, per node, the "along-axis" delta it applied (today this is computed internally and discarded). Use it to translate an edge's `bendPoints` by the same amount whenever both of that edge's endpoints moved by an identical delta.
- When an edge's two endpoints received *different* deltas (a real case: reconverging branches of uneven depth under one parent, or generally in dense fan-out shapes — verified to occur in one of the three reported flows), that edge alone falls back to today's `getSmoothStepPath` rendering. This is a per-edge decision — most edges in the same diagram still render via `bendPoints` even when one edge falls back.
- `FlowTransitionEdge` (`FlowEdges.tsx`) renders a multi-point path when routing data is present, preserving today's arrowhead, label placement/wrapping, and dashed placeholder-edge styling; it renders exactly as it does today (`getSmoothStepPath`) when routing data is absent.
- No change to manual mode: while `autolayout_enabled` is `false`, ELK never runs (as today), so those edges keep rendering via `getSmoothStepPath` — there is no ELK routing to speak of for a freely-dragged layout.
- No change to the persisted `Flow.steps[].position` contract: edge routing is derived, render-time-only data recomputed on every autolayout pass, alongside the existing per-step `position` — it is never written to `steps[]` or any other persisted field, so `autolayout_enabled` on/off continues to work exactly as it does today (position is what's saved and reused; routing is just how the currently-fresh diagram happens to draw its edges).

## Capabilities

### New Capabilities
(none — this is a rendering-fidelity change to an already-specified capability)

### Modified Capabilities
- `flow-management`: the "Client-side Flow diagram and Flow authoring UI" requirement gains an explicit routing guarantee — a diagram edge computed by autolayout SHALL route around any node it would otherwise visually cross, with a defined, narrower fallback scenario for the case where that isn't possible, and an explicit "manual mode is unaffected" scenario.

## Impact

- Frontend only (`plugins/flows/frontend/src/lib/flowLayout.ts`, `flowLayout.test.ts`, `FlowEdges.tsx`, `FlowCanvasEditor.tsx`, `FlowGraph.tsx`). No backend/API/model change, no migration.
- Verification set: the 16 seeded `test-*` Flows on the `elk-layout-tests` System (built specifically to stress branch/merge shapes for ELK), plus the pre-existing seeded `cancellation-flow`/`notification-delivery-flow` demo Flows already flagged for this exact issue in `flow-autolayout-modes`' design.md.
