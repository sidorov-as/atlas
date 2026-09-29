## Why

Flow steps today form a strict, divergence-only tree: a step id may be the target of at most one incoming transition. This forces authors documenting a real process — e.g. two branches of a condition both leading to the same "Success" outcome, or two different code paths emitting the same downstream event — to duplicate the target step once per incoming branch, even though it's logically one step. The original tree-only constraint was adopted so the canvas could ship without a layered-layout library; that library (ELK) was adopted for layout quality shortly after, but the reconvergence restriction was never revisited. It's no longer buying us anything.

## What Changes

- Allow a step id to be the target of more than one transition (`next_step`/`next_steps[]` from different source steps). Branches may now diverge **and** reconverge on a shared step.
- Remove the "reconverge" validation error on both the backend (`validate_steps`) and the frontend (`validateFlowSteps`/`canUseTransition`), while keeping the existing "unknown target" and "cycle" checks unchanged — self-transitions and any other cycle remain rejected exactly as today; this change does not touch cycle detection.
- Rework the canvas's step→layout pipeline (`buildForest`/`buildElkGraph`/`buildFlowNodesAndEdges` in `flowLayout.ts`) from a forest-of-trees (which silently drops a step's second incoming edge today, rather than just refusing to draw it) into a proper DAG passed to ELK, so every transition renders regardless of how many incoming edges its target has.
- Extend the sibling-column alignment pass (`alignSiblingColumns`) to align a step with multiple parents to the rightmost/bottommost of those parents' columns — the same rule already used for ordinary siblings under one parent — rather than leaving it at ELK's raw position.
- Allow a drag-to-connect gesture on the canvas to complete a connection to a step that already has an incoming transition; the existing "branches cannot reconverge" rejection banner no longer fires for this case (unknown-target and cycle rejections are unchanged).

**Considered and deferred**: fully delegating multi-parent alignment to ELK's own layered algorithm (no manual post-pass for such nodes) was considered as a simpler alternative. Deferred in favor of the rightmost-column rule above, which stays visually consistent with how ordinary sibling columns already align; revisit if the rightmost-column rule produces poor layouts in practice once real reconverging Flows exist.

Not in scope: cycle handling, self-transitions, and any "explanatory node to describe a loop" pattern were explicitly discussed and left untouched — those remain rejected by the unchanged cycle check.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `flow-management`: the "Step transitions form a strict divergence-only tree" requirement changes to permit multiple incoming transitions per step id (renamed in the delta to reflect the new behavior); the "Invalid edits are rejected on save" scenario's "strict-tree rule" wording is updated to reflect that only unknown-target and cycle violations block a save now.
- `visual-flow-editor`: the "Visual editor structural feedback" requirement's drag-to-connect rejection no longer includes "gives a target more than one incoming edge"; the "Attempt to reconverge branches" scenario is removed and replaced with a scenario confirming reconverging connections succeed. The "Synchronized Visual and JSON modes" requirement's structural-validity gate description drops "no target with more than one incoming transition" from its list of checks.

## Impact

- Backend: `plugins/flows/backend/atlas_plugin_flows/models.py` (`validate_steps`), exercised via `api/schemas.py`.
- Frontend: `plugins/flows/frontend/src/components/flowSteps.ts` (`validateFlowSteps`, `canUseTransition`), `plugins/flows/frontend/src/components/FlowCanvasEditor.tsx` (`handleConnect`), `plugins/flows/frontend/src/lib/flowLayout.ts` (`buildForest`, `buildElkGraph`, `buildFlowNodesAndEdges`, `alignSiblingColumns`).
- No API/schema shape change — `next_step`/`next_steps` already reference targets by id; only the validation rule and the layout algorithm change.
- No database migration; existing persisted Flows are all already valid trees, so this change only widens what's accepted going forward.
