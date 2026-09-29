## 1. Backend schema

- [x] 1.1 Add optional `position` (`{x: number, y: number}`), `label_theme` (`'success'|'danger'|'warning'|'info'|'utility'|'normal'`), and `external_label` (string) fields to the Flow step shape validated in `apps/catalog/models/flow.py`
- [x] 1.2 Add a validation rule rejecting a step that carries both a non-empty `entity_ref` and a non-empty `external_label`
- [x] 1.3 Confirm the existing strict-tree validator (`validate_steps`) is unaffected by the new optional fields; add/update backend tests covering the new fields and the mutual-exclusivity rejection

## 2. Frontend data model

- [x] 2.1 Extend `FlowStep`/`FlowStepTransition` types in `core/frontend/src/lib/flowLayout.ts` with `position?`, `label_theme?`, `external_label?`
- [x] 2.2 Extend `flowStepSchema.ts`'s JSON Schema with the three new optional fields and the entity_ref/external_label mutual-exclusivity constraint
- [x] 2.3 Add a shared node-kind derivation helper (e.g. `flowNodeKind.ts`): given a `FlowStep`, return one of `actor | team | service | data | api | system | external | step`, parsing `entity_ref`'s kind prefix or falling back to `external`/`step`
- [x] 2.4 Add `core/frontend/src/lib/flowNodePalette.ts` with the fixed fill/text/border hex triples copied from `plugins/c4/backend/atlas_plugin_c4/c4.py`'s `_ATLAS_PLANTUML_TAGS`, keyed by the node-kind values from 2.3 (Actor/Team, Service, Data, API, System, External)

## 3. Layout engine migration

