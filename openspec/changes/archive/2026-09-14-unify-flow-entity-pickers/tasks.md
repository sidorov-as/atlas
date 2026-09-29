## 1. Shared lookup item-row component

- [x] 1.1 Extract `SearchResultContent` (currently local to `plugins/flows/frontend/src/components/FlowStepModal.tsx`) into a small shared component (icon + primary text + secondary text), keeping its existing two-line layout and the `SEARCH_RESULT_OPTION_HEIGHT`-style fixed row height it already needs for `Select`'s virtualization.
- [x] 1.2 Add a shared loading-state treatment for a `Select` using this row shape (e.g. a small wrapper or shared props helper) so both the entity lookup and the endpoint/operation lookup show the same visual while a fetch is in flight, instead of an abrupt empty-to-populated change.

## 2. Flow-scoped entity catalog context

- [x] 2.1 Create `FlowEntityCatalogContext` (new file under `plugins/flows/frontend/src/lib/` or `components/`) that, on mount, fetches every `entity_ref`-backed kind (component, resource, api, system, user, group) via the existing `entities.ts` API clients, looping through `Paginated<T>` pages until exhausted (no `pageSize: 100` cap), and exposes `{ itemsByKind, isLoading }`.
- [x] 2.2 Provide `FlowEntityCatalogContext` once in `plugins/flows/frontend/src/pages/FlowFormPage.tsx`, wrapping both its own `<FlowStepModal>` instance and `<FlowCanvasEditor>` (whose own `<FlowStepModal>` instance is a descendant), so both mount points share one fetch per page visit.
- [x] 2.3 Confirm `core/frontend/src/components/RefSelect.tsx` and its other consumers (Flow's "Home system" field, `RelationsTab`'s `TargetRefSelect`, other entity forms' owner/system fields) are untouched and unaffected.

## 3. Unify the entity_ref lookup in FlowStepModal

- [x] 3.1 In `FlowStepModal.tsx`, replace the `entity_ref` field's use of `RefSelect` with a `Select` reading from `FlowEntityCatalogContext` (filtered to the kind matching the selected node type), rendering options through the shared item-row component from Task 1.1.
- [x] 3.2 Wire the context's `isLoading` into this `Select`'s `loading` prop so the field shows the shared loading-state treatment (Task 1.2) instead of silently flashing from empty to populated.

## 4. Unify the query_ref/event_ref lookup in FlowStepModal

- [x] 4.1 Update the `query_ref`/`event_ref` `Select`s' `renderOption` to use the shared item-row component from Task 1.1 (replacing the local `SearchResultContent`/`renderSearchResultOption`), keeping their existing debounced server-search data source unchanged.
- [x] 4.2 Confirm `endpointSearch.loading`/`operationSearch.loading` still drive the shared loading-state treatment from Task 1.2.

## 5. Backend pagination for Endpoint/Operation search

- [x] 5.1 In `plugins/apis/backend/atlas_plugin_apis/api/schemas.py`, add `page: int = 1` and `page_size: int = Field(default=20, le=100)` to `ApiEndpointSearchQuery` and `ApiOperationSearchQuery`, mirroring `EndpointServicesQuery`/`OperationServicesQuery`'s existing fields in the same file.
- [x] 5.2 In `plugins/apis/backend/atlas_plugin_apis/api/views.py`, update `ApiEndpointSearchController.get`/`ApiOperationSearchController.get` to slice the (already deterministically ordered, via each model's `Meta.ordering`) queryset by `page`/`page_size` and return the app-wide `Paginated<T>` response shape instead of a flat list.
- [x] 5.3 Update `plugins/apis/backend/atlas_plugin_apis/tests/test_endpoint_search.py` and `test_operation_search.py` for the new request params and paginated response shape, including a case covering a second page's results.

## 6. Frontend infinite scroll for Endpoint/Operation search

- [x] 6.1 In `plugins/flows/frontend/src/lib/apiSearch.ts`, update `endpointsApi.search`/`operationsApi.search` to accept a `page` parameter and return the new paginated response shape.
- [x] 6.2 In `FlowStepModal.tsx`'s `useEndpointSearch`/`useOperationSearch`, track accumulated `results` across pages plus the latest page's `numPages`; derive `hasMore`; reset accumulated state (and cancel any in-flight request, reusing the existing `cancelled`-flag pattern) whenever the debounced search term changes.
- [x] 6.3 Wire an `onLoadMore` handler (guarded against firing while a request is already in flight or no further page exists) that fetches the next page and appends its results.
- [x] 6.4 Pass `loading={fetching || hasMore}` to the `query_ref`/`event_ref` `Select`s so Gravity UI's built-in end-of-list sentinel row (which triggers `onLoadMore` via `IntersectionObserver` on scroll) renders for as long as further pages remain, and disappears once exhausted.

## 7. Node-title stability for just-added entity-backed steps

- [x] 7.1 In `plugins/flows/frontend/src/components/FlowNodes.tsx`'s `EntityNodeComponent`, add a lookup against `FlowEntityCatalogContext`'s already-fetched data (Task 2.1) as a source ahead of the `refName(entity_ref)` fallback in the title/subtitle resolution chain (`refStatus?.title || clientDetails?.title || refName(entity_ref) || step.id`), so a just-added step's title resolves directly to the catalog title when that data is already loaded, without an intermediate guess.
- [x] 7.2 Confirm the existing `refStatus`-first, `step.id`-last fallback behavior for already-saved/read Flows is unchanged — this task only affects the pre-save, `refStatus`-absent case.

## 8. Verification

- [x] 8.1 Manually verify in the Flow editor: opening "Add step" via the toolbar and via a node's own "+" produce visually identical entity/query/event lookups with no difference in loading behavior.
- [x] 8.2 Manually verify: adding an entity-backed step shows its final catalog title immediately, with no visible flicker to a different guessed title.
- [x] 8.3 Manually verify: opening the query/event lookup with a broad or empty search term, scrolling to the end of the loaded results triggers loading further pages, and the end-of-list loading indicator disappears once every matching result has loaded; typing a new search term discards previously loaded pages.
- [x] 8.4 Run the backend test suite for `plugins/apis/backend` (`test_endpoint_search.py`, `test_operation_search.py`) and the frontend test suite for `plugins/flows/frontend` and `core/frontend` to confirm no regressions in existing Flow editor / RefSelect-consumer / Endpoint-Operation-search tests.
