## Context

Two archived changes shape this one directly:

- `add-flow-query-event-steps` (2026-09-08) introduced `query_ref`/`event_ref` as point-in-time snapshots, deliberately never re-derived on save (Decision 2: "Snapshot, not a live pointer"). It explicitly flagged that an Event's `direction`/`channel` can drift from the live `ApiOperation` after an AsyncAPI re-import — `operation_key` is that model's upsert identity, while `direction`/`channel_address` are ordinary mutable fields the importer freely overwrites on the same row — and deferred building any detection for it ("Open Questions: whether a future change should add a lightweight stale indicator... explicitly deferred").
- `flow-node-vocabulary-alignment` (2026-09-09) added a stale-reference warning (Decision 4), but scoped it to `status: removed` / `deprecated: true` only. It never compares `direction`/`channel`, so the drift scenario the first change deferred is still, today, completely unflagged.

`local/flow-operation-bugs.md` re-raised this gap with a worked example (`Flow snapshot: send orders.created` vs. `Live operation: receive orders.events`) and proposed a state model (`current/stale/removed/missing/unavailable`) plus an explicit "update snapshot" user action. This design adopts the detection/state-model half of that proposal, but takes a different, lighter path for the remediation half — see Decision 5.

Current code, confirmed by inspection:
- `plugins/flows/backend/atlas_plugin_flows/models.py::resolve_step_ref_statuses` returns only `{status, deprecated}` per step, via the existing batched `atlas_plugin_apis.extension_points.resolve_endpoints`/`resolve_operations`.
- `plugins/flows/frontend/src/components/FlowNodes.tsx::staleRefTooltip`/`staleEntityRefTooltip` branch only on those same two fields.
- `EventNodeComponent` colors/labels the card purely from the stored snapshot (`eventRef.direction`), with no fetch — this render path is unchanged by this design.
- `FlowStepModal` has no awareness of `refStatus` at all today; it initializes its `eventRef`/title/summary form state directly from `step.event_ref`/`step.title`/`step.summary`.

## Goals / Non-Goals

**Goals:**
- Detect, at Flow read time, when a step's `event_ref.direction`/`channel` disagrees with its live `ApiOperation`, and surface the current values alongside the existing `status`/`deprecated` signal — without touching the stored snapshot.
- Extend the existing stale-reference warning to show this new signal, and to appear inside the step-edit modal as well as on the canvas card.
- Give the Flow author a single, opt-in way to pull live `direction`/`channel` values into the edit form for a drifted Event step, without ever auto-applying them — the author still explicitly saves or discards.
- Keep `validate_steps()` a pure validator and the canvas's render-from-JSON-only invariant exactly as `add-flow-query-event-steps` established them.

**Non-Goals:**
- No entity-backed (`entity_ref`) node scope of any kind — refresh, drift comparison, or otherwise. See Scope note in proposal.md: a separate change removes `entity_ref`-backed steps' `title`/`summary` free text entirely, making any such mechanism here moot.
- No change to `query_ref`/Call-node behavior beyond what already exists. An `ApiEndpoint`'s `(method, path)` is its own upsert identity (`openapi_import.py::_upsert_operation`), so a `query_ref` snapshot cannot drift — confirmed unchanged from `add-flow-query-event-steps` design.md Decision 2.
- No new backend endpoint, mutation command, or "update snapshot" lifecycle action. No schema change, no migration.
- No general "is this reference current" versioning field (`display_revision` or similar) on `ApiOperation` — direct field comparison remains sufficient, matching the original change's own rejection of this for the same reason.
- No auto-sync on save or on read — a drifted `event_ref` remains a valid, savable Flow; this change only makes the drift visible and easy to fix, never mandatory.

## Decisions

### Decision 1 — Drift computed by extending `resolve_step_ref_statuses`, not a new interface

The existing function already resolves every step's `event_ref.operation` in one batched call (`resolve_operations`) to produce `status`/`deprecated`. Add a direct comparison — `event_ref.direction != operation.direction or event_ref.channel != operation.channel_address` — using the same already-resolved rows, no second lookup. This mirrors `local/flow-operation-bugs.md`'s own recommendation ("Самая точная проверка — прямое сравнение семантически значимых полей") and its explicit rejection of `updated_at`-based checks: the importer's `_OPERATION_DOC_FIELDS` also covers `summary`/`description`/`tags`/`message`/`channel_protocol`/`operation_id`/`status`, so a timestamp check would false-positive on unrelated field changes.

Rejected: a `display_revision` counter on `ApiOperation`, bumped only on `direction`/`channel_address` change — would need a migration and new lifecycle logic for a comparison that's already cheap to do directly today; the same conclusion the original change reached.

### Decision 2 — New signal shape: presence-based `live` value on the existing ref-status entry

Extend each step's ref-status entry with an optional field carrying the live `direction`/`channel` — populated only when they actually differ from the snapshot, so its mere presence is the drift signal (no separate boolean needed). This follows the same "presence selects behavior" idiom `add-flow-query-event-steps` design.md Decision 1 already established for `external_label` and the two ref fields themselves.

