## 1. Backend validation

- [x] 1.1 In `plugins/flows/backend/atlas_plugin_flows/models.py`'s `validate_steps`, remove the `incoming_from` tracking and its "more than one incoming transition" rejection. Keep unknown-target and cycle detection unchanged.
- [x] 1.2 Update/add backend tests: a Flow with two steps targeting the same step id now saves successfully; unknown-target and cycle rejection tests still pass unchanged; add a self-transition (`A → A`) test if one doesn't already exist, asserting it's still rejected as a cycle.

## 2. Frontend validation

- [x] 2.1 In `plugins/flows/frontend/src/components/flowSteps.ts`'s `validateFlowSteps`, remove the `incoming` map and its "branches cannot reconverge" error. Keep unknown-target and cycle detection unchanged.
- [x] 2.2 In `canUseTransition`, remove `'reconverge'` from the accepted-error substring filter (only `'unknown'`/`'cycle'` remain).
- [x] 2.3 Update/add frontend unit tests for `validateFlowSteps`/`canUseTransition` mirroring 1.2's cases.

## 3. Canvas layout: DAG-safe edge rendering

- [x] 3.1 In `plugins/flows/frontend/src/lib/flowLayout.ts`, change `buildElkGraph` and `buildFlowNodesAndEdges` to derive their edge list from `childIdsOf(step)` over every step in `steps[]` directly, instead of from `LayoutNode.children` — so a target's second-plus incoming transition is no longer dropped by `buildForest`'s `placed` filter. Keep `buildForest`'s one-node-per-step placement (and its cycle/mid-edit tolerance) as the source of the node list and of layout order.
- [x] 3.2 Verify `transitionLabel` still resolves correctly per (source, target) pair when a target has multiple incoming edges — each edge's label should come from its own source step's transition entry, independent of the others.
- [x] 3.3 Add/update a `flowLayout.ts` unit test: two steps both transitioning to the same target step produces two edges into that target in `buildFlowNodesAndEdges`'s output (and two in `buildElkGraph`'s), not one.

## 4. Canvas layout: multi-parent column alignment

- [x] 4.1 In `alignSiblingColumns`, extend the alignment logic so a node with more than one parent aligns to the furthest-along-the-layering-axis column among *all* its parents' resolved columns (same rule as ordinary siblings), rather than only the column implied by whichever parent's forest traversal reaches it first.
- [x] 4.2 Ensure a second (or later) parent's pass over an already-aligned multi-parent child is a no-op rather than double-shifting it or its subtree.
- [x] 4.3 Add a unit test: a step with two parents in different columns ends up aligned to the rightmost (or bottommost, for top-down layout) of the two parents' columns.

## 5. Canvas UX

- [x] 5.1 Confirm `FlowCanvasEditor.tsx`'s `handleConnect` needs no code change beyond what 2.1/2.2 already produce — verify manually that dragging a connection onto an already-targeted step now succeeds instead of showing the "branches cannot reconverge" banner, and that unknown-target/cycle attempts still show their existing banners.
- [x] 5.2 Manually verify on the canvas: two branches from a condition step, each connected to the same downstream "Success"-themed step, render as one shared node with two distinct incoming edges (with independent labels, if set).

## 6. Spec/docs cleanup

- [x] 6.1 Confirm no other references to "strict divergence-only tree" / "reconverge" remain in code comments (e.g. `flowLayout.ts`'s file header comment currently describes the model as "validated server-side as a strict, divergence-only tree") — update them to describe the new DAG (cycles rejected, reconvergence allowed) model.
