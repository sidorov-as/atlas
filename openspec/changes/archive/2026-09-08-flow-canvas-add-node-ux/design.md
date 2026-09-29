## Context

`flow-canvas-redesign` (archived 2026-09-07) introduced `FlowCanvasEditor.tsx`, and `polish-flow-canvas-editor` (archived 2026-09-07) closed several of its rendering/interaction gaps (arrowheads, spacing, edge-click modal, layout-direction immediacy). This change closes three more, found by using the canvas and comparing it against EventCatalog's flow editor (a similar tool, inspected live at a local reference instance) as a point of reference for an established pattern:

1. **New-node placement/overlap.** `FlowFormPage.handleStepModalSave` (the toolbar "Add Step" path) appends a step with no `position` and no transitions. `flowLayout.ts`'s `buildForest()` treats it as a second, disconnected root; ELK lays out disconnected components independently and both roots frequently land at the same computed coordinate as the flow's actual first step. `mergeStepPositions()` (`flowLayout.ts:244-250`) then has nothing but that coincidental autolayout value to fall back to. `FlowCanvasEditor.tsx`'s `focusStepId` effect (lines 119-129) correctly pans the camera to the new node once it appears in `nodes` — but it's panning to the overlapping pile-up, not fixing it. This also means the canvas currently violates `visual-flow-editor`'s existing requirement that a positionless step should autolayout "instead of stacking at a default coordinate" — the disconnected-root case is exactly that stacking.
2. **No connected-add.** The only way today to get a *new, already-connected* step is: add an unconnected step via the toolbar, then separately drag a connection from an existing node to it (`onConnect`/`canUseTransition` in `FlowCanvasEditor.tsx`/`flowSteps.ts`). EventCatalog instead lets an author add a step directly from an existing node — either via a persistent per-node "+" or a placeholder card shown in the exact slot a next step would occupy — which both creates and wires the step in one action.
3. **Non-wrapping transition labels.** `buildFlowNodesAndEdges` (`flowLayout.ts:253-289`) uses `@xyflow/react`'s default `smoothstep` edge type with a plain `label` string. Reading the installed package (`@xyflow/react/dist/esm/index.mjs`, `EdgeTextComponent`) confirms this renders through the library's built-in `EdgeText`, which emits exactly one SVG `<text>{label}</text>` node — SVG text does not wrap. A long label today just overflows past the edge. EventCatalog's equivalent label visibly wraps onto multiple lines; inspecting its raw stored YAML for a wrapped label confirmed the underlying value is a single-line string — the wrap is pure rendering, not a data concern.

## Goals / Non-Goals

**Goals:**
- Guarantee a newly added step — whether unconnected (toolbar) or connected (node-header / placeholder) — never visually overlaps an existing node, without needing the user to manually reposition it afterward.
- Add one-click "create and connect the next step" from any node, matching EventCatalog's node-header "+" and terminal-step placeholder pattern, without removing drag-to-connect.
- Make transition labels legible regardless of length, on both the editable canvas and the read-only detail-page diagram, since they share `flowLayout.ts`/`FLOW_NODE_TYPES`.

**Non-Goals:**
- No change to the persisted `steps` JSON grammar, `flowStepSchema.ts`, or backend validation (`apps/catalog/models/flow.py`) — labels, positions, and transitions keep their existing shapes.
- No multi-line/manual-line-break label input — confirmed against the reference implementation that wrapping is a render-time concern over a single-line string; `FlowTransitionModal.tsx`'s `TextInput` is unchanged.
- No change to drag-to-connect's own validation (`canUseTransition`) — the new add-affordances reuse it implicitly by producing the same `addTransition()` result a manual drag would.
- No entity-subtype icons or new node kinds — out of scope, as in the prior polish change.

## Decisions

### 1. Deterministic placement for an unconnected new step (toolbar "Add Step")

`handleAddStep`/`handleStepModalSave` in `FlowFormPage.tsx` currently only sets `canvasFocusStepId`, relying on `FlowCanvasEditor`'s autolayout + `focusStepId` pan. Instead, at the moment the new step is appended (still in `FlowFormPage.tsx`, before it reaches the canvas), compute the bounding box of every existing step's resolved position (stored `position`, falling back to the canvas's last-known autolayout position for positionless steps) and set the new step's `position` to `{x: minX, y: maxY + gap}` — a new row below the whole flow, left-aligned to its leftmost node. `gap` matches the vertical spacing `computeFlowAutolayout` already uses between layers. This makes the new step's position explicit and stored from the start, so `mergeStepPositions` never falls through to an ELK-computed value shared with another disconnected root.

`FlowCanvasEditor` then calls its existing `fitView({ duration: 200 })` (already used by `handleAutoLayout`) instead of `setCenter`-based `focusStepId` panning for this path, so the whole diagram — including the new row — stays in frame, matching the reference's own "add step, then fit view" behavior. `focusStepId`/`setCenter` stays as-is for cases where a specific existing node should be centered (none remain after this change removes the toolbar path's use of it, but the mechanism isn't deleted — it's still the simplest way to focus a single node if a future entry point needs it).

