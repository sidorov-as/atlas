## Context

`FlowCanvasEditor.tsx`'s passive layout effect currently behaves like this:

```
if (autolayoutEnabled) {
  const { positions, edgeRouting } = computeFlowAutolayout(steps, layoutDirection)
  apply positions; attach edgeRouting to edges
} else {
  // edgeRouting is simply never computed here
  apply stored positions; edges get no routing => FlowTransitionEdge falls back
  to getSmoothStepPath for all of them
}
```

`handleAutoLayout` (the manual layout control, "Tune layout") calls `computeFlowAutolayout` once and attaches `edgeRouting` directly via `setEdges`/`setNodes` — bypassing the passive effect. But the passive effect re-runs on the very next `steps` mutation (including the next drag), sees `autolayoutEnabled === false`, and drops the routing it just set, because the effect's `else` branch has no memory of "ELK ran once, a moment ago, and nothing has invalidated that since."

The result: both bugs reported against the running app (`/flows/2/edit`, `/flows/32/edit`) — the toggle changing visuals with identical positions, and "Tune layout" not sticking — trace to the same missing concept: **the effect treats `autolayoutEnabled` itself as the routing-validity signal, when the real signal is "has anything moved since routing was last computed."**

This design does not revisit `computeFlowAutolayout`'s internals (ELK invocation, `alignSiblingColumns`'s delta tracking, the per-edge uniform/mismatched-delta fallback) — those are unchanged and already validated. It only changes when the *result* of that computation is discarded.

## Goals / Non-Goals

**Goals:**
- Toggling `autolayout_enabled` off, by itself, changes nothing about what's on screen — no position, no edge's routing.
- Manually dragging a node while `autolayout_enabled` is `false` invalidates routing only for the edges incident to that node; every other edge in the diagram keeps its last-computed ELK routing untouched.
- "Tune layout" produces a state indistinguishable from "autolayout was briefly on, then off" — every edge gets fresh routing, and it all stays until the next manual drag.
- Apply identically to both diagram surfaces that call `computeFlowAutolayout` — the edit canvas (`FlowCanvasEditor.tsx`) and, to the extent it's relevant, the read-only view (`FlowGraph.tsx`).

**Non-Goals:**
- Not changing `computeFlowAutolayout`, `alignSiblingColumns`, or the ELK integration itself.
- Not persisting routing or a "stale" flag to `Flow.steps[]` or any backend field — this stays derived, render-time-only client state, same as before.
- Not changing how a newly-added step is positioned in manual mode (out of scope per the earlier discussion — [[flow-manual-mode-routing-retention]] only concerns routing retention/invalidation, not placement of new steps).
- Not changing manual position-persistence-on-drag itself (already correct, unrelated to this bug).

## Decisions

