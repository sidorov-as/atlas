## Context

`FlowStepModal.tsx`'s form has a free-text "Title" `TextInput` and a "Summary" `TextArea` for every kind, stored verbatim as `step.title`/`step.summary` — both start empty for a fresh step (or hold whatever an editor last typed for an existing one). Nothing in the modal today reflects the reference an author just picked: selecting a Component, an Endpoint, an Operation, etc. leaves Title/Summary untouched, so the canvas card (`FlowNodes.tsx`) — which shows `step.title || step.id` as its primary line — ends up headlined by a bare step id or a stale/paraphrased title unless the author separately retypes the entity's real name.

`refName(ref)` (`core/frontend/src/lib/types.ts`) is pure string parsing of the `kind:name` ref itself — no fetch. `useEntitySubtype` (`plugins/flows/frontend/src/lib/entitySubtype.ts`) is a genuine fetch, today scoped to Component/API only: it resolves a `component:name`/`api:name` ref's real catalog `spec.type` via a `q`-search-by-name against `componentsApi`/`apisApi` (no name-keyed detail route exists; `.list({q: name})` plus an exact-match filter is the established substitute), caching the result by ref.

The API Call/Event pickers' search results (`endpointsApi.search`/`operationsApi.search`, `apiSearch.ts`) already embed the backend's full `EndpointOut`/`OperationOut` objects, which include a `summary: str` field (`plugins/apis/backend/atlas_plugin_apis/api/schemas.py`) — the frontend's `EndpointSearchResult`/`OperationSearchResult` types simply don't declare it yet.

An earlier draft of this change instead remapped the canvas card's `title`/`subtitle` props (promoting the referenced entity's name to `title`, demoting the author's free text to `subtitle`) and relabeled the modal's "Title" field to "Description". That approach is dropped: it introduced a redundant-looking third field ("Description" sitting right next to the pre-existing "Summary"), and reviewing it surfaced a simpler fix — make the form's own defaults correct, rather than restructure how the card renders them.

## Goals / Non-Goals

**Goals:**
- Picking a reference (entity, Endpoint, or Operation) for a step with no Title/Summary yet fills those fields with the reference's own real name/description, so the card ends up headlined correctly without the author retyping it.
- Prefill never destroys an author's own text — it only fills a field that is currently blank, and only right when the reference is selected/changed.
- Title/Summary stay ordinary, always-editable free text after prefill — no locking, no forced resync if the underlying entity's name/description changes later.
- The card's own second line (subtitle) actually surfaces that prefilled Summary once it exists, instead of continuing to show only the reference's raw identity — otherwise Decision 1-3's prefill fills a field the canvas never reads.

**Non-Goals:**
- No change to canvas card *title*. `title = step.title || step.id` for every kind, exactly as before this change — Decisions 1-3's prefill already makes this show the reference's real name/method+path, so title itself needed no rework. Only *subtitle* sourcing changes for entity-backed and API Call/Event kinds (Decision 4); Step subtitle (`step.summary`) and External subtitle (`step.external_label`) are unchanged.
- No new fetch added for subtitle rendering. Decision 4's subtitle is computed entirely from data already on the step (`step.summary`, `entity_ref`, `query_ref.api`, `event_ref.api`) — the same live-fetch-free principle Decision 2 already established for API Call/Event's own Title/Summary prefill.
- No relabeling of the "Title"/"Summary" fields, and no read-only preview line — both dropped from this change's earlier draft.
- No backend changes. `EndpointOut`/`OperationOut` already return `summary`; only the frontend's read shape needs to catch up. `query_ref`/`event_ref`'s stored shape is unchanged — still just a method/path/channel/direction snapshot, no summary persisted on the step itself.
- No continuous sync: once a field is filled (by prefill or by the author), it is never automatically overwritten again by a later reference change or by the referenced entity's data changing.

## Decisions

### 1. One shared entity_ref detail resolver, generalized from `useEntitySubtype`

`entitySubtype.ts`'s per-ref cache-and-`q`-search pattern is generalized from Component/API-only into a single resolver covering all six entity-backed kinds (Actor→`usersApi`, Team→`groupsApi`, Component→`componentsApi`, Data→`resourcesApi`, API→`apisApi`, System→`systemsApi`), keyed by the ref's `kind:name` prefix exactly like today's `fetchSubtype`. Each kind's `.list({ q: name, pageSize: 100 })` call already returns full `Metadata` (`title`, `description`) per item — `useEntitySubtype`'s existing exact-name-match filter is reused unchanged, just widened to also read `metadata.title`/`metadata.description` off the same matched item, not only `spec.type`.

One cache/fetch layer, not two: today Component/API nodes already pay for this exact fetch (for icon/color); this change makes that same fetch's result carry title/description too, rather than adding a second independent request. `usersApi.list()` returns a bare array (not `Paginated`) unlike the other five — the resolver branches on shape exactly as `RefSelect.tsx`'s existing `useRefItems` already does.

`useEntitySubtype(entityRef)` keeps its existing return contract (`string | undefined`, the subtype). A new `useEntityRefDetails(entityRef)` hook is added alongside it, built on the same cache, returning `{ title: string, description: string } | undefined` — `undefined` while unresolved or when `entityRef` is unset, matching `useEntitySubtype`'s own contract.

