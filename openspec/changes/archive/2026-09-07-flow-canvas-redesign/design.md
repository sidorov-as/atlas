## Context

Flow diagrams are rendered by `core/frontend/src/components/FlowGraph.tsx`, laid out by `core/frontend/src/lib/flowLayout.ts` via `@gravity-ui/graph`'s `useElk`/`<GraphBlock>`, and authored via `core/frontend/src/components/FlowStepEditor.tsx`, a linear card list (see `flow-management` and `visual-flow-editor` specs). Every step renders as one fixed-style block regardless of what it represents.

Two sibling features in this codebase already solve the pieces this change needs:

- `plugins/database-schema/frontend/src/components/ErDiagramView.tsx` + `erDiagramLayout.ts`: an editable `@xyflow/react` canvas with free dragging, a magic-wand "Auto layout" button that calls `elkjs` directly (`elk.layout(graph)`, no `@gravity-ui/graph` involved), `useReactFlow()`-driven zoom/fit, and a `ResizeObserver` re-fit fix for tab-hidden mounts.
- `plugins/c4/frontend/src/components/DiagramTab.tsx`'s `DiagramSettings` + `plugins/c4/frontend/src/lib/diagramPreferences.ts`: a gear-icon `Popup` with a `SegmentedRadioGroup` for layout direction (`LAYOUT_TOP_DOWN` / `LAYOUT_LEFT_RIGHT` / `LAYOUT_LANDSCAPE`).
- `plugins/c4/backend/atlas_plugin_c4/c4.py`'s `_ATLAS_PLANTUML_TAGS`: the fill/text/border hex triples Atlas's C4 diagrams already use per element kind (Person, Component, Database, Queue, Endpoint, External Endpoint).

This design wires those three together for Flow, rather than inventing new patterns.

## Goals / Non-Goals

**Goals:**
- Render each Flow step as a typed, colored node — type derived from `entity_ref`'s kind, or from a new non-entity node kind (Step, External).
- Replace the card-list Visual editor with an EventCatalog-style canvas: add via a node-type picker, edit/retype via a modal, connect via drag, position via drag.
- Migrate Flow rendering off `@gravity-ui/graph` onto `@xyflow/react`, matching the ER Diagram's already-proven approach.
- Persist manual node positions; keep autolayout (ELK) available on demand, with a direction setting.
- Keep the persisted `steps` JSON grammar's structural guarantees unchanged: single home per node id (no reconvergence), no cycles, no dangling transitions.

**Non-Goals:**
- No EventCatalog-style guided "walkthrough" (Start/Next/Previous step-through) — not requested.
- No resource-subtype color splitting (database vs. queue vs. cache) — all `resource:*` steps use one color (Database amber) in this pass; subtype splitting is a plausible independent follow-up, not part of this change.
- No change to the JSON editor mode or its Monaco/schema-validation behavior (`monacoFlowTheme.ts`, `flowStepSchema.ts`'s shape validation) beyond adding the new optional fields — it remains a supported, synchronized mode alongside the canvas.
- No backend change to `entity_ref` resolution or the strict-tree validator's algorithm (`apps/catalog/models/flow.py`'s `validate_steps`) — only the schema it validates against grows two new optional fields.

## Decisions