### Decision 1: Track routing validity as a set of "stale" node ids, not a boolean gated on `autolayoutEnabled`
Introduce local component state (`staleNodeIds: Set<string>`) alongside the existing `edgeRouting` state, in both `FlowCanvasEditor.tsx` and (where applicable) `FlowGraph.tsx`. An edge renders its stored ELK routing if and only if a routing entry exists for it **and** neither its source nor target id is in `staleNodeIds`. Absence of a routing entry (e.g. a brand-new edge that's never had ELK run since it was created) falls back to `getSmoothStepPath` exactly as today — no special-casing needed there, matching the one part of the old design (`flow-elk-edge-routing` Decision 4) that reasoned correctly, just applied to the wrong condition.

**Alternatives considered**: a boolean `routingIsFresh` flag for the whole diagram — rejected because it can't express "one dragged node's edges fall back, the rest keep ELK routing," which the user explicitly wants (Q7 in the earlier discussion).

### Decision 2: The passive layout effect no longer clears routing/staleness on its own when autolayout is off
Today's `else` branch (autolayout off) does nothing with routing at all — which, combined with `edgeRouting` being effect-local state recreated as `undefined` by default, is what wipes it. Instead: when `autolayoutEnabled` is `false`, the passive effect leaves `edgeRouting` and `staleNodeIds` untouched entirely (it only ever touches them in the `autolayoutEnabled === true` branch, which continues to run ELK on every relevant `steps` change and always resets `staleNodeIds` to empty, since a full recompute makes everything fresh by definition).

**Alternatives considered**: recomputing `edgeRouting` on toggle-off from whatever's currently on screen — rejected as unnecessary; the values already in state at the moment of toggling are exactly what should keep rendering, so the simplest correct move is to not touch them.

### Decision 3: Manual drag marks only the dragged node stale
The existing manual-drag handler (already responsible for persisting `position` while `autolayoutEnabled` is false, per the current, correct, unchanged spec requirement) is extended to also add that node's id to `staleNodeIds` on drag end. Adding a new unconnected step does not mark any other node stale (it has no pre-existing edges with routing entries to invalidate).

**Alternatives considered**: marking stale on every `onNodesChange` position event (fires continuously during a drag, not just at the end) — rejected as wasteful; nothing needs the edge to visually flip to fallback mid-drag versus at drag-end, and computing/comparing on every mousemove-driven event is unnecessary churn.

### Decision 4: "Tune layout" clears `staleNodeIds` entirely, same as a continuous-autolayout recompute
`handleAutoLayout` already calls `computeFlowAutolayout` once and attaches the resulting `edgeRouting`. It's extended to also reset `staleNodeIds` to empty — every node's routing is fresh as of that click, identically to what a continuous-autolayout recompute does. This is the mechanism that makes "Tune layout" durable: the very next passive-effect run (autolayout still `false`) now hits Decision 2's untouched-state path and leaves this fresh routing alone, instead of silently discarding it.

**Alternatives considered**: none seriously — this directly matches the user's stated requirement ("Tune layout should realign once, as if autolayout had been briefly turned on and off").

### Decision 5: `FlowGraph.tsx` (read-only detail page) needs no `staleNodeIds` state at all
The read-only page has no drag interaction, so there is no event that could ever mark a node stale there. It only ever needs `edgeRouting` from a fresh `computeFlowAutolayout` call when `autolayout_enabled` is `true` — unchanged from today. If `autolayout_enabled` is `false`, it never had live ELK routing to retain in the first place (each page load is a fresh mount, not a live toggle session), so its current behavior (no routing, direct curves) is already correct and untouched by this design.

## Risks / Trade-offs

- **[Risk] `staleNodeIds` is plain component state — a page refresh loses it, so a refreshed manual-mode diagram that had fresh "Tune layout" routing goes back to direct curves.** → **Mitigation**: acceptable and consistent with the existing design's treatment of routing as derived, session-local data (proposal.md's Impact: never persisted). A refresh already re-derives everything from `Flow.steps[].position`; routing was never meant to survive that boundary.
- **[Risk] Deleting a step or transition could leave a stale edge-routing-map entry keyed by an id that no longer exists.** → **Mitigation**: harmless — an edge lookup by a stale key that no longer matches any rendered edge is simply never read; no cleanup pass is required, but implementation should confirm the lookup is by current edge id, not an index, so this can't silently attach to the wrong edge.
- **[Risk] This duplicates a small amount of "what changed" tracking that conceptually overlaps with React Flow's own change-detection.** → **Mitigation**: scoped deliberately to just node ids (a `Set<string>`), the smallest state that answers "is this edge's routing still valid" — no attempt to generalize into a broader diffing system.

## Migration Plan

None. Purely a frontend rendering/state change: no model field, no API contract change, no data migration. Ships and rolls back like any other frontend change.

## Open Questions

- Whether `staleNodeIds` should live in the same state container as `edgeRouting` (e.g., one `layoutState` object) or as a sibling `useState` — an implementation detail with no behavioral consequence, left to whoever writes the code.
- Whether to also mark a node stale when its `position` is changed programmatically via the JSON panel editor (not a canvas drag) while `autolayout_enabled` is `false` — likely yes, for consistency, since it's the same underlying "this position no longer matches what routing was computed for" condition, but not explicitly covered by the original bug report; flagged for confirmation during implementation.