**Alternative considered**: keep `focusStepId`'s pan-to-node behavior and only change *where* the node lands (e.g. still let ELK/autolayout place it, just seed it far enough from existing bounds that overlap is impossible). Rejected — autolayout's placement for a disconnected root isn't a stable, predictable quantity to reason about (it depends on ELK's internal handling of disconnected components, which is what caused the bug); computing the position ourselves from the bounding box we already have in `steps` is simpler and deterministic.

### 2. Connected-add: one shared code path, two entry points

Both the node-header "+" and the terminal-step placeholder perform the identical operation: open `FlowStepModal`'s node-type picker, and on save, call `addTransition(steps, sourceId, newStep.id)` (already exists, `flowSteps.ts:55-68`, and already handles "append as a branch if the source already has one") plus set the new step's `position` to one layout-step past the source — `{x: source.x + FLOW_NODE_WIDTH + gap, y: source.y}` for `LAYOUT_LEFT_RIGHT`, or the transposed form for `LAYOUT_TOP_DOWN` — using the same `FLOW_NODE_WIDTH`/spacing constants ELK's own layout options already use, so a manually-added step lands in the same slot autolayout would have put it in.

This is implemented as one function (e.g. `addConnectedStep(sourceId)` in `FlowCanvasEditor.tsx`) that both entry points call — the placeholder card is not a different feature, it's a shortcut UI for the single most common invocation of the node-header "+" (a step with no children yet). Concretely:
- **Node-header "+"**: a new always-visible `Button` in `PaletteNodeCard`/`StepNode` (`FlowNodes.tsx`), next to the now-also-persistent remove button, calling `data.onAddNext` (a new `FlowNodeData` field, parallel to the existing `onDelete`).
- **Placeholder card**: a new synthetic React Flow node type (e.g. `'add-placeholder'`) added to `FLOW_NODE_TYPES`, rendered as a dashed, semi-transparent card with a centered "+" — visually inert (no title/kind/tooltip), `nodesDraggable={false}` for this type specifically. `FlowCanvasEditor`'s layout effect emits one of these, positioned exactly like a connected-add's target position above, for every step where `transitionTargets(step).length === 0` (mirrors the reference's exact scope: a step that already has an outgoing transition gets no placeholder, only the header "+"). Clicking it calls the same `addConnectedStep(sourceId)`.

Since the placeholder is synthetic (computed in `buildFlowNodesAndEdges` or alongside it, never written into `steps[]`), it needs no cleanup on the target side when removed — it simply stops being emitted once its step gains a transition.

**Alternative considered**: give the placeholder its own independent "add and connect" logic, separate from the header "+". Rejected — they must always agree on target position and transition semantics (branch vs single `next_step`); one shared function is the only way to guarantee that without duplicated logic drifting apart over time.

**Alternative considered**: show a placeholder for a step that already has children too, as an additional way to add another branch (an option considered and explicitly rejected in favor of matching the reference: placeholders are terminal-only, branching beyond the first child is header-"+"-only).

### 3. Wrapping transition labels via a custom edge label renderer

`buildFlowNodesAndEdges` stops relying on `smoothstep`'s built-in SVG label. A small custom edge component is registered (e.g. `FlowTransitionEdge`, alongside `FLOW_NODE_TYPES` as a new `FLOW_EDGE_TYPES` map passed to `<ReactFlow edgeTypes={...}>`) that:
- Renders the connector path with `getSmoothStepPath()` (same path shape as today) via `<BaseEdge>`.
- Renders the label via `<EdgeLabelRenderer>`, xyflow's HTML-overlay escape hatch, as a fixed-max-width `<div>` (Gravity `Text`, `variant="caption-2"`) with normal CSS wrapping (`white-space: normal`, `wordBreak: 'break-word'`) instead of SVG `<text>`, matching how the reference wraps ("Step 1 — reserve inventory" onto two lines within a fixed-width box).

`estimateLabelSize()` (`flowLayout.ts:125-127`), which tells ELK how much space to reserve between layers for a label, changes from a single-line character-count estimate to: given the same fixed max-width the renderer uses, estimate wrapped line count as `Math.ceil(label.length / charsPerLine)` (charsPerLine derived from the max-width the same way the existing estimate derives width from length) and reserve `height = lines * lineHeight`. This stays a heuristic — no real DOM/canvas text measurement — consistent with the existing comment in `flowLayout.ts` that ELK only needs a rough reservation, not a pixel-exact one.

Because `FLOW_EDGE_TYPES` is consumed by both `FlowCanvasEditor` and the read-only `FlowGraph`/`FlowDetailPage` canvas (shared `flowLayout.ts`/node-types-adjacent registration), the wrapping applies to both for free, matching how the prior polish change's arrowhead/spacing fixes did.

**Alternative considered**: keep the default SVG label but truncate long labels with an ellipsis + tooltip, matching how node titles/subtitles already handle overflow (`FlowNodes.tsx`'s `Tooltip`-wrapped `<Text ellipsis>`). Rejected — a transition label is short-lived UI real estate an author is actively naming a business step with (per the checkout-saga reference: "Step 1 — reserve inventory"); truncating it defeats the purpose more than a two-line wrap does, and the reference's own choice to wrap rather than truncate is a reasonable one to match.

## Risks / Trade-offs

- **Bounding-box placement for the toolbar "Add Step" path assumes every existing step has a resolvable position** (stored or the canvas's last computed autolayout value) → Mitigation: `FlowCanvasEditor` already computes and holds autolayout positions for every step every render (`mergeStepPositions`); the bounding-box calculation reads from that same source, not from `steps[].position` alone, so a step that has never been manually dragged still contributes a real coordinate.
- **A custom edge component takes over rendering from `@xyflow/react`'s default `smoothstep` type** → Mitigation: the path geometry (`getSmoothStepPath`) and marker (`markerEnd`) stay identical to today; only the label's DOM (SVG text → HTML div) changes, so the diagram's overall shape is visually unchanged apart from the wrap itself.
- **The placeholder card is a node the user can click but that doesn't exist in `steps[]`** — any code that iterates `nodes` expecting every entry to correspond to a step (e.g. `onNodesDelete`, selection logic) must explicitly skip nodes of type `'add-placeholder'` → Mitigation: give it `deletable: false` and `selectable: false` at creation, and have `handleNodesDelete`/`removeStepIds` filter by `FLOW_NODE_TYPES` membership rather than assume all `nodes` are steps.
- **Two new entry points (header "+", placeholder) both mutate `steps` through `addConnectedStep`, alongside the pre-existing drag-to-connect path through `addTransition` directly** → Mitigation: `addConnectedStep` calls `addTransition` internally rather than reimplementing its branch-append logic, so all three paths (drag, header "+", placeholder) stay behaviorally identical for the transition itself; they only differ in whether they also set a `position`.

## Migration Plan

1. `flowLayout.ts`: bounding-box helper for the toolbar-add placement; `FlowTransitionEdge` custom edge component + `FLOW_EDGE_TYPES`; updated `estimateLabelSize()` for wrapped-label ELK spacing.
2. `FlowNodes.tsx`: persistent (non-hover) header add/remove controls on `PaletteNodeCard`/`StepNode`; new `'add-placeholder'` node component added to `FLOW_NODE_TYPES`.
3. `FlowCanvasEditor.tsx`: `addConnectedStep(sourceId)` shared by the header "+" and placeholder click handlers; placeholder-node emission alongside real nodes for every childless step; `<ReactFlow edgeTypes={FLOW_EDGE_TYPES}>`; `handleNodesDelete`/selection logic updated to ignore placeholder nodes.
4. `FlowFormPage.tsx`: toolbar `handleAddStep`/`handleStepModalSave` computes and sets the new step's bounding-box `position` instead of relying solely on `canvasFocusStepId`; canvas switches to `fitView` for this path.
5. Update `flow-management` and `visual-flow-editor` delta specs (this change) for the new placement guarantee, the two additional add-entry-points, always-visible node controls, and label wrapping.
6. Rollback: every change here is presentation/interaction-only against the same `steps` data shape — reverting the frontend commit(s) is sufficient; no data migration either direction.

## Open Questions

- None blocking. One deliberately deferred question: whether the placeholder card should also appear on an empty canvas (zero steps) as the very first add-affordance, replacing the toolbar button entirely for that case. Left as toolbar-only for now, matching today's behavior for an empty Flow; worth revisiting only if the toolbar button and placeholder-card patterns turn out to feel redundant in practice.
