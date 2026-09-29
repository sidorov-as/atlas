## Why

`flow-elk-edge-routing` and `flow-manual-mode-routing-retention` tried to fix Flow-diagram rendering bugs (edges crossing/cutting through unrelated nodes, edges detaching from their handle) by layering increasingly custom logic on top of ELK: fixed ports, Coffman-Graham layering, `alignSiblingColumns` post-layout column alignment with collision checks, `bendPoints` capture/translation, and per-node "stale routing" tracking so a computed route survives the `autolayout_enabled` toggle. This machinery is now the majority of `flowLayout.ts`, and it keeps needing new specs to patch bugs it itself introduces.

A separate sandbox at `/flows/debug` (`FlowDebugPage.tsx`/`flowDebugLayout.ts`/`FlowDebugEdges.tsx`) demonstrated a much simpler approach: a plain layered layout via either `dagre` or `elkjs` (no ports, no bendpoints, no column alignment — the same shape as each library's own reactflow.dev example), producing node positions only, with edges always drawn live via `@xyflow/react`'s native `getSmoothStepPath` off each node's real rendered handle. It also demonstrated a better edge label (grows/wraps up to a cap, clamps with a tooltip, clickable) than production's current static, non-interactive one.

This change replaces production's custom ELK pipeline with that simpler approach wholesale, and makes the layout engine (dagre vs. ELK) a persisted, user-facing choice per Flow. It is an intentional **rewrite**, not a refactor: the custom routing/alignment system is deleted outright rather than repaired further, trading away its specific obstacle-avoidance guarantee for a much simpler, more predictable, and now user-selectable layout system.

## What Changes

- **BREAKING (behavior)**: Diagram edges no longer route around obstacles. Every connection renders as a live `getSmoothStepPath` curve between its two nodes' actual handle positions — never a precomputed, obstacle-aware polyline. The specific "edge cuts through/under an unrelated node" bug `flow-elk-edge-routing` fixed can recur; this is an accepted tradeoff, not an oversight.
- **BREAKING (behavior)**: The "computed routing survives the autolayout toggle, invalidated per-node on drag" model introduced by `flow-manual-mode-routing-retention` is removed entirely. There is no longer a "routing" concept distinct from node position, so nothing needs to survive a toggle or be invalidated by a drag.
- Replace `flowLayout.ts`'s ELK-with-ports/Coffman-Graham/`alignSiblingColumns`/bendpoint pipeline with a plain layered layout mirroring `flowDebugLayout.ts`'s two engines (`dagre` and `elkjs`, both with no ports, bendpoints, or column alignment) — output is `FlowPositions` only.
- Rewrite `FlowEdges.tsx`'s `FlowTransitionEdge`: always `getSmoothStepPath`; the label becomes an HTML div that grows/wraps up to a cap, clamps with an ellipsis plus a `Tooltip` for the full text past that cap, and is clickable to open the transition-edit modal directly (mirroring `FlowDebugEdges.tsx`), replacing today's static, `pointerEvents: 'none'` label.
- Node cards (`FlowNodes.tsx`: entity-kind icons, stale-ref warning, refresh action) are unchanged — only the `position` values feeding them change.
- **New capability**: a persisted, per-Flow layout engine choice (`dagre` default, or `elk`), selectable from the same settings popup as the existing autolayout toggle, alongside the existing `autolayout_enabled`/`layout_direction` fields — a real backend field (model + migration + API schema), not a client-only preference.
- Drag-stop, while autolayout is on, re-invokes the layout engine directly and writes the result back (mirroring `/flows/debug`'s mechanism), replacing the current "recompute, diff against stored positions, correct if stale" passive effect. Observable behavior for this requirement is unchanged (a drag still has no lasting effect while autolayout is on); only the internal mechanism changes.
- `FlowGraph.tsx` (the read-only Flow detail-page canvas and its PNG/SVG export) shares the rewritten `flowLayout.ts`/`FlowEdges.tsx` with the editor — same rewrite, no forked code path — and gains the new `layoutEngine` field alongside the `autolayoutEnabled`/`layoutDirection` it already threads through.
- Fix `FlowGraph.tsx`'s PNG/SVG export, which currently targets `.react-flow__edge-textbg`/`.react-flow__edge-text` (xyflow's *built-in* smoothstep label DOM), to instead handle whatever DOM the custom `EdgeLabelRenderer`-based label actually renders.
- Placeholder/"add-next" nodes and their collision-avoidance (`buildPlaceholderNodes`/`resolveConnectedPosition` in `FlowCanvasEditor.tsx`) are unchanged, just recomputed against whichever engine's fresh positions.
- Default `layout_engine` for every existing Flow, until an author changes it: `dagre`.

## Capabilities

### New Capabilities
(none — this extends the already-specified `flow-management` capability)

### Modified Capabilities
- `flow-management`: the "Flow diagram layout direction and manual node positioning" requirement gains a third persisted field (`layout_engine`, `dagre` or `elk`, default `dagre`) alongside `autolayout_enabled`/`layout_direction`. The "Client-side Flow diagram and Flow authoring UI" requirement's connection-routing text (added by `flow-manual-mode-routing-retention`'s not-yet-synced delta: obstacle-avoiding routes, per-connection routing staleness) is replaced — a connection is now always a direct, live curve between its two current node positions, with no routing-persistence or staleness concept. The transition-label requirement gains a clickable, growing/clamping label with a tooltip for overflow.

## Impact

- Frontend: `plugins/flows/frontend/src/lib/flowLayout.ts` (rewrite), `flowLayout.test.ts` (rewrite), `components/FlowEdges.tsx` (rewrite), `FlowEdges.test.ts`/`FlowTransitionEdge.test.tsx` (update), `components/FlowCanvasEditor.tsx` (settings popup gets an engine picker; drag-stop mechanics change; `staleNodeIds`/`edgeRouting` state deleted), `components/FlowGraph.tsx` (thread `layoutEngine`; fix export selectors), `pages/FlowFormPage.tsx` (new `layoutEngine` state, same lifecycle as `layoutDirection`).
- Backend: `plugins/flows/backend/atlas_plugin_flows/models.py` (new `layout_engine` field + migration), `api/schemas.py` (`LayoutEngine` literal on `FlowIn`/`FlowPatch`/`FlowOut`), `api/views.py` (wire the field through), `tests/test_flow_crud.py` (extend).
- Unlike the two changes it supersedes, this one is **not** frontend-only — it adds a real, persisted backend field.
- Supersedes parts of two existing changes:
  - `flow-elk-edge-routing` (complete, 21/21 tasks, not yet archived): its obstacle-avoidance routing guarantee is deleted, not carried forward.
  - `flow-manual-mode-routing-retention` (in-progress, 17/18 tasks): its entire subject — per-node routing-staleness surviving the autolayout toggle — is deleted; there is no more routing state to track.
  - Both should be archived together with this change so the canonical `flow-management` spec never asserts routing behavior that no longer exists.
- Verification: the same seeded Flows the superseded changes used (16 `test-*` Flows on the `elk-layout-tests` System, plus `cancellation-flow`/`notification-delivery-flow`) — but checking the new tradeoff (clean, non-overlapping layouts in the common case; obstacle-crossing edges are now an accepted possibility, not a regression to block on) rather than re-verifying obstacle avoidance.
