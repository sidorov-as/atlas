## Why

A Flow step's "Add Step"/edit modal has always had two free-text fields — "Title" and "Summary" — both start blank for a fresh step. When an author picks a reference (a Component, an Endpoint, an Operation, ...), nothing in the form reflects what was just picked: the author has to separately retype the entity's name into "Title" to get a sensible card label, and often skips it, leaving the canvas card headlined by a bare step id or a paraphrase that drifts from what the step actually refers to.

## What Changes

- When an author selects or changes a step's reference — `entity_ref` for Actor/Team/Component/Data/API/System, or a picked Endpoint/Operation for API Call/Event — the modal prefills the **Title** field with the reference's real name (or, for API Call/Event, its snapshotted `method`+`path` / `channel`+direction) and the **Summary** field with the reference's own description/summary, whenever those fields are currently empty.
- Prefill never overwrites text the author already typed — it only fills a blank field, and only at the moment a reference is selected or changed. Once filled (by prefill or by hand), a step's Title/Summary are never automatically resynced to the reference again.
- The "Title"/"Summary" fields keep their existing labels for every kind — no relabeling, no read-only preview line.
- Canvas card title (`FlowNodes.tsx`) is unchanged: every kind still shows `step.title || step.id`. Canvas card *subtitle*, for entity-backed kinds and for API Call/Event, now prefers the step's own `summary` once it's filled — by the prefill above or typed by hand — instead of always showing the reference's raw identity. While `summary` is still blank, subtitle falls back to that identity exactly as it renders today: the referenced entity's name for entity-backed kinds, the owning API's name for API Call/Event.
- No change to the persisted Flow `steps` JSON grammar: `title`/`summary` keep their exact field names and shapes; this is a form-default and card-rendering change only, not a data migration.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `visual-flow-editor`: the node-type picker/edit modal prefills a step's Title/Summary from its selected reference's own name/description (or method+path/channel+direction + summary for API Call/Event) whenever those fields are empty; the canvas card's subtitle shows that Summary once filled, falling back to the reference's identity while it's empty.

## Impact

- `plugins/flows/frontend/src/components/FlowStepModal.tsx` — prefill-on-selection logic for the Title/Summary fields.
- `plugins/flows/frontend/src/lib/entitySubtype.ts` — generalized from a Component/API-only subtype lookup into a shared entity_ref detail resolver (title + description, plus the existing subtype) covering all six entity-backed kinds.
- `plugins/flows/frontend/src/lib/apiSearch.ts` — widens `EndpointSearchResult`/`OperationSearchResult`'s frontend types to read the `summary` field the backend's `EndpointOut`/`OperationOut` already return.
- No backend changes: the Endpoint/Operation search endpoints already return `summary` in their response body; only the frontend type/usage catches up.
- `plugins/flows/frontend/src/components/FlowNodes.tsx` — `EntityNodeComponent`/`CallNodeComponent`/`EventNodeComponent`'s subtitle now prefers `step.summary`, falling back to the reference's identity (entity name / owning API name) only while `summary` is blank. Card *title* is untouched. This does not revive the earlier draft's title/subtitle remapping or its "Description" field — no modal relabeling, no new fetch, no third field.
- Depends on `flow-node-vocabulary-alignment` (Component/API Call vocabulary) being archived first — this proposal is written in terms of that change's post-archive vocabulary.
