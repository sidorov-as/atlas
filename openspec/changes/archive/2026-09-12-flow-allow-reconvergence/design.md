## Context

Flow steps form a graph via `next_step`/`next_steps[]` transitions, validated both client-side (`flowSteps.ts`'s `validateFlowSteps`) and server-side (`models.py`'s `validate_steps`). Today a step id may be targeted by at most one incoming transition ("reconvergence" is rejected) — the graph is required to be a strict tree.

That constraint traces back to `add-flows`'s design.md Decision 4: it let the canvas ship with a ~50-line hand-rolled DFS layout instead of a layered-layout library. `flow-canvas-elk-layout` then adopted ELK (a Sugiyama-style layered layout engine that natively handles multiple incoming edges per node) purely for layout quality, explicitly without revisiting the tree constraint. The technical reason for the constraint no longer holds; this change removes it.

The canvas's current layout code (`flowLayout.ts`) still reflects the tree assumption in a way that matters for this change: `buildForest()` walks `steps[]` into a forest of `LayoutNode` trees, placing each step exactly once (`placed` set) and — critically — **filtering a step's children to those not yet `placed`**. A step's second incoming transition, if it existed, wouldn't just be rejected by validation; it would be silently absent from the rendered diagram, because the second parent's edge to an already-placed child is dropped by that filter before it ever reaches ELK.

## Goals / Non-Goals

**Goals:**
- Allow two (or more) different steps to transition to the same target step id, in both the persisted data model's validation and the canvas's rendering.
- Every transition — including a step's second-plus incoming edge — renders as a real edge on the canvas; none are silently dropped.
- Multi-parent steps get a visually consistent column position, using the same alignment rule already applied to ordinary siblings.

**Non-Goals:**
- Cycle detection is unchanged. Self-transitions (`A → A`) and any longer cycle remain rejected by the existing DFS-based cycle check, on both frontend and backend. Discussed and explicitly deferred: a workaround pattern of routing a cycle through an explanatory intermediate node (`A → Note → A`) is *also* still a cycle and would still be rejected — supporting that pattern would mean relaxing cycle detection itself, a materially bigger and riskier change (Flow diagrams are hand-authored documentation, not an executed graph, so "cycle" here is a structural/rendering concern, not a runtime-safety one — but relaxing it is still out of scope here).
- No change to the `FlowStep`/transition JSON shape. `next_step`/`next_steps[]` already reference targets purely by id; nothing about how a transition is declared needs to change for it to target an already-targeted id.
- No change to how transition labels are stored or edited (`updateTransitionLabel`, `removeTransition`) — a label already lives on the source side's transition entry, so two independent incoming edges into a shared step already carry independent labels with no further work.

## Decisions

### Decision 1: Drop the reconvergence check; keep unknown-target and cycle checks as-is
`validateFlowSteps` (`flowSteps.ts:69-79`) currently pushes an error when a second step targets an id already recorded in its `incoming` map. That branch is removed; the `incoming` map itself can go too, since nothing else reads it. `canUseTransition` (`flowSteps.ts:79`) stops filtering the `'reconverge'` substring out of its accepted-error check — there's no such error left to filter. The backend mirror, `validate_steps`'s `incoming_from` tracking and its "more than one incoming transition" rejection (`models.py:144-182`), is removed the same way. Cycle detection (the `visiting`/`visited` DFS in both files) and unknown-target detection are untouched.

### Decision 2: Rebuild the layout pipeline around a real DAG, not a forest-of-trees
`buildForest`'s per-step `placed` dedup exists to keep rendering safe against an *invalid* mid-edit graph (a cycle, or — until now — a reconvergence) so the canvas doesn't infinite-loop or double-render a node while an author is mid-typo in the JSON rail. That safety property must survive: a node still renders exactly once. What changes is that a second (or third...) *edge* into an already-placed node must now survive too, instead of being dropped by the `!placed.has(child.id)` filter.

