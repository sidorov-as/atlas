## 1. Revert card rendering (superseded draft)

- [x] 1.1 In `plugins/flows/frontend/src/components/FlowNodes.tsx`, revert `EntityNodeComponent`'s `title`/`subtitle` back to `title={step.title || step.id}` / `subtitle={step.entity_ref ? refName(step.entity_ref) : undefined}`.
- [x] 1.2 Revert `CallNodeComponent`'s `title`/`subtitle` back to `title={step.title || step.id}` / `subtitle={queryRef ? \`${queryRef.method} ${queryRef.path}\` : undefined}`.
- [x] 1.3 Revert `EventNodeComponent`'s `title`/`subtitle` back to `title={step.title || step.id}` / `subtitle={eventRef ? \`${eventRef.channel} (${eventRef.direction})\` : undefined}`.
- [x] 1.4 Revert the accompanying doc-comment edits on `EntityNodeComponent`/`CallNodeComponent`/`EventNodeComponent` back to their original wording (no longer describe a title/subtitle promotion).
- [x] 1.5 In `plugins/flows/frontend/src/components/FlowNodes.test.tsx`, remove the "node title/subtitle promotion" describe block added by the earlier draft — no longer applicable.

## 2. Entity reference detail lookup (generalized across all six kinds)

- [x] 2.1 In `plugins/flows/frontend/src/lib/entitySubtype.ts`, generalize the per-kind `q`-search-by-name fetch to cover all six entity-backed kinds (`user`→`usersApi`, `group`→`groupsApi`, `component`→`componentsApi`, `resource`→`resourcesApi`, `api`→`apisApi`, `system`→`systemsApi`), reading `metadata.title`/`metadata.description` off the matched item in addition to the existing `spec.type` (only present for component/api). Branch on `usersApi.list()`'s bare-array response shape vs. the other five kinds' `Paginated<T>` shape, mirroring `RefSelect.tsx`'s `useRefItems`.
- [x] 2.2 Keep `useEntitySubtype(entityRef)`'s existing return contract (`string | undefined`) built on the shared cache/fetch. Add `useEntityRefDetails(entityRef)`, built on the same cache, returning `{ title: string, description: string } | undefined`.
- [x] 2.3 In `plugins/flows/frontend/src/lib/apiSearch.ts`, add `summary: string` to `EndpointSearchResult['endpoint']` and `OperationSearchResult['operation']` — the backend's `EndpointOut`/`OperationOut` already return this field, no backend change needed.

## 3. Prefill Title/Summary on reference selection

- [x] 3.1 In `FlowStepModal.tsx`, drop the earlier draft's `hasReference`/`referencePreview` computation and the read-only preview block; restore the free-text field's label to a plain, unconditional "Title" for every kind (as it was before this change).
- [x] 3.2 Wire prefill into `RefSelect`'s `onChange` (not a passive `entityRef`-keyed effect — that would also fire when the modal re-seeds an existing step's `entityRef` on open/edit, which the Migration Plan requires stays inert): on selecting a non-null ref, call `fetchEntityRefDetails` (`entitySubtype.ts`, imperative one-shot resolution) and prefill `title`/`summary` from the result via the shared `prefillIfEmpty` helper, only into whichever field is currently empty.
- [x] 3.3 Wire prefill into the API Call `Select`'s `onUpdate`, alongside the existing `setQueryRef` call: when a search result is picked, prefill `title` with `${result.endpoint.method} ${result.endpoint.path}` and `summary` with `result.endpoint.summary` (data already in the search result, no extra fetch), only into empty fields.
- [x] 3.4 Wire prefill into the Event `Select`'s `onUpdate` the same way: `title` from `${result.operation.channelAddress} (${result.operation.direction})`, `summary` from `result.operation.summary`.

## 4. Tests

- [x] 4.1 Rewrite `FlowStepModal.test.tsx`'s label/preview-focused tests (from the earlier draft) into coverage of the new prefill behavior: selecting an entity reference for a step with empty Title/Summary fills both from the resolved entity's title/description; selecting an Endpoint/Operation fills Title from its method+path/channel+direction and Summary from its own `summary`; a step with an already-typed Title/Summary keeps it unchanged after selecting (or changing) a reference.
- [x] 4.2 Run the full `plugins/flows/frontend` test suite; fix any incidental breakage.

## 6. Card subtitle prefers Summary, falling back to the reference's identity

- [x] 6.1 In `plugins/flows/frontend/src/components/FlowNodes.tsx`, change `EntityNodeComponent`'s `subtitle` from `step.entity_ref ? refName(step.entity_ref) : undefined` to `step.summary || (step.entity_ref ? refName(step.entity_ref) : undefined)`.
- [x] 6.2 Change `CallNodeComponent`'s `subtitle` from `queryRef ? \`${queryRef.method} ${queryRef.path}\` : undefined` to `step.summary || (queryRef ? refName(queryRef.api) : undefined)`.
- [x] 6.3 Change `EventNodeComponent`'s `subtitle` from `eventRef ? \`${eventRef.channel} (${eventRef.direction})\` : undefined` to `step.summary || (eventRef ? refName(eventRef.api) : undefined)`.
- [x] 6.4 Update the doc-comments on `EntityNodeComponent`/`CallNodeComponent`/`EventNodeComponent` to describe the new subtitle sourcing (Summary first, reference-identity fallback when Summary is empty) instead of the reverted "always the reference's identity" wording from task 1.

## 7. Tests

- [x] 7.1 In `plugins/flows/frontend/src/components/FlowNodes.test.tsx`, add coverage: an entity-backed node with a non-empty `step.summary` shows that summary as its subtitle instead of the entity's name; the same node with an empty `summary` falls back to the entity's name exactly as before task 6. Mirror both cases for `CallNodeComponent`/`EventNodeComponent`, whose fallback is the owning API's name (`refName(query_ref.api)`/`refName(event_ref.api)`), not the method+path/channel+direction shown in the title.
- [x] 7.2 Run the full `plugins/flows/frontend` test suite; fix any incidental breakage.

## 8. Spec and final verification

- [x] 8.1 Confirm `openspec/specs/visual-flow-editor/spec.md` matches this change's delta spec after archive.
- [x] 8.2 Manually verify in the running app (`/flows/{id}/edit`): picking a Component/Actor/etc. reference for a step with empty Title/Summary fills both in with the entity's real name/description, still editable afterward; picking an Endpoint/Operation similarly fills Title from method+path/channel+direction and Summary from its own summary; changing an already-titled step's reference does not clobber its existing Title/Summary; canvas card title is unchanged (`step.title || step.id`); canvas card subtitle shows the step's Summary once filled, falling back to the referenced entity's name (entity-backed kinds) or the owning API's name (API Call/Event) only while Summary is still empty.
