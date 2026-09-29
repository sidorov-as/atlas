## Why

Flow diagrams currently have no way to reference another Flow or an external resource — a scenario that continues into a different Flow, or that depends on outside documentation, has no node to represent that. Separately, the "Add Step" node-type picker's grid currently holds exactly 10 tiles (5 full rows of 2); it reads as visually complete today, but any single addition would leave a half-empty final row.

## What Changes

- Add a **Flow** node kind: a step referencing another Flow by id (`flow_ref`). Structurally ref-backed like Actor/Team/Component/Data/API/System — its title and subtitle are always the target Flow's live `name`/`description`, never author-typed text. Uses the same `BranchesRight` icon as the "Flows" sidebar nav item.
- Add a **Link** node kind: a step referencing an arbitrary external URL (`link_url`). Structurally freeform like External/Step — its title and summary are author-typed and optional, falling back to the URL itself (never the step's opaque auto-generated id) when no title is given. Uses the `Link` icon (plain chain glyph).
- Add a read-only-only **navigate button** (outbound-link icon) to both node kinds' card, opening the target — the referenced Flow's detail page, or the stored URL — in a new browser tab. Rendered only on the read-only detail-page canvas, never on the editable canvas (where clicking a node already opens its edit modal). Dragging a canvas pan gesture that starts on a Flow/Link node's card does not trigger navigation — only a direct activation of the button does.
- Extend the "Add Step" node-type picker from 10 to 12 tiles, filling the grid evenly again, with Flow/Link tiles assigned colors that don't clash with their row/column neighbors.
- Extend the `FlowStep` JSON grammar with `flow_ref` (integer Flow id) and `link_url` (string), mutually exclusive with each other and with the existing `entity_ref`/`external_label`/`query_ref`/`event_ref` fields, validated on save on both backend and frontend. `link_url` is rejected on save unless it is a well-formed absolute `http`/`https` URL.
- Surface live status for `flow_ref` targets on read (current `name`/`description`, and whether the target Flow still exists) mirroring the existing live-status surfacing for `entity_ref`/`query_ref`/`event_ref`, and show a stale-reference warning indicator (with the navigate button disabled) when a Flow node's target no longer exists.

## Capabilities

### New Capabilities
- `flow-node-linking`: the `FlowStep` JSON grammar, validation, and live-status surfacing for the new `flow_ref` and `link_url` fields — mirrors how `flow-query-event-steps` covers `query_ref`/`event_ref`.

### Modified Capabilities
- `flow-management`: "Flow diagram nodes are typed and colored by kind" gains Flow and Link kind rendering rules.
- `visual-flow-editor`: "Visual Flow step authoring" gains Flow and Link tiles in the node-type picker (a Flow search lookup, and Link's own title/summary/URL fields); "Unified node visual styling" and "Node-type picker tile colors and layout" extend to the two new fixed-color kinds and the now-12-tile grid; new requirements cover the Flow reference lookup, the read-only navigate button, and a stale Flow-reference indicator.

## Impact

- Frontend: `plugins/flows/frontend/src/lib/flowNodeKind.ts`, `flowNodePalette.ts`, `components/flowSteps.ts`, `components/FlowNodes.tsx`, `components/FlowStepModal.tsx`, `components/FlowGraph.tsx`, `components/FlowRefWarning.tsx`, `core/frontend/src/lib/types.ts` (`FlowStep`), `core/frontend/src/lib/entities.ts` (`flowsApi` reused for the new Flow lookup).
- Backend: `plugins/flows/backend/atlas_plugin_flows/models.py` (`_validate_step_shape`, live-status resolution), `api/schemas.py`.
- No breaking changes — existing steps and their kinds are unaffected; the new fields are additive to the `steps` JSON grammar.
