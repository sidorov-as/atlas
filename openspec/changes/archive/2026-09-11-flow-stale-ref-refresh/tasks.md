## 1. Backend: Event direction/channel drift detection

- [x] 1.1 In `plugins/flows/backend/atlas_plugin_flows/models.py::resolve_step_ref_statuses`, for each step with a non-empty `event_ref` whose Operation resolves, compare `event_ref.direction`/`event_ref.channel` against the resolved Operation's `direction`/`channel_address` (reuse the existing batched `resolve_operations()` call already made in this function — no new lookup).
- [x] 1.2 When they differ, add the live `direction`/`channel_address` to that step's ref-status entry, alongside the existing `status`/`deprecated` keys. Omit this field entirely when there is no drift (presence-based signal, per design.md Decision 2).
- [x] 1.3 Confirm `query_ref` entries are untouched by this change — no drift field is ever added for a Query step.
- [x] 1.4 Add/extend backend tests covering: drift present, drift absent (values match), Operation not resolvable (no live status at all, existing behavior unchanged), `atlas.apis` not installed (existing behavior unchanged).

## 2. Frontend: types and shared warning/refresh primitives

- [x] 2.1 Extend `FlowStepRefStatus` (`core/frontend/src/lib/types.ts` or wherever it's defined per `flowLayout.ts`'s re-export) with the new optional live-value field from task 1.2.
- [x] 2.2 In `plugins/flows/frontend/src/components/FlowNodes.tsx`, extend `staleRefTooltip` so the tooltip stacks every applicable condition (removed/deprecated copy, then the drift before/after comparison) instead of an if/elif chain that only shows one (design.md Decision 3).
- [x] 2.3 Extract a small shared "warning + refresh control" component/handler (or a pair of tightly-coupled functions) usable from both `FlowNodes.tsx` (canvas card) and `FlowStepModal.tsx` (modal), so the two call sites share one implementation (design.md Risk: "Two implementations of one control").
- [x] 2.4 The refresh control renders only when there's something to refresh: an Event node with drift (from 1.2). Never for a Query node.

## 3. Frontend: canvas card integration

- [x] 3.1 Render the refresh control next to the existing `StaleRefWarning` triangle on `EventNodeComponent` when drift is present.
- [x] 3.2 Confirm `CallNodeComponent` gains no refresh control (Query is unaffected, design.md Decision 6).
- [x] 3.3 Wire the canvas refresh control's click to open the step-edit modal for that step in "refresh" mode (see task 4).

## 4. Frontend: step-edit modal integration

- [x] 4.1 Add a `refStatus` prop to `FlowStepModal` (the single ref-status entry for the step being edited, not the whole map).
- [x] 4.2 Render the same warning icon/tooltip inside the modal, next to the Operation select for an Event step, whenever `refStatus` indicates drift, mirroring the canvas card.
- [x] 4.3 Render the refresh control next to that in-modal warning, under the same visibility rule as task 2.4.
- [x] 4.4 Implement the refresh behavior: clicking the control (canvas or in-modal) sets `eventRef` state from the live `direction`/`channel` in `refStatus` — writing to component state only, no persistence.
- [x] 4.5 Confirm the modal's default initialization (opening via a normal card click, not the refresh control) is unchanged — `eventRef` state still comes straight from `step.event_ref`, with no prefill.
- [x] 4.6 Confirm Cancel/close after a refresh discards the prefilled state without persisting anything (this should fall out of existing modal state lifecycle, but verify explicitly).

## 5. Frontend: threading refStatus into the modal

- [x] 5.1 In `FlowFormPage.tsx`, pass the ref-status entry for the step currently open in `FlowStepModal` (looked up from the existing full `refStatus` map already in scope) as the new prop from task 4.1.
- [x] 5.2 Check `FlowCanvasEditor.tsx`'s own `FlowStepModal` usage (if it renders one independently of `FlowFormPage`) and thread the same prop there if applicable.

## 6. Verification

- [x] 6.1 Run existing `flow-query-event-steps`/`flow-management`/`visual-flow-editor` spec-scenario test suites (backend and frontend) — confirm no regression for any pre-existing scenario.
- [x] 6.2 Add/confirm new scenario coverage for every scenario listed in this change's spec deltas (drift reporting, stacked tooltip copy, modal parity, refresh control visibility and behavior, no-op for Query).
- [x] 6.3 Manually verify in a running distribution: re-import an AsyncAPI spec that changes an Operation's `direction`/`channel`, confirm the existing Flow's Event node shows the new warning, confirm the refresh control populates the modal's Operation field without saving, confirm Save persists the new snapshot and Cancel does not.