Rejected: a separate top-level staleness map alongside the existing ref-status map — two payloads answering the same "what's live for this step" question is one more thing for every caller to merge, for no benefit over extending the map that already exists and is already threaded through `FlowGraph`/`FlowCanvasEditor`/`FlowFormPage`.

### Decision 3 — Warning copy shows every true condition, not just the highest-precedence one

Today's tooltip picks one branch (`removed` text, else `deprecated` text). This change adds a third, orthogonal fact (drift) that can be true independently of `status`/`deprecated` — an Operation can be perfectly active and non-deprecated while its `direction`/`channel` has still changed. Rather than extending the existing if/elif precedence chain with a third rung (which would silently hide the drift line whenever `removed`/`deprecated` is also true), the tooltip stacks every applicable line: removed/deprecated copy (if any) followed by the before/after drift comparison (if any). A single icon still represents "something needs attention"; the tooltip body is the only place detail is added.

### Decision 4 — The warning now also renders inside `FlowStepModal`

`FlowFormPage` already holds the full `refStatus` map (used today only to feed the canvas). Thread the single entry for the step currently open in the modal down as a new `FlowStepModal` prop. No new fetch — this is prop-plumbing only. The modal renders the same warning component the canvas card uses, next to the Operation select.

### Decision 5 — Refresh is a client-only, opt-in action routed through the ordinary Flow save — not a new server command

`local/flow-operation-bugs.md` proposed a distinct, explicitly-invoked "update snapshot" command as a separate action from ordinary editing. This design reaches the same outcome — the snapshot is never touched without deliberate author action — through a cheaper mechanism: a small `↻` control, shown only next to an active drift warning, that copies the already-available `refStatus.live` value (computed for the warning itself) into the modal's in-memory `event_ref` form state. Nothing is persisted until the author clicks the modal's existing Save — at which point it is just an ordinary step edit, going through the unmodified `validate_steps()` path.

This is deliberately *not* wired into the default open-for-edit flow: opening a step by clicking its card (not its `↻`) initializes form state from the stored step exactly as today, with no prefill. Only an explicit `↻` click populates live values. This is the load-bearing guarantee: an author fixing an unrelated typo in a step's title never silently carries a refreshed `event_ref` along with that save.

Rejected: a dedicated backend "sync snapshot" endpoint/command. It would add a new mutation surface and (per the original change's own stated Goal) turn part of the Flow-editing lifecycle into something more than `validate_steps()` validating what the client already decided to send — for no capability the client-side prefill-then-ordinary-save path doesn't already provide.

### Decision 6 — Query/Call nodes are unaffected

No drift check, no `↻` control, for `query_ref`. Its snapshot cannot drift by construction (Decision "Non-Goals" above); the existing `status`/`deprecated`-only warning is already complete for it.

## Risks / Trade-offs

- **[Two implementations of one control]** The `↻` action appears both on the canvas card and inside the modal. → Mitigation: implement it as one small shared component/handler consumed from both `FlowNodes.tsx` and `FlowStepModal.tsx`, not two parallel implementations.
- **[`refStatus` reflects last page load, not the instant of the click]** The live values used to prefill on refresh come from the Flow's last read, same as the passive warning already tolerates. → Accepted: identical staleness tolerance the existing `status`/`deprecated` warning already has; a page reload gets fully current data. Not a new risk this change introduces.
- **[Combined tooltip copy could get long]** Decision 3's "stack every true condition" could, in the rare case of a removed *and* drifted Operation, show two lines instead of one. → Accepted: still bounded (at most two short lines), and strictly more informative than picking one and hiding the other.

## Migration Plan

1. Backend: `resolve_step_ref_statuses` — add the `direction`/`channel` comparison and the new `live`-value field for `event_ref` steps (Decisions 1-2).
2. Frontend types: extend `FlowStepRefStatus` (`lib/types.ts`) with the new optional live-value field.
3. Frontend: `FlowNodes.tsx` — extend the warning tooltip to stack the drift line (Decision 3); extract the shared `↻` control.
4. Frontend: `FlowStepModal.tsx` — accept a `refStatus` prop for the step being edited; render the same warning + `↻` control next to the Operation select; wire `↻` to prefill `eventRef` form state only (Decisions 4-5).
5. Frontend: `FlowFormPage.tsx`/`FlowCanvasEditor.tsx` — pass the current step's `refStatus` entry into `FlowStepModal`.
6. Verify: existing `flow-query-event-steps`/`flow-management`/`visual-flow-editor` spec-scenario suites pass unmodified for every case that isn't new; new scenarios (this change's specs deltas) pass; a normal (non-`↻`) edit of any step, including one with an active warning, persists with its snapshot unchanged.

Rollback: every step above is an independently revertible code addition — no data migration, no new route, no manifest change to unwind.

## Open Questions

- Exact key name for the new live-value field on the ref-status entry (e.g. `live` vs `current`) — mechanical, resolved during implementation.
- Precise placement/icon for the `↻` control on the canvas card (inline with the triangle vs. a small adjacent hit-target) — a design-system detail, not a behavioral decision, left to implementation.
