## 1. Backend: live title/description for entity-backed steps

- [x] 1.1 In `plugins/flows/backend/atlas_plugin_flows/models.py::resolve_step_ref_statuses`, add `title`/`description` to the dict entry already built from the resolved `CatalogEntity` row for each `entity_ref` step (alongside the existing `status`/`deprecated`) — no new query.
- [x] 1.2 Confirm this applies uniformly to all six entity-backed kinds (Actor, Team, Component, Data/Resource, API, System) — `resolve_ref()` isn't kind-filtered, so no per-kind branching is needed.
- [x] 1.3 Add/extend backend tests: title/description present when the entity resolves; absent (along with status/deprecated) when the entity_ref no longer resolves at all.

## 2. Backend: reject entity_ref + custom title/summary on save

- [x] 2.1 In `_validate_step_shape()`/`validate_steps()` (same file), add a rejection rule: a step with non-empty `entity_ref` and non-empty `title` or `summary` fails validation.
- [x] 2.2 Add backend tests: `entity_ref` + non-empty `title` rejected; `entity_ref` + non-empty `summary` rejected; `entity_ref` alone (no title/summary) still saves; Step/External steps with title/summary are unaffected by this rule.

## 3. Frontend: mirror the entity_ref/title/summary rule client-side

- [x] 3.1 In `plugins/flows/frontend/src/components/flowSteps.ts::parseFlowSteps`, add the same rejection check so a JSON-rail edit that reintroduces `entity_ref` + title/summary is caught the same way the existing `entity_ref`/`external_label`/`query_ref`/`event_ref` mutual-exclusion rule already is.

## 4. Frontend: remove Title/Summary inputs for entity-backed kinds

- [x] 4.1 In `FlowStepModal.tsx`, remove the Title/Summary `TextInput`/`TextArea` for the six entity-backed kinds (keep them for Step and External, unchanged).
- [x] 4.2 Remove the now-dead prefill-into-empty-field logic for entity-backed kinds' Title/Summary (the `prefillIfEmpty` calls tied to `entity_ref` selection) — Step/External's own prefill behavior, if any, is unaffected. Query/Event's prefill (`query_ref`/`event_ref`) is unaffected — out of scope.
- [x] 4.3 Confirm the step submitted on Save never carries `title`/`summary` for an entity-backed kind (matching the new backend/client validation rule from tasks 2/3).

## 5. Frontend: render entity-backed nodes from live data

- [x] 5.1 In `FlowNodes.tsx`, change `EntityNodeComponent`'s `title`/`subtitle` props to read from the step's live `refStatus` entry (`title`/`description` from task 1.1) instead of `step.title`/`step.summary`.
- [x] 5.2 Implement the fallback chain: live title → entity's raw name (existing `refName(entity_ref)` logic) → `step.id`, for when the reference doesn't resolve or the live title is blank.
- [x] 5.3 Confirm Component/API's existing subtype-driven icon/color (`useEntitySubtype`) is unchanged — this task only touches title/subtitle text, not icon/color resolution.
- [x] 5.4 Reuse the shared warning-icon/tooltip component introduced by `flow-stale-ref-refresh` (consumed by both `FlowNodes.tsx` and `FlowStepModal.tsx`) for the existing entity removed/deprecated warning indicator, instead of a separate implementation — see design.md Decision 6. If `flow-stale-ref-refresh` hasn't landed yet, leave the current implementation as-is and treat this as a follow-up, not a blocker.
- [x] 5.5 (Found during manual QA) Add a client-side fallback so a step with no `refStatus` entry yet (just added, or just re-pointed at a different reference, in the current edit session) still shows live-ish title/description instead of a blank card: `EntityNodeComponent` calls `useEntityRefDetails(entity_ref)` (existing, previously-unused export in `entitySubtype.ts`) only when `refStatus` has neither `title` nor `description`, and only as a rendering-only preview — never written into the step (design.md Decision 1 refinement).

## 6. Frontend: step id is not a visual-editor field

- [x] 6.1 Remove the `id` `TextInput` from `FlowStepModal.tsx`, for every step kind.
- [x] 6.2 Confirm a new step still gets a fresh id via `nextFlowStepId(steps)` with no UI prompt.
- [x] 6.3 Confirm `FlowFormPage.tsx::handleStepModalSave`'s cascade-rename branch is left in place (still legitimately used for the add/edit `previousId` distinction) even though its id-changed sub-case can no longer be triggered via the modal.

