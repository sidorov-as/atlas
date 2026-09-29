## Context

`flowLayout.ts` currently drives both the editable canvas (`FlowCanvasEditor.tsx`) and the read-only canvas (`FlowGraph.tsx`, also used for PNG/SVG export) through one pipeline: `buildElkGraph` (ELK with per-node `FIXED_POS` ports, Coffman-Graham layering) → `computeFlowAutolayout` → `alignFlowPositions`/`alignSiblingColumns` (post-hoc column snapping with collision checks) → `computeEdgeRouting` (translates ELK's `bendPoints` by each node's alignment delta, or drops the edge to a fallback curve if its two endpoints moved by different deltas). `FlowCanvasEditor.tsx` additionally tracks `staleNodeIds` so a manually-dragged node's own connections fall back to a direct curve while every other edge keeps its last-computed route across the `autolayout_enabled` toggle.

Three specs (`flow-elk-edge-routing`, complete but unarchived; `flow-manual-mode-routing-retention`, in progress; and the original `flow-autolayout-modes`, already archived) built this pipeline incrementally, each patching a bug the previous one's simplifications exposed. A throwaway sandbox at `/flows/debug` demonstrated that dropping the whole routing/alignment layer — plain `dagre` or plain `elkjs` layered layout, node positions only, edges always drawn live by `@xyflow/react` off the node's real handle — produces clean diagrams without any of that machinery, and does so through two well-tested library defaults instead of ~250 lines of bespoke ELK post-processing.

## Goals / Non-Goals

**Goals:**
- Delete the custom ELK ports/Coffman-Graham/`alignSiblingColumns`/bendpoint-routing/staleness system, replacing it with a plain layered layout selectable between `dagre` and `elkjs`.
- Make the layout engine a persisted, per-Flow, user-facing setting (not a client-only preference), following the exact pattern `layout_direction` already established.
- Keep `flowLayout.ts`/`FlowEdges.tsx` as the single shared implementation for both the editable canvas and the read-only canvas/export — no forked code path.
- Improve the transition-edge label to grow/wrap/clamp with a tooltip and be directly clickable, matching `/flows/debug`.
- Preserve every other already-specified behavior unrelated to routing/alignment: `autolayout_enabled`/`layout_direction` semantics, deterministic placement of a toolbar-added or connected-added step, add-next placeholder collision avoidance, node visuals, structural validation, entity-ref staleness warnings.

**Non-Goals:**
- Obstacle-aware edge routing. This design deliberately does not attempt to route an edge around a node it visually crosses — that guarantee is being removed, not reimplemented differently.
- Any change to `FlowNodes.tsx`'s visuals, or to the picker/modal/structural-validation logic in `flowSteps.ts`, `FlowStepModal.tsx`, `FlowTransitionModal.tsx`.
- A per-viewer or per-browser layout-engine preference. The engine is a Flow-level fact, like `layout_direction`.
- Re-adding ELK ports/bendpoints for the `elk` engine option specifically. Both engine choices use the same plain, position-only layout style; `elk` is offered as an alternative node-placement algorithm, not as a path back to routed edges.

## Decisions

### Decision 1: Two engines, one shared position-only contract
`computeFlowAutolayout(steps, direction, engine)` returns `FlowPositions` only (no `edgeRouting`). Internally it dispatches to `layoutWithDagre` or `layoutWithElk`, each a direct port of `flowDebugLayout.ts`'s same-named functions: one `dagre.graphlib.Graph` (or one flat ELK graph) built fresh per call, one node per step at `FLOW_NODE_WIDTH`/`FLOW_NODE_HEIGHT`, one edge per transition with `estimateLabelSize()`-derived label dimensions so both engines reserve enough inter-layer space for a labeled edge. Neither engine declares ports, `FIXED_POS`, or any bendpoint/section extraction — dagre's result is read from `graph.node(id)` (center-to-top-left corrected), ELK's from `result.children[].x/y` directly.

*Alternative considered*: keep ELK's port-based routing for the `elk` engine option only, and only let `dagre` skip it (since dagre has no routing concept at all). Rejected — it would leave two structurally different code paths (one with a routing/staleness concept, one without) behind a single UI toggle, undermining the whole point of simplifying to "position only." A user switching engines mid-edit should not also toggle a routing feature on and off.