**Alternative considered:** have `FlowStepModal.tsx` read the entity's title/description off `RefSelect`'s own internal list fetch instead of a separate resolver. Rejected — `RefSelect` is a generic core component (used well beyond Flows) and doesn't expose its fetched items to its parent; piggybacking on it would mean either changing its public contract for one caller or reaching into its internals. A dedicated resolver mirrors the already-accepted precedent of `useEntitySubtype` paying for its own fetch independent of `RefSelect`'s.

### 2. API Call/Event: Title has no fetch, Summary reads data already returned

Title prefills from data already in memory at selection time — `${queryRef.method} ${queryRef.path}` / `${eventRef.channel} (${eventRef.direction})` — no fetch needed, mirroring how these values are already snapshotted onto `query_ref`/`event_ref` today. Summary prefills from the selected search result's own `endpoint.summary`/`operation.summary` — data the backend already sends in `endpointsApi.search`/`operationsApi.search`'s response (`EndpointOut`/`OperationOut` both carry `summary: str`); only `apiSearch.ts`'s frontend types need to add the field to read it. No backend change.

The summary is read at selection time from the search result already in hand and is not persisted onto `query_ref`/`event_ref` — consistent with the existing non-goal that those refs snapshot only method/path/channel/direction.

### 3. Fill-only-when-empty, no resync

Prefill checks the field's current value at the moment a reference is selected/changed and writes into it only if blank (`''`, after `.trim()`). This applies uniformly: a fresh step with nothing typed yet gets fully prefilled; an author who already typed a Title before picking a reference keeps their own text; swapping an already-referenced step's reference for a different one never clobbers whatever Title/Summary it already holds (which, in practice, usually means the earlier prefill or the author's own edit).

**Alternative considered:** always overwrite Title/Summary on every reference change, keeping them permanently in sync with the current reference. Rejected (explicit user direction) — an author who has customized a step's Title/Summary should never have that silently discarded by picking a different reference.

### 4. Canvas subtitle prefers `step.summary`, falling back to the reference's identity

`FlowNodes.tsx`'s `EntityNodeComponent`/`CallNodeComponent`/`EventNodeComponent` subtitle changes from unconditionally showing the reference's raw identity to preferring `step.summary` — the same field Decision 1-3's prefill already fills with the reference's real description — and falling back to the previous, identity-only subtitle only while `summary` is still blank:

- Entity-backed kinds (Actor/Team/Component/Data/API/System): `step.summary || (entity_ref ? refName(entity_ref) : undefined)`.
- API Call: `step.summary || (query_ref ? refName(query_ref.api) : undefined)` — the *owning API's* name, not the method+path already shown in the title, so the fallback doesn't just repeat the line above it.
- Event: `step.summary || (event_ref ? refName(event_ref.api) : undefined)` — the owning API's name, mirroring API Call.

Title (`step.title || step.id`) is untouched by this decision (Non-Goals, above) — it already surfaces the reference's real name/method+path via Decision 1-3's prefill. Only the second line was left stranded showing stale, always-on identity text by this change's original "canvas unchanged" scope, even after Decision 1-3 gave it somewhere better to point.

No new fetch: every value on the right-hand side of `||` above is already present on the step in memory (`step.summary`, `entity_ref`, `query_ref.api`, `event_ref.api`) — `refName` is pure string parsing, not a network call.

**Alternative considered:** fall back to the previous exact subtitle content for API Call/Event (`${method} ${path}` / `${channel} (${direction})`) instead of the owning API's name. Rejected (explicit user direction) — that text already renders as the title (via prefill) in the common case, so repeating it as the fallback subtitle would just duplicate the line above it; the owning API's name gives the card a second, distinct piece of information instead.

## Risks / Trade-offs

- **[Trade-off]** A prefilled Title/Summary can drift from the referenced entity if that entity's own name/description changes later — there is no re-sync. Accepted: this mirrors the trade-off `query_ref`/`event_ref` already make for their own method/path/channel/direction snapshot, and continuous resync would risk silently discarding an author's edits (Decision 3).
- **[Risk]** `useEntityRefDetails`'s widened `q`-search-by-name resolution can, in principle, match the wrong entity if two catalog entities of the same kind share a name differing only in case — pre-existing risk, unchanged from `useEntitySubtype`'s current behavior (case-insensitive exact match), not introduced by this change.
- **[Trade-off]** A step created before this change (or whose author left Summary blank on purpose) shows the same subtitle it always has (Decision 4's fallback) — its card doesn't gain the new information until someone opens it and either the reference re-triggers prefill or the author types a Summary by hand. Accepted: consistent with this change's no-migration, no-retroactive-effect stance (Migration Plan).

## Migration Plan

No database or API migration: `FlowStep.title`/`summary` keep their exact field names, shapes, and validation, and `query_ref`/`event_ref` are unchanged. Purely a frontend form-default and card-rendering change. Rollback is a plain revert of the affected frontend files. Existing, already-saved steps are entirely unaffected at the data level — prefill only fires when a reference is freshly selected/changed inside the modal, never retroactively — though their *rendered* subtitle does change today, from the old identity-only text to Decision 4's `summary || identity` fallback (which is the identity text again while `summary` is blank, so a never-reopened step's card is visually unchanged).

## Open Questions

(none)