## 7. Frontend: JSON rail collapsed by default

- [x] 7.1 In `FlowFormPage.tsx`, change `isEditorOpen`'s initial state from `true` to `false`.

## 8. Frontend: JSON rail structural-validity gate

- [x] 8.1 In `FlowFormPage.tsx`, change the `useEffect` that currently does `if (parsedSteps) setSteps(parsedSteps)` to also require `validateFlowSteps(parsedSteps)` to be empty before calling `setSteps` — compute this on the candidate `parsedSteps`, not the already-committed `steps`.
- [x] 8.2 Surface the structural error inline in the same UI location already used for `jsonError`/`monacoError`, without discarding the rail's entered text.
- [x] 8.3 Confirm `handleSubmit`'s existing Save-time `structuralErrors` check (on the committed `steps`) still exists as a backstop — it should now be effectively unreachable in normal use, but is not removed.
- [x] 8.4 Add/extend frontend tests: a JSON edit that renames a step's id without updating a referencing `next_step` does not update the canvas and shows an inline structural error; fixing the reference resolves the error and the canvas updates.

## 9. Frontend: picker tile colors and layout

- [x] 9.1 In `plugins/flows/frontend/src/lib/flowNodePalette.ts`, change `FLOW_NODE_PALETTE.system` from `FLOW_NODE_SWATCHES.info` to `FLOW_NODE_SWATCHES.success`.
- [x] 9.2 Change `FLOW_NODE_PALETTE.component` from `FLOW_NODE_SWATCHES.success` to `FLOW_NODE_SWATCHES.info`.
- [x] 9.3 Confirm Component's actual canvas rendering (`componentTypeColors(subtype)` in `FlowNodes.tsx`) is unaffected by 9.2 (it never reads `FLOW_NODE_PALETTE.component`).
- [x] 9.4 Confirm System's canvas rendering picks up 9.1 automatically (it reads `FLOW_NODE_PALETTE.system` directly, same constant as the picker tile).
- [x] 9.5 In `FlowStepModal.tsx`, reorder `KIND_TILES` to: Actor, System, API, Data, External, Component, Call, Team, Event, Step (2-column grid — matches the row/column layout verified to have no adjacent same-color tiles post-9.1/9.2).

## 10. Verification

- [x] 10.1 Run existing `visual-flow-editor`/`flow-management` spec-scenario test suites (backend and frontend) — confirm no regression for any scenario not directly superseded by this change's deltas.
- [x] 10.2 Add/confirm new scenario coverage for every scenario listed in this change's spec deltas.
- [x] 10.3 Manually verify in a running distribution: add/edit an entity-backed step, confirm no Title/Summary fields are offered and the card shows live catalog data; confirm the picker has no id field for any kind; confirm the JSON rail starts collapsed; confirm renaming a step id in the JSON rail without fixing a referencing transition blocks the canvas update with an inline error until fixed; confirm the picker's System/Component tile colors and grid order.

## 11. Widened scope (found during manual QA of task 10.3): API Call/Event lose editable Title/Summary too