- [x] 3.1 Rewrite `flowLayout.ts`'s ELK integration to call `elkjs` directly (drop `@gravity-ui/graph`'s `useElk`), following `plugins/database-schema/frontend/src/lib/erDiagramLayout.ts`'s pattern
- [x] 3.2 Change `buildElkGraph`/layout output to produce `@xyflow/react` `Node[]`/`Edge[]` instead of `TBlock[]`/`TConnection[]`
- [x] 3.3 Add a layout-direction parameter (`LAYOUT_TOP_DOWN` | `LAYOUT_LEFT_RIGHT`, matching `plugins/c4/frontend/src/lib/diagramPreferences.ts`'s naming) that maps to ELK's `elk.direction` (`DOWN`/`RIGHT`)
- [x] 3.4 Add a pure function that merges ELK-computed positions with any steps' stored `position`, so stored positions always win over autolayout output
- [x] 3.5 Unit-test the forest-building/sibling-alignment logic still holds with the new output shape

## 4. Typed node components

- [x] 4.1 Build `ActorNode`, `ServiceNode`, `DataNode`, `ApiNode`, `SystemNode`, `TeamNode` React Flow node components (title, entity_ref-derived subtitle, palette color from 2.4), following `plugins/database-schema/frontend/src/components/TableNode.tsx`'s structure/conventions
- [x] 4.2 Build `ExternalNode` (title + `external_label`, fixed gray palette) and `StepNode` (title + optional summary, colored via Gravity UI `Label` theme from `label_theme`, theme-aware)
- [x] 4.3 Register all node components in a shared `NodeTypes` map consumed by both the read-only and editable canvases
- [x] 4.4 Build the shared edge/connection label rendering (transition `label`) using `@xyflow/react`'s built-in edge label support

## 5. Read-only diagram (detail page)

- [x] 5.1 Rewrite `FlowGraph.tsx` as a `ReactFlow` viewer (`nodesConnectable={false}`, `nodesDraggable={false}`) using the shared `NodeTypes`, following `ErDiagramView.tsx`'s read/write split
- [x] 5.2 Port zoom-in/zoom-out/fit-to-viewport toolbar to `useReactFlow()`, replacing `FlowGraphToolbar`'s `@gravity-ui/graph` camera calls
- [x] 5.3 Update `FlowDetailPage.tsx` to pass steps (including stored positions) straight through, no behavior change expected beyond the new rendering
- [x] 5.4 Update `.flow-graph__*` CSS in `index.css` for the new node components (or remove rules fully superseded by component-scoped styles)

## 6. Editable canvas foundation

- [x] 6.1 Build the new canvas editor component (replacing `FlowStepEditor.tsx`'s list) with `nodesDraggable`, `nodesConnectable={true}`, `useNodesState`
- [x] 6.2 Wire `onNodesChange`'s drag events to update the corresponding step's `position`
- [x] 6.3 Wire `onConnect` to call `flowSteps.ts`'s `canUseTransition` before committing; reject (no state change, inline message) an attempt that targets an already-targeted step, a nonexistent step, or introduces a cycle
- [x] 6.4 Wire node deletion (selection + Delete key, and/or a hover affordance) to remove the step and cascade-clear transitions targeting it, matching `FlowStepEditor.remove()`'s existing behavior
- [x] 6.5 Wire the edit page's "Clicking a diagram node selects the active editor" requirement: in Visual mode, clicking a node opens its edit modal (task 7)

## 7. Node-type picker and edit/retype modal

- [x] 7.1 Build the "Add Step" node-type picker modal (tiles: Actor, Service, Data, API, System, Team, External, Step — icon + short description each)
- [x] 7.2 For entity-backed types, show the matching `TargetRefSelect`/`RefSelect` lookup scoped to that kind; on selection, create a step with the resulting `entity_ref`
- [x] 7.3 For Step, show title/summary/`label_theme` inputs (using Gravity UI `Label` theme options)
- [x] 7.4 For External, show title/summary/`external_label` inputs
- [x] 7.5 Build the "edit existing node" flow: clicking a node opens the same modal pre-filled from its current data
- [x] 7.6 Add the "Change type" action that resets type-specific fields and re-opens the type picker within the modal
- [x] 7.7 Add id-uniqueness validation in the modal (duplicate id blocks save, matching the existing `visual-flow-editor` structural-feedback requirement)
- [x] 7.8 New steps get a fresh, non-colliding id and are added to the canvas unconnected, per the "Add Step" requirement

## 8. Layout controls

- [x] 8.1 Add an "Auto layout" toolbar button (magic-wand icon, matching `ErDiagramView.tsx`) that re-runs the layout from task 3 and overwrites every visible step's `position`
- [x] 8.2 Add the gear-icon settings `Popup` with a `SegmentedRadioGroup` for layout direction, matching `DiagramTab.tsx`'s `DiagramSettings` structure; store the choice as a local/session preference
- [x] 8.3 Ensure steps without a stored `position` are autolaid-out on initial canvas mount (task 3.4's merge logic)

## 9. JSON/Visual mode sync

- [x] 9.1 Ensure switching Visual → JSON serializes `position`, `label_theme`, `external_label` into the JSON output
- [x] 9.2 Ensure switching JSON → Visual autolayout-places any step lacking a stored `position` (per the updated "Synchronized Visual and JSON modes" requirement)
- [x] 9.3 Update `flowStepSchema.ts`-driven Monaco inline validation messages/hints for the new optional fields

## 10. Cleanup

- [x] 10.1 Remove `FlowStepEditor.tsx` once the canvas editor fully replaces it
- [x] 10.2 Check remaining repo-wide usages of `@gravity-ui/graph`; if none remain outside the Flow feature, remove the dependency from `package.json`
- [x] 10.3 Update any Storybook/docs/screenshots referencing the old Flow diagram or Visual editor look

## 11. Verification

- [x] 11.1 Manually verify each node kind (Actor, Service, Data, API, System, Team, External, Step) renders with the correct color/label on both the detail page and edit canvas
- [x] 11.2 Manually verify drag-to-connect rejects reconvergence, cycles, and unknown targets with an inline message
- [x] 11.3 Manually verify Auto layout + direction setting produce top-down and left-right arrangements correctly
- [x] 11.4 Manually verify an existing (pre-change) Flow with no stored positions still loads and renders correctly (autolayout fallback)
- [x] 11.5 Run/update frontend unit tests and backend tests touched by this change