### Decision 2: `alignSiblingColumns` and everything downstream of it is deleted, not gated
`alignFlowPositions`, `alignSiblingColumns`, `computeEdgeRouting`, `handleAnchor`, `portId`/`stepIdFromPort`, and the `FlowEdgeRouting`/`FlowAlignmentDeltas` types are removed from `flowLayout.ts` entirely — not left in place behind a flag. `buildFlowNodesAndEdges` drops its `edgeRouting`/`staleNodeIds` parameters; an edge's `data` no longer carries a `routing` field.

*Rationale*: this code has no purpose once nothing produces `bendPoints` for it to translate. Keeping it dormant would be dead code inviting a future "let's turn routing back on" that this design explicitly argues against (see Non-Goals).

### Decision 3: Edge label — grow, clamp, tooltip, click-through to the modal
`FlowTransitionEdge` always computes its path via `getSmoothStepPath` (the `routing` branch is deleted). The label renders through `EdgeLabelRenderer` as an HTML div that grows with its text up to `FLOW_NODE_WIDTH`/`FLOW_NODE_HEIGHT` (mirroring `FlowDebugEdges.tsx`'s `estimateLabelSize`-driven cap and `-webkit-line-clamp` treatment), wrapped in a `Tooltip` showing the full label once clamped, with `pointerEvents: 'all'` and its own `onClick` that opens `FlowTransitionModal` for that edge — matching `/flows/debug`'s `onOpenTransitionModal` callback threaded through edge `data`.

*Change from today*: production's current label is `pointerEvents: 'none'` so a click passes through to the (wider) edge path beneath it, which already opens the same modal via `onEdgeClick`. Making the label itself clickable is additive (a bigger click target, consistent with the debug page) and doesn't remove the existing edge-path click handling — both remain valid ways to open the same modal.

*Alternative considered*: keep the label non-interactive and only take this change's layout/routing parts. Rejected per the user's explicit instruction to take rendering (including the edge label) from `/flows/debug`, and because a growing/clamping label with a tooltip is a strict usability improvement with no downside identified.

### Decision 4: Layout engine is a persisted Flow field, wired exactly like `layout_direction`
Backend: `Flow.layout_engine = models.CharField(choices=[("dagre", "Dagre"), ("elk", "ELK.js")], default="dagre")`, migration, and the mirrored `LayoutEngine = Literal["dagre", "elk"]` type on `FlowIn` (default `"dagre"`), `FlowPatch` (optional), `FlowOut` (required) in `schemas.py`, wired through `views.py` the same way `layout_direction` already is. Frontend: `FlowFormPage.tsx` holds `layoutEngine` state sourced from/saved to the Flow exactly like `layoutDirection`; `FlowCanvasSettings`'s gear popup gains a `SegmentedRadioGroup` (Dagre / ELK.js) beneath the existing autolayout `Switch`, mirroring `/flows/debug`'s `DebugSettingsPopup`.

*Rationale*: `autolayout_enabled`/`layout_direction` already establish this exact pattern (persisted Flow field, not a viewer preference) for a very similar kind of setting, so a third field follows the path of least surprise for anyone reading the model. A per-browser preference was considered and rejected in the exploration that produced this proposal, since it would mean two teammates viewing the same Flow could see different diagrams for a Flow-level fact.

### Decision 5: Drag-stop re-invokes the engine directly instead of diff-and-correct
While `autolayoutEnabled` is on, `handleNodeDragStop` calls the layout engine again and writes the fresh positions back directly (mirroring `/flows/debug`'s `applyLayout`), instead of the current mechanism (a passive effect recomputes positions on every `steps` change, diffs them against `steps`' stored values, and calls `onChange` only if something is stale, relying on the resulting re-render to converge). The passive effect keyed on `steps`/`autolayoutEnabled`/`layoutDirection`/`layoutEngine` still exists for non-drag `steps` changes (add/remove/edit a step) — this decision only changes the drag-stop path specifically.

*Rationale*: with no `edgeRouting`/`staleNodeIds` state left to reconcile, the diff-based mechanism's only remaining job was working around the fact that a drag is itself a `steps` change; calling the engine straight from the drag handler is simpler and matches the one other place (`/flows/debug`) this exact interaction was already built and verified.

*Observable behavior is unchanged*: the `flow-management` spec's "While autolayout is on, a drag has no lasting effect" scenario continues to hold — this is purely an internal mechanism change.

### Decision 6: `FlowGraph.tsx` gets the same rewrite, not a fork
The read-only canvas and PNG/SVG export already call `computeFlowAutolayout`/`buildFlowNodesAndEdges`/`mergeStepPositions` directly and render through `FLOW_EDGE_TYPES`/`FLOW_NODE_TYPES}` — the same shared modules the editor uses. This design changes those modules once; `FlowGraph.tsx`'s only required edit is threading the new `layoutEngine` prop through to `computeFlowAutolayout`, same as it already threads `layoutDirection`.

`inlineEdgeExportStyles` (PNG/SVG export) is audited and fixed in the same change: it currently targets `.react-flow__edge-textbg`/`.react-flow__edge-text`, which are xyflow's *built-in* smoothstep-label DOM classes — classes the custom `EdgeLabelRenderer`-based label (both today's and this design's) never emits. If export currently silently drops the label background/text inlining (because the querySelectorAll finds nothing), the fix targets the label `<div>`/`<Text>` this design's `FlowTransitionEdge` actually renders.

### Decision 7: Default engine is `dagre`
Every existing Flow gets `layout_engine = "dagre"` on migration. `/flows/debug` also defaults to `dagre`. No migration data backfill beyond the model default is needed since no Flow has ever had a `layout_engine` value before this change.

## Risks / Trade-offs

- **[Risk] Edges can once again visually cross or pass under an unrelated node** — the exact bug class `flow-elk-edge-routing` fixed. → **Mitigation**: none attempted by design; this is the accepted core trade of the rewrite (simplicity and a user-facing engine choice, over a guaranteed-no-crossing render). Verify against the same seeded stress-test Flows (`elk-layout-tests` System) to confirm crossings are rare in practice with either engine's default spacing, even though they're no longer structurally prevented.
- **[Risk] Two engines can produce visibly different diagrams for the same Flow**, which could surprise a team if one member's default differs from another's expectation. → **Mitigation**: the setting is persisted per-Flow (Decision 4), so it's a deliberate, shared, visible choice, not an accidental per-viewer divergence.
- **[Risk] Backend migration adds a required-on-read (`FlowOut`) field** — any external consumer of the Flow API deserializing strictly will need to handle the new field. → **Mitigation**: same low-risk shape as the pre-existing `layout_direction` field; default is backfilled by the migration, and this is an internal-catalog API, not a versioned public one.
- **[Risk] Deleting `flowLayout.test.ts`'s bendpoint/alignment test coverage removes regression protection for a shape of bug (obstacle crossing) that can now recur silently.** → **Mitigation**: replace those tests with coverage of the new engine dispatch (`dagre`/`elk` both produce positions for every step id) and the deleted-surface assertion that `buildFlowNodesAndEdges`'s output no longer carries a `routing` field, so a future change can't quietly reintroduce partial routing without a visible test change.

## Migration Plan

1. Backend: add the `layout_engine` model field + migration (additive, default-backfilled — no data loss, reversible by a follow-up migration if ever needed).
2. Backend: extend `FlowIn`/`FlowPatch`/`FlowOut` schemas and `views.py` wiring.
3. Frontend: rewrite `flowLayout.ts` (engines, deleted routing surface), `FlowEdges.tsx` (label + no-routing path), update both call sites (`FlowCanvasEditor.tsx`, `FlowGraph.tsx`) together in the same change so there is never a commit where the two canvases render a Flow differently.
4. Frontend: add the `layoutEngine` field to `FlowFormPage.tsx` state and the settings popup.
5. Archive `flow-elk-edge-routing` and `flow-manual-mode-routing-retention` alongside this change's own archival, so the canonical `flow-management` spec is updated exactly once to its final, correct state rather than through three sequential (and partially contradictory) syncs.

No rollback beyond standard revert is anticipated: the persisted `steps[].position` contract is untouched by this change (still the only thing ever written to the database besides the new `layout_engine` field), so reverting the frontend rewrite alone — keeping or dropping the backend field — leaves existing Flows fully readable either way.

## Open Questions

None outstanding — engine default (`dagre`), persistence model (per-Flow field), drag-stop mechanism (direct re-invoke), and node-visual scope (unchanged `FlowNodes.tsx`) were all settled during the exploration that produced this proposal.