- [x] 11.1 In `plugins/flows/backend/atlas_plugin_flows/models.py::_validate_step_shape`, widen the entity_ref + title/summary rejection rule (task 2.1) to also cover `query_ref`/`event_ref` — a step with a non-empty `entity_ref`, `query_ref`, or `event_ref` and a non-empty `title` or `summary` fails validation.
- [x] 11.2 Add/extend backend tests mirroring task 2.2's coverage for `query_ref`/`event_ref`: each + non-empty `title` rejected; each + non-empty `summary` rejected; each alone (no title/summary) still saves.
- [x] 11.3 In `plugins/flows/frontend/src/components/flowSteps.ts::parseFlowSteps`, widen the client-side mirror (task 3.1) the same way.
- [x] 11.4 In `FlowStepModal.tsx`, remove the Title/Summary `TextInput`/`TextArea` for `call`/`event` too (widen task 4.1's gate); remove the now-dead prefill-into-empty-field calls tied to Endpoint/Operation selection (widen task 4.2); confirm the step submitted on Save never carries `title`/`summary` for `call`/`event` either (widen task 4.3).
- [x] 11.5 In `FlowNodes.tsx`, change `CallNodeComponent`/`EventNodeComponent`'s `title`/`subtitle` props to be computed from the step's own `query_ref`/`event_ref` snapshot (method+path, or channel+direction, plus the owning API's raw name via `refName`) instead of `step.title`/`step.summary` — no live fetch, preserving the offline-canvas-render invariant (design.md Decision 7).
- [x] 11.6 Update `core/backend/server/apps/catalog/management/commands/seed_booking_demo.py`'s `FLOWS` fixture: strip `title`/`summary` from every step carrying `entity_ref`, `query`, or `event` (pre-existing seed data predated this change and no longer validates) — found and fixed during manual QA (task 10.3) alongside the widened scope.
- [x] 11.7 Re-run the full backend/frontend test suites and re-seed a running distribution to confirm all 8 seeded flows validate cleanly and render correctly end to end.

## 12. Addendum (found during user review of task 11): Call/Event subtitle uses the picked Endpoint's/Operation's own summary, not just the API name

- [x] 12.1 In `plugins/flows/backend/atlas_plugin_flows/models.py`, add `REF_OPTIONAL_KEYS = frozenset({'summary'})` and widen `_validate_ref_shape()` to accept it on `query_ref`/`event_ref` — present or absent, and an empty string allowed (unlike the required keys), since the source `ApiEndpoint`/`ApiOperation.summary` field is itself optional.
- [x] 12.2 Add backend tests: `query_ref`/`event_ref` accepts an optional `summary`; accepts an empty-string `summary`; rejects a non-string `summary`.
- [x] 12.3 In `plugins/flows/frontend/src/components/flowSteps.ts`, mirror the same optional-key handling in `isRefShape()`; add `core/frontend/src/lib/types.ts`'s `FlowStepQueryRef`/`FlowStepEventRef` `summary?: string`.
- [x] 12.4 In `FlowStepModal.tsx`, capture `result.endpoint.summary`/`result.operation.summary` into `query_ref`/`event_ref` at Select `onUpdate`, the same way `method`/`path`/`channel`/`direction` already are — no live fetch.
- [x] 12.5 In `FlowNodes.tsx`, change `CallNodeComponent`/`EventNodeComponent`'s subtitle to `queryRef.summary || refName(queryRef.api)` (and the `event_ref` equivalent).
- [x] 12.6 Update `seed_booking_demo.py`'s `_resolve_flow_step()` to snapshot `endpoint.summary`/`operation.summary` into the generated `query_ref`/`event_ref` too, so the seeded demo shows real subtitles instead of always falling back to the API name.
- [x] 12.7 Re-run the full backend/frontend test suites and re-seed a running distribution; confirm via shell that every seeded `query_ref`/`event_ref` step carries a non-empty `summary` and all 8 flows still validate.
- [x] 12.8 (Found by user, opening the JSON rail on a real Flow) `plugins/flows/frontend/src/lib/flowStepSchema.ts` — the Monaco JSON-rail schema — is a separate, hand-maintained mirror of `parseFlowSteps()`/`models.py`'s shape checks with nothing enforcing they stay in sync; task 12.3 updated `parseFlowSteps()` but missed this file, so the rail rejected an already-valid, already-saved `summary` on `query_ref`/`event_ref` with "Property summary is not allowed". Add `summary: { type: 'string' }` to `queryRefSchema`/`eventRefSchema`'s `properties` (not `required`). Add a regression test asserting both schemas declare it.

## 13. Addendum (found by user, manually editing an Operation): the newly-snapshotted `summary` (task 12) can drift with zero detection — extend the existing flow-stale-ref-refresh drift check to cover it, for both event_ref and query_ref

- [x] 13.1 In `resolve_step_ref_statuses()`, extend the `event_ref` drift comparison (task from flow-stale-ref-refresh) to also compare the stored `summary` against the resolved Operation's current `summary`, independently of the existing `direction`/`channel` comparison — `live.summary` present only when it actually differs, alongside (not replacing) `live.direction`/`live.channel_address` when those also differ.
- [x] 13.2 Add a `query_ref` drift comparison — previously nonexistent, since `method`/`path` cannot drift by construction, but `summary` is an ordinary mutable field with no such guarantee. `live.summary` present only when it differs from the resolved Endpoint's current `summary`.
- [x] 13.3 Add backend tests: event_ref summary-only drift; event_ref summary + direction/channel drift together; query_ref summary drift; query_ref no drift when summary matches (including when both are blank).
- [x] 13.4 In `core/frontend/src/lib/types.ts`, widen `FlowStepRefStatus.live` to `{ direction?: string; channel_address?: string; summary?: string }` (all independently optional, from the event-only-and-always-paired `{ direction: string; channel_address: string }`).
- [x] 13.5 In `FlowRefWarning.tsx`'s `staleRefTooltip()`, add an independent summary-drift line (stacked with the existing removed/deprecated/direction-channel lines per its existing "stack every applicable condition" rule) that fires for either `query_ref` or `event_ref`. Give `RefreshRefButton` an optional `label` prop (default: the existing "Refresh from live operation" copy, unchanged for every existing call site) so a Call-node instance can say "Refresh from live endpoint" instead.
- [x] 13.6 In `FlowNodes.tsx`, wire `CallNodeComponent` up to `onRefresh`/`refreshLabel` the same way `EventNodeComponent` already is, gated on `refStatus?.live?.summary` being present (a `query_ref` has nothing else that can ever be on `live`).
- [x] 13.7 In `FlowStepModal.tsx`, add the same warning+refresh header above the Endpoint `Select` that the Operation `Select` already has; add `refreshQueryRef()` (mirrors `refreshEventRef()`, summary-only); update `refreshEventRef()` to also pull `live.summary` when present, independent of `live.direction`/`live.channel_address`; update the "refresh mode" (`autoRefresh`) effect to dispatch to `refreshEventRef`/`refreshQueryRef` based on the step's own kind (`flowNodeKindOf(step)`, not the `pickedKind` state — that state update from the seeding effect hasn't landed yet within the same commit).
- [x] 13.8 Add frontend tests mirroring the existing Event drift/refresh coverage for Call: warning+refresh shown/hidden correctly, refresh button updates only `query_ref.summary`, `autoRefresh` mode prefills it, Cancel discards it. Add an Event summary-only-drift test (no direction/channel change) to `FlowNodes.test.tsx`/`FlowStepModal.test.tsx`.
- [x] 13.9 Re-run the full backend/frontend test suites; rebuild and restart the running distribution's `frontend`/`backend` containers; confirm via shell against a real Flow with a manually-edited Operation/Endpoint summary that `live.summary` is now reported where it previously wasn't.

## 14. Addendum (found in user review of task 13): the canvas card's `↻` should apply directly, not route through the edit modal

- [x] 14.1 In `plugins/flows/frontend/src/components/flowSteps.ts`, add a pure `refreshStepRef(steps, stepId, live)` mutator (alongside `addTransition`/`removeTransition`/etc.): applies `live.summary` onto a step's `query_ref`, or `live.direction`+`live.channel_address` (as a pair) and/or `live.summary` (independently) onto its `event_ref`; a no-op when `live` is unset or the step has neither ref.
- [x] 14.2 In `FlowCanvasEditor.tsx`, change both `onRefresh` wirings (the layout effect and `handleAutoLayout`) from `(stepId) => onEditStep(stepId, {refresh: true})` to `(stepId) => onChange(refreshStepRef(steps, stepId, refStatus?.[stepId]?.live))` — matches `removeSteps`'s existing directness (no modal, undone only by not saving the Flow) rather than requiring an extra "open modal, click Save" round trip for a single-field change.
- [x] 14.3 Remove the now-dead `{refresh?: boolean}` option from `FlowCanvasEditorProps.onEditStep` and `FlowFormPage.tsx`'s `handleEditStep`; remove `autoRefresh` from `stepModal` state and the `<FlowStepModal>` call site.
- [x] 14.4 In `FlowStepModal.tsx`, remove the `autoRefresh` prop and the effect that consumed it; keep `refreshEventRef()`/`refreshQueryRef()` themselves unchanged — they're still reachable via the modal's own `↻` button (shown when a step happens to be open in the modal and its ref is stale), which still only fills in-memory form state, committed only by the modal's explicit Save.
- [x] 14.5 Update stale doc comments referencing the old "opens the modal in refresh mode" behavior (`flowLayout.ts`'s `onRefresh` doc, `FlowNodes.tsx`'s Event `onRefresh` wiring comment).
- [x] 14.6 Add `flowSteps.test.ts` coverage for `refreshStepRef`: query_ref summary, event_ref direction+channel, event_ref summary independent of direction/channel, both together, no-op when `live` is undefined, no-op for a step with neither ref. Remove the two now-dead `autoRefresh`-mode tests from `FlowStepModal.test.tsx` (their behavior no longer exists).
- [x] 14.7 Re-run the full backend/frontend test suites; confirm `tsc -b`/`oxlint` clean.
