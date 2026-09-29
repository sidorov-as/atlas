## Context

`flow-canvas-redesign` (archived 2026-09-07) replaced the Flow editor's card list with `FlowCanvasEditor.tsx`, an editable `@xyflow/react` canvas with drag/connect/delete, an Auto Layout button, and a layout-direction gear popup (Decision 4/5). It left `FlowFormPage.tsx`'s two-panel structure untouched: a small "Steps (Visual/JSON)" panel on the left hosts either `FlowCanvasEditor` (editable) or the Monaco JSON editor, and a large "Preview" panel on the right always renders the separate, read-only `FlowGraph` component (`nodesDraggable={false}`) — the same component `FlowDetailPage.tsx` uses for its read-only view. So the edit page carries two independent diagram renders of the same steps, and the one an author actually interacts with (the editable canvas) is the small one.

`FlowGraph` stays in use on `FlowDetailPage.tsx` — this change only removes its use from `FlowFormPage.tsx`.

## Goals / Non-Goals

**Goals:**
- Make the canvas an author already interacts with also the primary, full-width view on the edit page.
- Keep JSON editing available, at parity with today (Monaco, schema validation, inline error), just relocated to an on-demand rail instead of a competing panel.
- Close the five rendering/interaction gaps found by inspection: missing arrowheads, cramped ELK spacing, no tooltip on truncated text, low-contrast kind label, no edge edit/delete.
- Make a layout-direction change visually immediate, consistent with the mental model "I changed a setting, the canvas reflects it now."

**Non-Goals:**
- No change to the persisted `steps` JSON grammar, `flowStepSchema.ts`, or backend validation (`apps/catalog/models/flow.py`) — this is presentation/interaction only.
- No change to `FlowDetailPage.tsx`'s read-only `FlowGraph` rendering beyond what it already inherits from shared code (`flowLayout.ts`, `FlowNodes.tsx`) — arrowheads/spacing/tooltip/icon fixes apply there too since they share the same layout/node code, but no detail-page-specific behavior changes.
- No "Query"/"Event" step kinds, no new node kinds, no entity-subtype icons requiring a catalog lookup per node — tracked separately.
- No persistence of the JSON-rail's open/closed state beyond what `isEditorOpen` already does (in-memory, per page load).

## Decisions

### 1. Canvas becomes the primary panel; JSON becomes a togglable rail

`FlowFormPage.tsx`'s layout inverts: the area currently labeled "Preview" (large, right-hand `FlowGraph`) is replaced by `FlowCanvasEditor`, full width. The area currently labeled "Steps (Visual/JSON)" is removed as a persistent panel; in its place, the existing `isEditorOpen` toggle (today: "Hide/Show editor", `LayoutSideContentRight`/`LayoutColumns` icons) opens a right-side rail containing only the Monaco JSON editor. The Visual/JSON `mode` toggle (`switchMode`) goes away — there is exactly one editable view (the canvas) and one optional inspection/bulk-edit view (JSON), not two mutually exclusive editors.

Consequences for existing wiring in `FlowFormPage.tsx`:
- `steps`/`stepsText` stay dual-tracked as today (canvas edits update `steps` → reserialize `stepsText`; JSON edits reparse into `parsedSteps` and, on a successful parse, sync back into `steps` so the canvas reflects JSON edits live) — this direction of sync already exists (`useEffect` on `parsedSteps` at `FlowFormPage.tsx:76-81`), it just no longer gates on `mode === 'json'`; the canvas is always "live," so JSON edits always flow into it, without discarding the canvas's own `position`/other-step data.
- `scrollToStep` (today: JSON mode scrolls Monaco, Visual mode opens the edit modal) simplifies to: if the JSON rail is open, scroll/select the step's JSON block; regardless, clicking a canvas node still opens its edit modal directly (that binding is already on `FlowCanvasEditor`'s `onNodeClick`, unaffected).
- `handleAddStep`'s JSON-mode branch (append + scroll) is preserved for when the rail is the surface the author is using to add a step by hand; the canvas's own "Add Step" button (opening `FlowStepModal`) stays the primary path.
- `FlowGraph`'s import is dropped from `FlowFormPage.tsx` only; the component itself is untouched (`FlowDetailPage.tsx` keeps using it).

**Alternative considered**: keep both panels but make the "Preview" panel draggable/interactive too (i.e., promote `FlowGraph` to editable instead of swapping in `FlowCanvasEditor`). Rejected — `FlowCanvasEditor` already has connect/delete/auto-layout/settings wired up against `flowSteps.ts`'s validation; duplicating that onto `FlowGraph` would just recreate the same component under a different name.

**Alternative considered**: keep the mode toggle, but let both Visual and JSON render simultaneously side-by-side always (no rail/collapse). Rejected — on the width most authors work at, two full diagram-scale panels plus the metadata form is what today's layout already tries and is exactly what reads as cramped; a collapsible rail preserves the option without permanently taxing width.

### 2. Layout-direction change triggers Auto Layout immediately

`FlowLayoutSettings`'s `onChange` (in `FlowCanvasEditor.tsx`) currently only calls `setPreferences({ ...preferences, layout })`. This change makes it also call the same `handleAutoLayout()` the magic-wand button calls, after updating the preference. This deliberately breaks `flow-canvas-redesign`'s Decision 5 guarantee ("a manually-dragged node is never silently moved back") for this one gesture only: changing the layout-direction setting is itself an explicit, user-initiated action, the same category `handleAutoLayout()` already treats as license to overwrite every step's `position` — it is not a passive recompute. The existing passive path (steps without a stored `position` get autolaid-out on render) is untouched.

