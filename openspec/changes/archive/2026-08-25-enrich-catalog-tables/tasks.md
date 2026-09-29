## 1. Backend: pagination and tag filtering

- [x] 1.1 Add `tags: list[str] = []`, `page: int = 1`, `page_size: int = Field(default=20, le=100)`, and optional `system` to `ListFilters` in `backend/apps/catalog/api/schemas.py`.
- [x] 1.2 Add `filter_by_tags_overlap(queryset, tags)` to `backend/apps/catalog/api/filters.py`, using `queryset.filter(tags__overlap=tags)` when `tags` is non-empty (no-op otherwise).
- [x] 1.3 Update `SystemListController.get`, `ComponentListController.get`, `ResourceListController.get`, and `ApiListController.get` (`backend/apps/catalog/api/views.py`) to apply the new tags filter, paginate the queryset with `django.core.paginator.Paginator(queryset, parsed_query.page_size).page(parsed_query.page)`, and return `dmr.pagination.Paginated[XOut]` instead of `list[XOut]`; Component/Resource/API controllers also apply the `system` filter.
- [x] 1.4 Add/update backend tests: tag filter returns entities matching ANY selected tag (not requiring all), pagination returns the correct slice and total count, `page_size` beyond the cap is rejected or clamped.

## 2. Frontend: shared plumbing

- [x] 2.1 Add a `Paginated<T>` TS type (mirroring the backend envelope: item count, page count, page size, current page's items) to `frontend/src/lib/types.ts`.
- [x] 2.2 Update `ListFilters` and `toQuery` in `frontend/src/lib/entities.ts` to support `tags?: string[]` (serialized as repeated `tags=` params), `page?: number`, and `pageSize?: number`.
- [x] 2.3 Update `systemsApi.list`, `componentsApi.list`, `resourcesApi.list`, and `apisApi.list` (`frontend/src/lib/entities.ts`) to return `Promise<Paginated<T>>` instead of `Promise<T[]>`.
- [x] 2.4 Add `frontend/src/lib/badges.ts` with a `LIFECYCLE_THEME` map (`production`→`success`, `experimental`→`warning`, `deprecated`→`unknown`) and per-kind `COMPONENT_TYPE_THEME`/`RESOURCE_TYPE_THEME`/`API_TYPE_THEME` maps covering each model's existing `TYPE_CHOICES` values.
- [x] 2.5 Add a `MultiSelectFilterConfig` variant to `frontend/src/components/FilterBar.tsx` (multi-value `Select` with `multiple`), rendered alongside the existing single-select `SelectFilterConfig` entries without changing their behavior.
- [x] 2.6 Extract the tag-`Label` rendering used on `EntityDetailPage.tsx:112-117` into a small shared helper/component so table cells and the detail page render tags identically.

## 3. Frontend: entity list pages

- [x] 3.1 Update `frontend/src/components/EntityListPage.tsx`: add `page`/`pageSize` state, reset `page` to 1 whenever `filters` changes, render Gravity UI `<Pagination>` below `EntityTable` using the response's total count, and add a Tags multi-select filter (options from `tagsApi.list()`) alongside the existing Owner filter.
- [x] 3.2 Update `frontend/src/pages/ComponentsListPage.tsx`: render Type and Lifecycle columns as `<Label theme={...}>` badges using the maps from 2.4, and add a Tags column using the helper from 2.6.
- [x] 3.3 Update `frontend/src/pages/ResourcesListPage.tsx`: render the Type column as a `<Label theme={...}>` badge, and add a Tags column.
- [x] 3.4 Update `frontend/src/pages/ApisListPage.tsx`: render the Type column as a `<Label theme={...}>` badge, and add a Tags column.
- [x] 3.5 Update `frontend/src/pages/SystemsListPage.tsx`: add a Tags column (no Type/Lifecycle badges — System has neither field).

## 4. Frontend: owned-entity tables

- [x] 4.1 Update `TeamDetailPage.tsx`'s `OwnedTable` (and its `systemsApi.list`/`componentsApi.list`/`resourcesApi.list`/`apisApi.list` calls) to handle the paginated response shape, track independent page state per section, and render `<Pagination>` under each section's table.
- [x] 4.2 Update `SystemDetailPage.tsx`'s owned-entity tables the same way as 4.1.
- [x] 4.3 Add the Tags column (via the 2.6 helper) to the owned-entity tables in both pages, matching the top-level list pages.

## 5. Verification

- [x] 5.1 Run the backend test suite, including the new/updated tests from 1.4.
- [x] 5.2 Run frontend typecheck (`tsc -b`) and lint (`oxlint`); fix any new warnings.
- [x] 5.3 Manually verify in the running app, light and dark theme: Type/Lifecycle badge colors on Components/Resources/APIs, Tags column and OR-semantics tag filter on all four list pages and on Team/System owned-entity tables, and pagination (page navigation, page-size change, and filter changes resetting to page 1).
