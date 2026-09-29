## Why

Step is Flow's single generic, fully-customizable non-entity-backed node kind (established by `flow-canvas-palette-unification`), carrying an author-chosen color and icon — but its type chip always reads the fixed word "Step", no matter what the node actually represents (a retry point, a manual approval, a notification). EventCatalog's own Custom node solves this with a free-text "Type Label" field, and that gap was explicitly called out and deferred in `flow-canvas-palette-unification`'s design.md as a Non-Goal ("not requested, not in scope") — it's now requested. Letting an author override the chip text closes that gap without adding a new node kind or schema field for every ad-hoc concept.

## What Changes

- Step gains an optional `type_label` field: free-text, author-chosen, shown on the node's type chip instead of the fixed word "Step". Unset (or blank) falls back to "Step" — no author action required, no migration.
- `FlowStepModal.tsx`'s Step config panel gains a "Type label" text input (placeholder/default "Step"), alongside the existing color and icon fields.
- No other node kind is affected — Actor/Team/Service/Data/API/System/External/Query/Event keep their fixed or derived chip labels; this is Step-only, matching Step's existing role as the one generic kind.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `visual-flow-editor`: Step's node-type picker fields gain an optional type label; Step's chip-label source changes from always-fixed to author-chosen-with-fallback.

## Impact

- `plugins/flows/frontend/src/lib/flowStepSchema.ts` — add optional `type_label` (free-text string) to the step JSON schema.
- `core/frontend/src/lib/types.ts` — add `type_label?: string` to the `FlowStep` interface.
- `plugins/flows/frontend/src/lib/flowNodeKind.ts` — add a `stepTypeLabel`-style resolver (chosen value, falling back to `FLOW_NODE_KIND_LABELS.step`), mirroring `stepIcon`'s existing chosen-value-with-fallback pattern.
- `plugins/flows/frontend/src/components/FlowNodes.tsx` — `StepNodeComponent` uses the resolved type label instead of the fixed `FLOW_NODE_KIND_LABELS.step` constant for its chip.
- `plugins/flows/frontend/src/components/FlowStepModal.tsx` — new optional "Type label" text field in Step's config panel.
- `openspec/specs/visual-flow-editor/spec.md` — requirement text/scenarios for Step's fields gain the type label.
- No backend/API changes — stays within the existing Flow `steps` JSON grammar and its frontend schema/validation.