**Alternative considered**: add a confirmation ("This will reposition all nodes — continue?") before applying. Rejected as unnecessary friction — Auto Layout already does this destructively today with one click and no confirmation; gating the settings change behind an extra step would make it *less* convenient than the button it's meant to shortcut.

### 3. Edge editing: a lightweight modal, not inline label editing

Clicking a transition edge (`onEdgeClick` on `FlowCanvasEditor`'s `<ReactFlow>`) opens a small `Dialog` (same family as `FlowStepModal.tsx`) with a single `label` text field and a "Delete transition" action, scoped to the one edge clicked. Saving updates the source step's `next_step.label` or the matching `next_steps[]` entry's `label`; deleting removes that transition the same way `removeStepIds` already cascades transition cleanup on node delete, just for one edge instead of every edge touching a removed node.

**Alternative considered**: inline-editable label directly on the edge (double-click the label text itself to edit in place). Rejected for v1 — `@xyflow/react`'s built-in edge label rendering (used today, per `flow-canvas-redesign` Decision 6) is a plain non-interactive `<div>`; making it independently editable in place would need a custom edge component, more work than a modal for a rarely-touched field, and inconsistent with how node fields are already edited (via `FlowStepModal`, not inline).

### 4. Node visuals: reuse existing icons, separate label styling by weight not just opacity

`PaletteNodeCard`'s kind label switches from `opacity: 0.75` on the same `colors.text` color to Gravity UI's `caption-2` + `color="secondary"` treatment (theme-aware secondary text color, distinct from the node's own fixed-palette text color) with the matching icon from `FlowStepModal.tsx`'s `KIND_TILES` (`Person`/`Cube`/`Database`/`PlugConnection`/`Layers`/`Persons`/`Compass`/`Flag`) rendered at a small size next to it. `StepNode`'s existing `Label theme={...}` badge is unaffected (it's already visually distinct by design).

Truncated `<Text ellipsis>` elements (title, subtitle, kind label) are wrapped in Gravity UI's `Tooltip` showing the untruncated value — applied unconditionally rather than only when actually truncated, since detecting truncation would need a ref + measurement and the tooltip is a no-op cost when the text already fits.

**Alternative considered**: derive the icon from the referenced entity's subtype (`componentTypeIcon`/`resourceTypeIcon`/`apiTypeIcon` from `lib/icons.ts`), matching list-page rows exactly. Rejected for this change — the canvas has no per-node entity-subtype data available today (only the `kind:name` ref string); fetching it would mean an extra catalog lookup per node. The kind-level icon (already drawn for the type picker) is a same-day improvement; subtype icons are a plausible independent follow-up if wanted later.

### 5. Arrowheads and spacing: additive layout-code changes

`buildFlowNodesAndEdges` (`flowLayout.ts`) adds `markerEnd: { type: MarkerType.ArrowClosed }` to every edge. `buildElkGraph` adds `'elk.spacing.nodeNode'` to `layoutOptions`, sized relative to `FLOW_NODE_HEIGHT`/`FLOW_NODE_WIDTH` (e.g. `'40'`, matching the existing between-layers spacing's order of magnitude) so siblings in the same column get breathing room without materially changing the overall diagram footprint ELK already produces.

## Risks / Trade-offs

- **Removing the Visual/JSON mode toggle changes a documented `visual-flow-editor` behavior** ("Synchronized Visual and JSON modes" — today's spec describes switching between two modes) → Mitigation: functionally, both directions of sync are kept; only the framing changes (one always-visible canvas + an optional JSON rail, instead of two mutually exclusive panels). The delta spec updates the requirement text and scenarios to match, rather than silently diverging from it.
- **Auto-applying layout on a settings change discards any manual dragging done since the last Auto Layout** → Mitigation: this is the same destructive behavior the existing Auto Layout button already has; changing the direction setting is a deliberate enough action (a `Popup` with a radio group, not a stray click) that treating it the same way is consistent, not surprising.
- **Dropping `FlowGraph` from the edit page removes its `onBlockClick`-driven JSON-scroll wiring** → Mitigation: the same click-to-scroll behavior is re-implemented against `FlowCanvasEditor`'s own node click (already present for opening the edit modal); when the JSON rail is open, the same click additionally scrolls Monaco to that step's block.
- **Reviewers may expect this change to also add Query/Event step kinds**, since that was raised in the same discussion → Mitigation: explicitly called out as out of scope in the proposal and here; it depends on an unresolved core/plugin extension-point question that deserves its own change.

## Migration Plan

1. `flowLayout.ts`: add `markerEnd` to edges, add `elk.spacing.nodeNode` to ELK layout options. No data shape change.
2. `FlowNodes.tsx`: kind-label styling + icon, `Tooltip` wrapping on truncated text.
3. `FlowCanvasEditor.tsx`: `onEdgeClick` + new edge modal (label edit / delete transition); `FlowLayoutSettings.onChange` also invokes `handleAutoLayout()`.
4. `FlowFormPage.tsx`: swap the "Preview" panel's `FlowGraph` for `FlowCanvasEditor`; convert the "Steps" panel into a JSON-only rail behind the existing `isEditorOpen` toggle; remove the Visual/JSON `mode` state and `switchMode`; adjust `scrollToStep`/`handleAddStep` per Decision 1.
5. Update `flow-management` and `visual-flow-editor` delta specs (this change) to match the new panel structure, the immediate-apply layout-setting behavior, and the edge edit/delete interaction.
6. Rollback: every change here is presentation-only against the same `steps` data shape — reverting the frontend commit(s) is sufficient; no data migration is involved either direction.

## Open Questions

- None blocking — the one open architectural question raised alongside this feedback (Query/Event step kinds referencing Endpoints/Operations) is deliberately out of scope for this change.