### 1. Node type is derived, never stored, for entity-backed steps
A step's visual type comes from parsing its existing `entity_ref` (`"component:checkout-api"` → Service). No new `type` enum field is added for these steps — `entity_ref`'s kind prefix (`user | group | component | resource | api | system`, the same six kinds `RefSelect.tsx`'s `TARGET_REF_KINDS` already supports) is the single source of truth. This avoids a second field that could drift from the actual referenced entity's kind (e.g. a step claiming `type: 'service'` while `entity_ref` points at a `resource`).

Mapping: `user`→Actor, `group`→Team, `component`→Service, `resource`→Data, `api`→API, `system`→System.

**Alternative considered**: an explicit `type` field independent of `entity_ref`, matching EventCatalog's richer taxonomy (Event, Command, Query, Decision as distinct types even when backed by a catalog entity). Rejected for v1 — Atlas's catalog doesn't model messages/events as entities the way EventCatalog's does, so there's no natural entity kind to hang those types on, and introducing an unenforced, entity-independent `type` string reopens the drift problem above.

### 2. Two new non-entity node kinds: Step and External
Steps without an `entity_ref` split into:
- **Step**: a plain step with a manually chosen semantic color, stored as a new optional `label_theme: 'success' | 'danger' | 'warning' | 'info' | 'utility' | 'normal'` field (Gravity UI's own `Label` theme vocabulary — same tokens used elsewhere in the app, e.g. `Label theme="danger"`). Absent `label_theme` renders as the current neutral style.
- **External**: an out-of-catalog reference (e.g. a third-party payment gateway), stored as a new optional `external_label: string` field. When present (and `entity_ref` absent), the step renders with the External node component, using the C4 "External Endpoint" gray.

A step has at most one of `entity_ref`, `external_label`, or neither (implying plain Step, optionally with `label_theme`). `flowStepSchema.ts` and the backend `steps` shape validator both grow these two optional fields; a step carrying both `entity_ref` and `external_label` is rejected as invalid, same enforcement layer as today's entity-ref-resolution check.

### 3. Fixed C4 palette for entity-backed and External nodes; theme-aware Label palette for Step nodes
Entity-backed node colors are copied verbatim from `_ATLAS_PLANTUML_TAGS` (fill/text/border hex):

| Node type | Fill | Text | Border |
|---|---|---|---|
| Actor / Team (`user`, `group`) | `#fff3e0` | `#e65100` | `#fb8c00` |
| Service (`component`) | `#e8f5e9` | `#1b5e20` | `#66bb6a` |
| Data (`resource`) | `#fff8e1` | `#5d4037` | `#ffb300` |
| API (`api`) | `#e3f2fd` | `#0d47a1` | `#42a5f5` |
| System (`system`) | `#e3f2fd` | `#0d47a1` | `#42a5f5` (bold, 2px) |
| External | `#f5f5f5` | `#424242` | `#9e9e9e` |

These are defined once as shared constants (e.g. `core/frontend/src/lib/flowNodePalette.ts`) consumed by the new node components — not re-derived from the C4 plugin's Python module, since that's a separate backend package; the frontend copy is a deliberate, documented duplication of a fixed design constant, not a runtime dependency on the `c4` plugin.

Step nodes instead use `var(--g-color-*)` tokens via Gravity UI's `Label` component/theme, so they remain theme-aware (dark/light) — the one node family without a fixed catalog identity to anchor a fixed color to.

This keeps the current `.flow-graph` CSS's existing "fixed light palette, not theme-aware" decision intact for six of eight node types, while giving Step nodes the same theme-aware semantics as every other status badge in Atlas.

### 4. Canvas editor: node-type picker, edit-in-place modal, drag-to-connect
`FlowStepEditor.tsx` (card list) is replaced by a new canvas editor built on `@xyflow/react`, structurally mirroring `ErDiagramView.tsx`:
- `nodesDraggable`, `nodesConnectable={true}` (unlike ErDiagram's read-only `false}` — Flow's canvas is the primary authoring surface).
- **Add step**: opens a node-type picker modal (Actor/Service/Data/API/System/Team/External/Step tiles with icon + description, matching the visual weight of EventCatalog's picker but scoped to Atlas's 8 types instead of ~17). Selecting an entity-backed type shows the matching `TargetRefSelect`/`RefSelect` lookup (already grouped/labeled by kind); selecting Step shows title/summary/`label_theme` inputs; selecting External shows title/summary/`external_label`.
- **Edit existing node**: clicking a node reopens the same modal pre-filled, with a "Change type" action that resets the type-specific fields.
- **Connect**: dragging from a node's source handle to another node's target handle calls the existing `canUseTransition` check (`flowSteps.ts`) before committing — a connection to an already-targeted node, a nonexistent step, or one that would create a cycle is rejected inline (visually: the drag snaps back, with the existing validation message shown), preserving the `visual-flow-editor` spec's structural-feedback requirements without new validation logic.
- **Delete**: a node's hover affordance (or selection + Delete key) removes it and any transitions targeting it, matching `FlowStepEditor.remove()`'s existing cascade behavior.
- **Reorder**: no longer a first-class action (canvas position replaces list order) — `steps[]` array order becomes insignificant for rendering/authoring purposes (it was never semantically ordered beyond the tree structure).

The JSON editor mode and its live-sync behavior are unchanged; both editor modes keep producing/consuming the same `steps` JSON shape.

### 5. Layout: persisted `position`, on-demand autolayout, direction setting
`FlowStep` gains an optional `position?: { x: number, y: number }`. Rendering logic:
- A step with a stored `position` renders there.
- A step without one is placed by ELK autolayout (same forest-building logic in `flowLayout.ts`, now emitting `@xyflow/react` `Node[]`/`Edge[]` instead of `TBlock[]`/`TConnection[]`, and calling `elkjs` directly rather than through `@gravity-ui/graph`'s `useElk`).
- Dragging a node writes its new `position` into that step's data immediately (mirrors `ErDiagramView`'s `onNodesChange`/`useNodesState`, except Flow persists positions rather than treating them as session-only).
- An "Auto layout" toolbar button (magic-wand icon, matching `ErDiagramView`) re-runs ELK and overwrites every step's `position` with the computed layout — the explicit, user-initiated escape hatch from a manually-dragged-into-a-mess canvas.
- A gear-icon settings `Popup` with a `SegmentedRadioGroup` (`LAYOUT_TOP_DOWN` / `LAYOUT_LEFT_RIGHT`, reusing `diagramPreferences.ts`'s naming) chooses the direction Auto Layout lays out in, stored as a lightweight view preference (not persisted per-Flow — a session/local default, same scope as the C4 plugin's `DiagramRenderingPreferences`, unless product feedback later asks for per-Flow persistence).

The Flow detail page (read-only) renders the same nodes/positions with `nodesConnectable={false}`, `nodesDraggable={false}` — a pure viewer, matching `ErDiagramView`'s split between its editable canvas and read consumers elsewhere.

### 6. Drop `@gravity-ui/graph` from the Flow feature
`FlowGraph.tsx` and `flowLayout.ts` are rewritten against `@xyflow/react` (`ReactFlow`, `ReactFlowProvider`, `useNodesState`, `useReactFlow`) and raw `elkjs`, following `erDiagramLayout.ts`/`ErDiagramView.tsx` line for line where applicable. `@gravity-ui/graph` remains a dependency only for the database-schema plugin's own (already-migrated) ER diagram code path — actually it is fully unused after this change, since ER Diagram itself only used `elkjs` directly; a follow-up housekeeping task checks whether `@gravity-ui/graph` can be removed from `package.json` entirely once no importer remains.

## Risks / Trade-offs

- **Backend schema growth** (`position`, `label_theme`, `external_label` on each step) → Mitigation: all three are optional/additive; existing Flows and existing JSON payloads remain valid without modification, and the strict-tree validator's algorithm is untouched.
- **Frontend duplication of the C4 hex palette** (copied into TypeScript rather than served from the backend) → Mitigation: documented as a deliberate fixed design constant in code comments, same posture the current `.flow-graph__block` CSS already takes toward its C4-inspired palette; a future shared-constants extraction is possible but not required now.
- **Losing `@gravity-ui/graph`'s built-in connection routing/label placement** → Mitigation: `@xyflow/react` ships its own edge label rendering and smoothstep/bezier routing (already exercised by `ErDiagramView`'s edges), so no custom routing code is needed.
- **Drag-to-connect enforcing tree constraints interactively is a new interaction pattern** (today's Visual editor only validates on selection change in a dropdown, not mid-drag) → Mitigation: reuse the exact `canUseTransition`/`validateFlowSteps` functions from `flowSteps.ts` unchanged, just called from `onConnect` instead of a `Select`'s `onUpdate`.
- **Removing list-based reordering** removes the only way today's editor expresses tree structure without a diagram → Mitigation: the canvas itself is the structural view now; this is the intended trade (EventCatalog-style authoring), not an oversight.

## Migration Plan

1. Backend: add `position`, `label_theme`, `external_label` as optional fields to the Flow step shape validated in `apps/catalog/models/flow.py`; no data migration needed (additive optional fields).
2. Frontend data layer: extend `FlowStep` (`flowLayout.ts`) and `flowStepSchema.ts` with the three new optional fields; add the shared C4-derived palette constants module.
3. Rendering: rewrite `flowLayout.ts`'s layout output to `@xyflow/react` shapes calling `elkjs` directly; build the eight typed node components; rewrite `FlowGraph.tsx` as a thin read-only `ReactFlow` wrapper (detail page) plus a new editable canvas component (edit page), following `ErDiagramView.tsx`.
4. Editor: build the node-type picker modal and edit/retype modal; wire `onConnect`/`onNodesChange`/deletion through the existing `flowSteps.ts` validation; retire `FlowStepEditor.tsx`.
5. Settings: add the gear/`Popup`/`SegmentedRadioGroup` layout-direction control and the Auto Layout action.
6. Update `flow-management` and `visual-flow-editor` specs (delta specs in this change) to match; update `.flow-graph__*` CSS in `index.css` for the new node components (or remove it if fully superseded by inline/component-scoped styles).
7. Rollback: since every schema addition is optional and additive, reverting the frontend to the previous commit is sufficient to roll back — no backward-incompatible data would have been written.
