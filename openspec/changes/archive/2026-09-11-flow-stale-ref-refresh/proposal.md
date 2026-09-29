## Why

`add-flow-query-event-steps` (archived 2026-09-08) explicitly accepted, then deferred, the risk that an Event step's `event_ref.direction`/`channel` snapshot can silently drift from the live `ApiOperation` after an AsyncAPI re-import — `operation_key` (not `direction`/`channel_address`) is that model's upsert identity, so a re-import can mutate direction/channel on the *same* row a Flow already references. `flow-node-vocabulary-alignment` (archived 2026-09-09) later added a stale-reference warning, but only for `status: removed` / `deprecated: true` — it never compares `direction`/`channel`, so the exact scenario flagged and deferred by the first change (documented in `local/flow-operation-bugs.md`) still produces zero warning anywhere in the product today. Verified directly in code: `resolve_step_ref_statuses()` (`plugins/flows/backend/atlas_plugin_flows/models.py`) and `staleRefTooltip()` (`plugins/flows/frontend/src/components/FlowNodes.tsx`) both only ever branch on `status`/`deprecated`.

Separately, once a stale reference is flagged, there is today no way to act on it from the UI short of manually reopening the Endpoint/Operation picker and reselecting the same item — an unintuitive workaround the average Flow author won't discover.

## What Changes

- Extend `resolve_step_ref_statuses()` to also compare an `event_ref`'s stored `direction`/`channel` against the resolved live `ApiOperation`'s `direction`/`channel_address`, and include the live values in that step's ref-status entry when they differ. Read-time only, computed at serialization — the stored `Flow.steps` JSON is never touched. `query_ref` gets no equivalent check: an `ApiEndpoint`'s `(method, path)` is its own upsert identity, so a `query_ref` snapshot cannot drift by construction (unchanged from `add-flow-query-event-steps` design.md Decision 2).
- Extend the existing stale-reference warning triangle to show this new drift signal on an Event node, with copy showing the saved value against the current one. The same warning now also renders inside the step-edit modal, not only on the canvas card (today it's canvas-only).
- Add a new refresh (`↻`) action next to the warning triangle, in both places, visible only on an Event node with the direction/channel drift above — a Query node has nothing to refresh (its snapshot cannot drift), and an entity-backed node's `entity_ref` is out of scope for this change (see Scope note below).
  - Clicking it pre-fills the step-edit modal's `event_ref` inputs from live data. This only touches in-memory form state — nothing is persisted until the user explicitly saves the step, and closing/cancelling discards it, same as any other unsaved edit.
  - A normal (non-`↻`) click on a node or on an existing step continues to open the modal with **no** prefill, exactly as today — editing a step's title alone must never silently carry a refreshed `event_ref` snapshot along with it.
- No new backend endpoint, no new mutation surface, no schema/migration change. `validate_steps()` stays a pure validator; a drifted `event_ref` remains a non-blocking condition on save (matches current behavior — drift was never checked before either; this change makes that explicit rather than incidental).

## Capabilities

### New Capabilities
_None._ This change extends the read-time live-status and stale-indicator machinery already specified across three existing capabilities.

### Modified Capabilities
- `flow-query-event-steps`: the "Reading a Flow surfaces live status of referenced Endpoints/Operations" requirement gains a direction/channel drift comparison for `event_ref` steps, alongside the existing `status`/`deprecated` live status.
- `flow-management`: the "Flow diagram nodes visibly flag a removed or deprecated referenced entity" requirement is extended so the same warning indicator (a) also covers an Event node's direction/channel drift, and (b) renders in the step-edit modal in addition to the canvas.
- `visual-flow-editor`: new requirements for the refresh (`↻`) action on an Event node — an interactive, opt-in remediation available wherever the direction/channel-drift warning appears on the editable canvas/modal, distinct from the existing read-only warning indicator.

## Impact

- Backend: `plugins/flows/backend/atlas_plugin_flows/models.py` (`resolve_step_ref_statuses`) — new direction/channel comparison for `event_ref`, using the existing batched `atlas_plugin_apis.extension_points.resolve_operations()` call already made there. No changes to `validate_steps()`, no new routes, no migration.
- Frontend: `plugins/flows/frontend/src/components/FlowNodes.tsx` (`staleRefTooltip`, warning rendering), `FlowStepModal.tsx` (new `refStatus` prop, in-modal warning + refresh UI, prefill-on-demand logic for `event_ref`), `FlowFormPage.tsx`/`FlowCanvasEditor.tsx` (thread `refStatus` for the edited step into the modal), `lib/types.ts` (extend the `FlowStepRefStatus` shape with the new live-value field).

## Scope note

An earlier draft of this change also covered entity-backed nodes (`entity_ref`): a warning + refresh action for a `removed`/`deprecated` referenced entity, gated on status only (explicitly not a text-diff against the entity's `title`/`description`, since those step fields were free text). That entity-backed scope has been superseded by a separate, broader change that removes `entity_ref`-backed steps' `title`/`summary` free text entirely — once those fields are never author-editable, there is nothing for a "refresh" action to do for an entity-backed node: the card always renders the live entity's current name/description already, and the existing removed/deprecated warning (unchanged, pre-existing) is sufficient on its own. This change is scoped to `event_ref` only.
