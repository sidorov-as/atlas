## Why

Every Flow step renders as an identical light-blue block today (`FlowGraph.tsx` via `@gravity-ui/graph`), so a diagram gives no visual signal about what kind of thing each step is — an actor, a service, a data store, an outcome. The step-authoring UI (`FlowStepEditor.tsx`) is a linear list of cards with up/down/remove buttons, not a graph-editing surface, which makes building or restructuring a Flow slow and indirect compared to clicking, dragging, and connecting nodes directly. EventCatalog's Flow visualiser and Flow Editor demonstrate the alternative: color- and icon-coded node types plus a canvas where adding, retyping, connecting, and repositioning steps all happen in place.

## What Changes

- Flow steps render as typed, colored nodes: type is derived from the step's existing `entity_ref` kind (`user`→Actor, `group`→Team, `component`→Service, `resource`→Data, `api`→API, `system`→System), plus two new non-entity node kinds — a manually-colored plain **Step** and an out-of-catalog **External** reference.
- Entity-backed node colors reuse the existing C4 diagram palette (`plugins/c4/backend/atlas_plugin_c4/c4.py`'s `_ATLAS_PLANTUML_TAGS`) verbatim, as a fixed, non-theme-aware palette, so Flow diagrams read consistently with Atlas's own C4 diagrams. Plain Step nodes use Gravity UI's theme-aware `Label` color vocabulary (`success | danger | warning | info | utility | normal`) instead.
- **BREAKING**: The Visual editor (`FlowStepEditor.tsx`'s card list) is replaced with an interactive `@xyflow/react` canvas: an "Add step" control opens a node-type picker (Actor/Service/Data/API/System/Team/External/Step); entity-backed types open a searchable catalog lookup (reusing `RefSelect`/`TargetRefSelect`), non-entity types prompt for title/summary/color; clicking an existing node reopens the same modal with a "Change type" action; dragging from a node's handle to another node creates a transition, enforcing the existing strict-tree rule (no reconvergence, no cycles, target must exist) live during the drag; nodes are freely draggable to reposition.
- **BREAKING**: `FlowGraph.tsx`/`flowLayout.ts` migrate off `@gravity-ui/graph` onto `@xyflow/react`, calling `elkjs` directly (following the pattern already proven in `erDiagramLayout.ts`). The same typed node components render on both the editable canvas and the read-only Flow detail page (`nodesConnectable={false}` there, matching `ErDiagramView`'s read/write split).
- Node positions become persisted, optional data (`FlowStep.position?: {x, y}`) rather than always recomputed: dragging a node sticks; an explicit "Auto layout" action re-runs ELK; a settings control (gear + `SegmentedRadioGroup`, matching `DiagramTab.tsx`'s `DiagramSettings`) picks layout direction (`LAYOUT_TOP_DOWN` / `LAYOUT_LEFT_RIGHT`, reusing the naming from `diagramPreferences.ts`). Steps without a stored position fall back to autolayout, so existing Flows keep working unchanged.

## Capabilities

### New Capabilities

_None — this reshapes how two existing capabilities render and are authored; it does not introduce a new domain capability._

### Modified Capabilities

- `flow-management`: the step data shape gains optional `position` (and the data needed to describe an External node), and the "Client-side Flow diagram" requirement is rewritten around typed/colored nodes rendered via React Flow instead of a single fixed block style via `@gravity-ui/graph`.
- `visual-flow-editor`: the entire authoring model changes from list-based (add/edit/remove/reorder rows) to canvas-based (add via node-type picker, edit/retype via modal, connect via drag, position via drag), while preserving the same underlying `steps` JSON grammar and the same structural validation guarantees (no reconvergence, no cycles, no dangling transitions).

## Impact

- **Frontend**: `core/frontend/src/components/FlowGraph.tsx`, `FlowStepEditor.tsx`, `lib/flowLayout.ts`, `lib/flowStepSchema.ts`, `components/flowSteps.ts`, `pages/FlowDetailPage.tsx`, `pages/FlowFormPage.tsx`, `index.css` (`.flow-graph__*` rules). New node components (Actor/Service/Data/API/System/Team/External/Step) and a node-type-picker modal.
- **Dependencies**: drops `@gravity-ui/graph` from the Flow feature in favor of `@xyflow/react` (already a dependency via `plugins/database-schema`); no new package additions expected.
- **Backend**: the Flow model/schema gains an optional `position` field per step (and a way to represent an External node) — a additive, backward-compatible change to the `steps` JSON shape validated in `apps/catalog/models/flow.py`.
- **Existing Flows**: unaffected functionally — steps without a stored `position` continue to autolayout exactly as today.
