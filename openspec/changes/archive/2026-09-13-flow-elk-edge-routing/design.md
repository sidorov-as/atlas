## Context

`flowLayout.ts`'s `computeFlowAutolayout()` calls `elk.layout()` and keeps only `result.children[].x/y` (`raw`), which then goes through `alignFlowPositions()` → `alignSiblingColumns()` — a post-ELK pass that snaps a node's whole subtree to its rightmost sibling's column along the layering axis, to avoid a narrower sibling's node clipping a curve headed to a wider one (see that function's own header comment). `result.edges[].sections[].bendPoints` — ELK's own routed path for each edge, computed in the same layout pass as the node positions — is never read at all. `FlowEdges.tsx`'s `FlowTransitionEdge` instead calls React Flow's `getSmoothStepPath({sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition})`, which only ever sees an edge's two endpoints.

This was investigated once already, during `flow-autolayout-modes` (task 6.1 spike, recorded in that change's archived design.md): naively rendering `bendPoints` was rejected because `alignSiblingColumns`'s shift moves a subtree's nodes by a delta computed after ELK already produced `bendPoints`, so an edge whose two ends belong to differently-shifted subtrees would have its `bendPoints` detach from its nodes (verified on `cancellation-flow`).

This change revisits that conclusion with new evidence. Given three flows reported as visually broken (`test-branch-within-branch`, `test-skip-level-bypass`, `test-uneven-branch-lengths` — three of the sixteen synthetic `test-*` Flows seeded specifically to stress ELK autolayout), direct experimentation shows:

1. **Raw `elk.layout()` output already avoids every one of the three overlaps/crossings**, with no app code involved — confirmed by geometrically checking `bendPoints` against every other node's rectangle (0 intersections in all three cases) and, for the two-branches-into-one-target case, checking whether the two edges' `bendPoints` cross each other (they don't).
2. **`alignSiblingColumns` is not always the culprit.** Diffing raw ELK positions against `alignFlowPositions()`'s output for the same three graphs:
   - `test-uneven-branch-lengths`: alignment changes **nothing** — every node's aligned position equals its raw ELK position. The reported overlap here is caused *solely* by rendering through `getSmoothStepPath` instead of `bendPoints`.
   - `test-skip-level-bypass`: alignment shifts every node downstream of the fork (`s3`, `s4`, `s5`, `s6`) by the **same** delta (+480 along the layering axis). A uniform per-edge-endpoint delta is trivially safe to apply to that edge's `bendPoints` too.
   - `test-branch-within-branch`: alignment shifts different siblings by **different** deltas (0 / 240 / 480, depending on branch). This is a live instance of the exact problem the 2025 spike flagged on `cancellation-flow` — no single delta translates this edge's `bendPoints` correctly.

So the "detachment" risk from the earlier spike is real, but narrower than it appeared: it only affects edges whose two endpoints receive different alignment deltas, not every edge in an autolayout-computed diagram. Two of the three reported flows don't hit it at all.

## Goals / Non-Goals

**Goals:**
- Render an autolayout-computed edge along ELK's own routed path (`bendPoints`) instead of a naive two-point curve, whenever doing so is geometrically safe (both endpoints shifted by the same alignment delta, including zero).
- Fall back to today's `getSmoothStepPath` rendering, per edge, when it isn't safe — never render a detached or visibly wrong path.
- Keep `Flow.steps[].position` as the only persisted layout data. Edge routing is derived from a fresh `computeFlowAutolayout()` call and exists only for the render currently on screen; it is never written to `steps[]`, never sent to the save API, and has no bearing on `autolayout_enabled`'s on/off behavior (`mergeStepPositions`, `FlowFormPage.tsx`'s save payload — untouched by this change).
- Apply this identically to both places a Flow diagram renders: the editable canvas (`FlowCanvasEditor.tsx`) and the read-only view (`FlowGraph.tsx`), same as `flow-autolayout-modes` already keeps their position-resolution logic identical.

**Non-Goals:**
- Not fixing `alignSiblingColumns` itself to always produce a uniform shift. That's a real follow-up (see Open Questions) but a materially different, riskier change; this proposal accepts "some edges keep today's rendering" as a correct, bounded outcome rather than blocking on solving the harder alignment problem.
- Not changing anything about manual mode (`autolayout_enabled: false`). ELK never runs there today and still won't; those edges keep rendering via `getSmoothStepPath`, unchanged.
- Not persisting edge routing anywhere. No model field, no migration, no API change.
- Not touching the placeholder "add next step" connector (`buildPlaceholderEdges`) — it's a synthetic, dashed, non-ELK edge and stays exactly as it renders today.

## Decisions

### Decision 1: `alignSiblingColumns` returns each node's applied delta instead of discarding it
Today `alignSiblingColumns` mutates an internal `along` record in place and returns nothing. It's extended to also produce a `Record<stepId, number>` of the net delta applied to each node (0 for a node that was never shifted). `alignFlowPositions` threads this out as a second return value alongside the position map. This is the only structural change to the alignment pass itself — no change to *how* it decides to shift a subtree, only to what it reports having done.

**Alternatives considered**: recomputing each node's delta after the fact by diffing raw vs. aligned positions at the call site — rejected as redundant; the alignment pass already knows this number exactly, mid-computation, more cheaply and more reliably than a second pass reconstructing it from two position maps.

### Decision 2: Per-edge routing is computed once, alongside positions, in `computeFlowAutolayout`
A new function (name TBD at implementation, e.g. `computeFlowEdgeRouting`) takes the raw `bendPoints` per edge (from `result.edges[].sections[]`, keyed by `${sourceId}->${targetId}` to match `buildElkGraph`'s edge ids) and the per-node delta map from Decision 1, and returns `Record<edgeKey, {x, y}[]> | undefined` per edge:
- If `delta[sourceId] === delta[targetId]`: translate every point in that edge's `bendPoints` (start point, bend points, end point) by that single delta along the layering axis (the same axis `alignSiblingColumns` operates on — `x` for left-right, `y` for top-down); the cross axis is untouched, matching how node positions themselves are only ever adjusted along one axis.
- Otherwise: the edge gets `undefined` routing — the render layer's signal to fall back to `getSmoothStepPath`.

`computeFlowAutolayout`'s return type grows from `FlowPositions` to something like `{ positions: FlowPositions, edgeRouting: FlowEdgeRouting }`. Every call site (`FlowCanvasEditor.tsx`'s passive layout effect, its `handleAutoLayout`, `FlowGraph.tsx`'s canvas effect) updates to destructure both instead of treating the return value as positions directly.

**Alternatives considered**: attempting a partial/best-effort translation for the mismatched-delta case (e.g., interpolate a delta across intermediate bend points) — rejected per the earlier spike's own conclusion: a bend point isn't a node, so there's no principled answer to "whose delta" applies to an interior point of a shifted edge; a clean per-edge fallback is simpler, correct, and no worse than today's behavior for exactly the edges it applies to.

### Decision 3: `buildFlowNodesAndEdges` attaches routing to `Edge.data`; `FlowTransitionEdge` branches on its presence
`buildFlowNodesAndEdges` (or its call sites) look up each edge's routing by the same `${sourceId}->${targetId}` key and set it as `data.routing` on the corresponding React Flow `Edge`. `FlowTransitionEdge` (`FlowEdges.tsx`) checks `data?.routing`:
- Present → build the path as a polyline through the translated points (straight segments; ELK's own `bendPoints` are already orthogonal-ish for a layered layout, so no additional smoothing is needed to match today's visual language) and place the label at the midpoint of total path length rather than `getSmoothStepPath`'s two-point midpoint.
- Absent → exactly today's `getSmoothStepPath(...)` call, unchanged.

Both branches keep the same `<BaseEdge>`/`markerEnd`/label-wrapping treatment; only the `d` attribute's construction and label-position math differ.

**Alternatives considered**: a second edge type (`flow-transition-routed`) selected at the `edges` array level instead of branching inside one component — rejected as pure duplication; the two paths share every visual concern (arrowhead, label box, hover state) except how `d`/label position are computed, which is a few lines either way.

### Decision 4: Manual mode is untouched by construction, not by a special case
Because `edgeRouting` only ever exists as output of `computeFlowAutolayout()`, and manual mode (`autolayout_enabled: false`) never calls it (per `flow-autolayout-modes` Decision 4), there is no routing data to attach to any edge while in that mode — `data.routing` is simply never set, and `FlowTransitionEdge` falls back to `getSmoothStepPath` the same way it does for a same-diagram edge that hit Decision 2's mismatched-delta case. No `if (autolayoutEnabled)` branch is needed anywhere in the rendering path for this reason.

## Risks / Trade-offs

- **[Risk] Flows with heavy sibling-depth imbalance (like `test-branch-within-branch`) still render some edges the old way.** → **Mitigation**: this is a strict improvement, never a regression — every edge that would have rendered via `getSmoothStepPath` today still can; some now render correctly instead. Tracked as a real follow-up (Open Questions), not silently accepted as "fixed."
- **[Risk] Label placement on a multi-point path needs its own midpoint-of-total-length calculation**, unlike `getSmoothStepPath`'s built-in `labelX`/`labelY`. → **Mitigation**: straightforward arc-length walk over the polyline's segments; unit-testable in isolation against hand-fed point arrays, same pattern `alignFlowPositions` already uses for testability (`flowLayout.test.ts`).
- **[Risk] `elk.layout()`'s edge section coordinates must be confirmed to already share the same coordinate space as `result.children[].x/y`** (both root-relative), so Decision 2's translation needs no extra transform. → **Mitigation**: verify explicitly as an early implementation task against a real `elk.layout()` result before building the translation logic on top of an assumption.
- **[Risk] Read-only `FlowGraph.tsx` and editable `FlowCanvasEditor.tsx` could drift** (one gets routed edges, the other doesn't) the same way `flow-autolayout-modes` had to fix after the fact for positions. → **Mitigation**: explicit task to thread `edgeRouting` through both call sites in the same change, verified against the same seeded Flows in both views.

## Migration Plan

None. Purely a frontend rendering change: no model field, no API contract change, no data migration. Ships and rolls back like any other frontend change.

## Open Questions

- Whether to eventually address the harder case directly — extending `alignSiblingColumns` (or replacing it) so every shift is uniform per edge, removing the fallback path entirely — left as a follow-up, since it's a materially larger and riskier change than this one (see Non-Goals).
- Whether a visibly-different styling for a "we couldn't route this one cleanly" fallback edge is worth adding (e.g., so it doesn't look identical to a real ELK-routed edge) — left to implementation/design review; today's rendering is already indistinguishable in that sense, so this is not a regression either way.
