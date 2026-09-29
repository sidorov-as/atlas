## 1. Track routing validity per node

- [x] 1.1 In `FlowCanvasEditor.tsx`, add `staleNodeIds: Set<string>` state alongside the existing `edgeRouting` state.
- [x] 1.2 In the passive layout effect's `autolayoutEnabled === true` branch, reset `staleNodeIds` to empty every time `computeFlowAutolayout` runs (a full recompute makes every node fresh by definition) — unchanged behavior otherwise.
- [x] 1.3 In the passive layout effect's `autolayoutEnabled === false` branch, remove whatever logic currently clears/omits `edgeRouting` — leave both `edgeRouting` and `staleNodeIds` completely untouched when this branch runs.

## 2. Invalidate routing on manual drag, not on toggle

- [x] 2.1 In the manual-drag handler that persists a step's `position` while `autolayoutEnabled` is `false`, add the dragged step's id to `staleNodeIds` on drag end.
- [x] 2.2 Confirm toggling `autolayout_enabled` itself (the switch's own change handler) does not add to, clear, or otherwise touch `staleNodeIds` or `edgeRouting` — the fix for the toggle bug is that this handler does nothing to either.

## 3. Make "Tune layout" (manual layout control) durable

- [x] 3.1 In `handleAutoLayout`, after computing and attaching `edgeRouting` as it does today, also reset `staleNodeIds` to empty.
- [x] 3.2 Verify (manually, then via the test in 5.2) that after clicking "Tune layout" and then making an unrelated Flow change (e.g. editing a step's label via the JSON panel), all edges keep their routed appearance — the passive effect's now-untouched `else` branch (task 1.3) should leave it alone.

## 4. Edge rendering respects per-edge staleness

- [x] 4.1 In `FlowEdges.tsx` / wherever `Edge.data.routing` is attached (`buildFlowNodesAndEdges` or its call sites), only attach a routing entry to an edge when neither its source nor target id is in `staleNodeIds`; otherwise leave `data.routing` unset so `FlowTransitionEdge` falls back to `getSmoothStepPath` for that edge only.
- [x] 4.2 Confirm a new edge (added since the last `computeFlowAutolayout`/`handleAutoLayout` run, so it has no entry in `edgeRouting` at all) renders via the existing fallback path unchanged.

## 5. Tests

- [x] 5.1 Add a test (component-level or logic-level, matching the existing style in `flowLayout.test.ts` / `FlowEdges.test.ts`) covering: toggling `autolayoutEnabled` from `true` to `false` with no other change leaves every edge's routing/rendering identical before and after.
- [x] 5.2 Add a test covering: `handleAutoLayout` runs, then an unrelated `steps` change occurs (autolayout still off) — routing is still present on every edge.
- [x] 5.3 Add a test covering: after `handleAutoLayout` runs, dragging one node invalidates only that node's incident edges' routing, leaving all other edges' routing intact.
- [x] 5.4 Add a test covering: a newly added, never-autolaid-out connection renders via the direct-curve fallback.

## 6. Manual verification

- [x] 6.1 On `/flows/2/edit` (verified via DOM inspection; `/flows/32/edit` not separately checked), toggle `autolayout_enabled` off and confirm the diagram visually does not change.
- [x] 6.2 On the same flow, with autolayout off, click "Tune layout", then make an unrelated edit (edited a transition label via the JSON panel) and confirm the tidied edges remain tidied.
- [x] 6.3 With autolayout off and a freshly tidied diagram, drag one node and confirm only its own connections revert to a direct curve, with all others staying routed. Verified live on `/flows/2/edit`: dragging "Booking DB" (s3) fell back only `s2->s3` and `s3->s4`; every other edge (`s1->s2`, `s2->s7`, `s4->s5`, `s5->s6`, `s6->s8`, `s8->s9`) kept its routed path.
- [x] 6.4 Confirm `Flow.steps[].position` in the saved JSON is unaffected by any of the above — routing/staleness state never appears in persisted data.

## 7. OpenSpec hygiene

- [x] 7.1 Before or alongside archiving this change, ensure `flow-elk-edge-routing`'s Decision 4, its "Not changing anything about manual mode" Non-Goal, and its "Manual-mode connections always render as a direct curve" spec scenario are not left as the final merged text for `flow-management` — this change's `MODIFIED Requirements` block is the version that should land. Superseded: `flow-layout-engine-rewrite` deletes the entire routing/staleness concept this change and `flow-elk-edge-routing` both modified, and its own spec delta (synced last, per its tasks.md 8.3) is the version that actually lands — neither this change's nor `flow-elk-edge-routing`'s routing/staleness text survives in the merged `flow-management` spec.