Concretely: `buildForest` keeps producing one `LayoutNode` per step (so recursion still terminates and a node is still visually singular), but the two functions that read it — `buildElkGraph` and `buildFlowNodesAndEdges` — stop deriving their edge list purely from `LayoutNode.children` (parent-owns-child, one edge per placement) and instead emit one edge per transition found by `childIdsOf(step)` for every step in `steps[]`, regardless of whether that transition's target was "placed" by a different parent first. The node list stays exactly as `buildForest` produces it (one entry per step, first-reachable-root-first) — only the edge list changes from "edges implied by the forest's parent/child links" to "edges implied by the data's transitions directly."

This keeps the existing cycle-tolerant safety behavior (an in-progress cyclic edit still renders every node exactly once, per Decision 1's Non-Goal) while making reconvergence — now valid — actually show up.

### Decision 3: Multi-parent column alignment — rightmost/bottommost wins
`alignSiblingColumns` (`flowLayout.ts:221-239`) currently walks the forest and, for each node's direct children, shifts every child's whole subtree to align with the child furthest along the layering axis (rightmost in a left-right layout, bottommost in top-down) — so sibling columns read as a clean grid. With a multi-parent node, "its parent's children" is now ambiguous: the node appears as a child under more than one parent's alignment pass.

Chosen approach: treat a multi-parent node the same as any other sibling for the purposes of this rule — whichever of *all* its parents' resolved columns is furthest along the layering axis wins, and that node (and its own subtree) shifts to match. This requires `alignSiblingColumns` to key off "already-computed column per node id" (which it already does via the `along` map) rather than assuming a single shift-owning parent; the second (and later) parent's pass over the same child becomes a no-op once the child is already at or past the target column, rather than double-shifting it. This is the same visual rule already governing ordinary siblings, just applied without assuming a unique parent.

**Considered and deferred — Decision 3b**: drop the manual `alignSiblingColumns` pass entirely for any node with more than one parent, and let ELK's own layered algorithm position it (it already computes a reasonable column for a DAG node with multiple incoming edges; the manual pass exists to make *sibling* columns tidier than ELK's raw output, not to fix DAG placement). This is simpler to implement and closer to "trust the layout engine" — but it means multi-parent nodes could align inconsistently with their sibling columns, which is a visible seam right at the interesting part of the diagram (the reconvergence point). Deferred rather than rejected: worth reconsidering once real Flows with reconvergence exist and we can see whether Decision 3's rule actually produces better results in practice, or whether it's solving a problem ELK already handles well enough on its own.

### Decision 4: Canvas drag-to-connect simply stops rejecting this case
`FlowCanvasEditor.tsx`'s `handleConnect` (line ~275) calls `canUseTransition`, which (per Decision 1) no longer returns a `'reconverge'` error for this case. No separate UI change is needed — the existing success path (`addTransition`, canvas re-render) already runs whenever `canUseTransition` returns `null`. The inline error banner (`setConnectError`) simply stops firing for this specific case; it still fires for an unknown-target or cycle-introducing attempt.

## Risks / Trade-offs

- **Layout quality for reconvergence is untested against real data.** ELK handles multi-parent DAGs natively, but Decision 3's rightmost-column rule is a hypothesis about what looks good, not something validated against a real reconverging Flow yet. If it produces bad layouts once authors start using this, Decision 3b is the fallback to try next.
- **Silent-drop bug (pre-existing) becomes visible as a real feature.** Before this change, a reconverging edge was rejected by validation, so `buildForest`'s edge-dropping behavior was unreachable in valid data (only visible transiently while a JSON edit was mid-invalid). After this change, that code path is exercised by every valid, intentionally-reconverging Flow, so Decision 2's fix is load-bearing, not cosmetic.
- **Existing Flows are unaffected.** Every currently-persisted Flow already satisfies the (now-relaxed) old rule, so this change is purely additive from a data standpoint — no migration, no re-validation pass needed on existing rows.
