## Why

Toggling `autolayout_enabled` off currently changes a Flow diagram's edges even when no step's `position` changed at all. This happens because ELK's per-edge computed routing (`bendPoints`) is only ever attached to an edge while `autolayout_enabled` is `true` — the moment the flag flips to `false`, every edge's routing is dropped and it falls back to a generic point-to-point curve, regardless of whether anything about that edge actually became stale. The same gap makes the manual-mode "manual layout control" (product-facing name: "Tune layout") non-durable: it computes a one-time ELK pass, but the very next `steps` change silently discards that routing again, even though the positions it just set haven't moved.

Both symptoms are one missing piece: there is no notion of "is this edge's computed routing still valid," tracked independently of the `autolayout_enabled` flag itself. This change adds that notion.

## What Changes

- An edge's ELK-computed routing (`bendPoints`) is retained across the `autolayout_enabled` toggle. Turning autolayout off no longer clears any edge's routing by itself — whatever routing and positions were current at that moment remain exactly as they were.
- Routing validity is tracked per node, not per diagram: a node is "stale for routing" only once an author manually drags it while `autolayout_enabled` is `false`. An edge falls back to the direct point-to-point curve only when at least one of its own two endpoints is stale — every other edge in the same diagram is unaffected.
- The manual layout control ("Tune layout"), after recomputing positions once, also attaches fresh routing to every edge and clears every node's stale flag — the resulting diagram is indistinguishable from one currently under autolayout, until the author's next manual drag.
- Adding a new step while `autolayout_enabled` is `false` does not mark any *other* node stale; only the dragged node(s) a change actually moves are affected.
- **Supersedes** the not-yet-archived `flow-elk-edge-routing` change's Decision 4 ("Manual mode is untouched by construction"), its Non-Goal "Not changing anything about manual mode", and its spec scenario "Manual-mode connections always render as a direct curve". Those documented the opposite of the behavior above and are corrected by this change rather than carried forward.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `flow-management`: the "Client-side Flow diagram and Flow authoring UI" requirement gains an explicit, per-edge routing-validity model — an edge's ELK-computed route survives the autolayout toggle and the manual layout control, and is invalidated only for edges touching a node that was actually manually moved.

## Impact

- Frontend only: `plugins/flows/frontend/src/lib/flowLayout.ts`, `flowLayout.test.ts`, `FlowEdges.tsx`, `FlowEdges.test.ts`, `FlowCanvasEditor.tsx`, `FlowGraph.tsx`. No backend/API/model change, no migration — `Flow.steps[].position` remains the only persisted layout data; routing stays derived, render-time-only data.
- Sequencing: `flow-elk-edge-routing` is complete (21/21 tasks) but not yet archived, and its own design/spec text asserts the opposite manual-mode behavior this change introduces. This change's spec delta is the final word on manual-mode routing behavior; `flow-elk-edge-routing` should be archived together with this change (or corrected first) so the canonical `flow-management` spec never states the superseded behavior.
