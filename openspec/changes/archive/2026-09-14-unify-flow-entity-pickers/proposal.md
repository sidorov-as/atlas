## Why

The Flow "Add Step" modal (`FlowStepModal.tsx`) currently mixes three different picker mechanisms for what authors experience as "the same kind of interaction": a client-prefetched, uncapped-loading-state combobox for `entity_ref` (`RefSelect`), a debounced server-search combobox with a spinner and hand-patched two-line rows for `query_ref`/`event_ref`, and a separate nested modal-in-modal for the Step icon. Each field also refetches its data from scratch on every open, and the modal is mounted twice independently (toolbar "Add step" vs. each node's own "+"), so the same field can feel different depending on which entry point was used. Authors experience this as the picker "looking different every time" and "jittering." A newly-added entity-backed step's node title compounds the effect by briefly showing a slug-derived guess before swapping to the resolved catalog title.

## What Changes

- Unify the visual/interaction shape of the `entity_ref` lookup and the `query_ref`/`event_ref` lookup inside `FlowStepModal`: one shared item-row (icon + primary text + secondary text) and one shared loading-state treatment, even though the two keep different fetch strategies underneath.
- Introduce a Flow-editor-page-scoped data provider (a React Context established once in `FlowFormPage`, the common ancestor of both `FlowStepModal` mount points) that fetches every `entity_ref`-backed list (component/resource/api/system/user/group) fully paginated — looping through all pages — exactly once per Flow editor page visit, instead of each `FlowStepModal` mount independently fetching a single capped page (`pageSize: 100`) on its own. This is new, Flow-scoped code; the shared `core/frontend/src/components/RefSelect.tsx` used elsewhere in the catalog (Flow's own "Home system" field, `RelationsTab`'s `TargetRefSelect`, other entity forms' owner/system fields) is not modified.
- Add offset pagination (`page`/`page_size`, mirroring the existing `EndpointServicesQuery`/`OperationServicesQuery` convention already used elsewhere in `atlas_plugin_apis`) to `/api/apis/endpoints/search/` and `/api/apis/operations/search/`, and load additional pages of the `query_ref`/`event_ref` lookup as an author scrolls near the end of the currently-loaded results, using Gravity UI `Select`'s built-in `onLoadMore`/`loading` infinite-scroll mechanism — instead of silently truncating at the first page with no way to see further matches. **This is a backend change**, scoped to these two search endpoints only (see Impact).
- Fix the node-title flash on a just-added, not-yet-saved entity-backed step (`FlowNodes.tsx`'s `EntityNodeComponent`): the node should settle on one title rather than rendering a slug-derived guess (`refName(entity_ref)`) and then visibly swapping to the resolved catalog title once it loads.
- **Out of scope, explicitly**: the Step icon picker (`IconPickerDialog`) is left as-is, including its trigger button and nested-modal presentation. No backend caching layer (e.g. a JSONB snapshot table) is introduced — investigated and rejected given current data volumes and the cross-plugin cache-invalidation cost it would add for no current performance benefit.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `visual-flow-editor`: "Catalog entity lookup for Flow steps" gains requirements for a consistent lookup UI shape/loading treatment (matching the Endpoint/Operation lookup) and for the just-added-step live preview to resolve without a visible flicker between two different title guesses. "Endpoint/Operation search lookup for API Call/Event steps" gains a requirement to load further matching results as the author scrolls, instead of silently stopping at the first page.
- `api-endpoint-operation-search`: "Cross-API Endpoint search" and "Cross-API Operation search" gain `page`/`page_size` pagination support (request params and a paginated response shape), mirroring the existing `EndpointServicesQuery`/`OperationServicesQuery` pagination convention already used elsewhere in `atlas_plugin_apis`.

## Impact

- Frontend, within `plugins/flows/frontend/src`: `components/FlowStepModal.tsx`, `components/FlowCanvasEditor.tsx`, `components/FlowNodes.tsx`, `pages/FlowFormPage.tsx`, `lib/apiSearch.ts` (new Flow-scoped entity-catalog fetch/context code, plus reworking `apiSearch.ts`'s search clients to page/accumulate results).
- Backend, within `plugins/apis/backend/atlas_plugin_apis`: `api/schemas.py` (`ApiEndpointSearchQuery`/`ApiOperationSearchQuery` gain `page`/`page_size`), `api/views.py` (`ApiEndpointSearchController`/`ApiOperationSearchController` return a paginated response instead of a flat capped list). Verified via repo-wide search that `plugins/flows/frontend/src/lib/apiSearch.ts` is the only frontend consumer of these two search endpoints, so the response-shape change has no other call sites to update.
- No changes to `core/frontend/src/components/RefSelect.tsx`, `core/frontend/src/lib/useAsync.ts`, the ingestion pipeline, or any other backend plugin. No new dependencies, no database migration (the endpoint/operation models' existing `Meta.ordering` already makes offset pagination stable, so no schema change is needed there either).
