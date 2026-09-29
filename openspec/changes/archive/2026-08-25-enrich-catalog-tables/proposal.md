## Why

Entity list tables (Systems/Components/Resources/APIs, plus the owned-entity tables on Team and System detail pages) currently show plain, unpaginated, untagged rows: Type and Lifecycle render as bare text with no visual distinction, tags configured on an entity are invisible outside its detail page, and every list endpoint returns its full unfiltered result set client-side with no paging. As catalogs grow, this makes tables harder to scan and slower to load, and there's no way to narrow a table down by tag.

## What Changes

- Render each entity's **Type** as a colored `Label` badge in list tables, using a static, per-entity-kind color map (Component/Resource/API each keep their own existing fixed `choices`; no new admin UI, no migration).
- Render **Lifecycle** (Component only, its only existing home) as a colored `Label` badge: `production` → success (green), `experimental` → warning (yellow), `deprecated` → unknown (gray). Static mapping, no admin UI.
- Add a **Tags column** to every table that uses the shared `EntityTable` component (the four entity list pages, plus the Team and System detail pages' owned-entity sub-tables), rendering each entity's tags as the same colored `Label`s used on the detail page.
- Add a **tag filter** to those same tables: a multi-select control that narrows rows to entities carrying **any** of the selected tags (OR semantics).
- Add **pagination** to every list endpoint and every `EntityTable` usage, using Gravity UI's `Pagination` component (page number buttons, prev/next, jump-to-page input, items-per-page selector). List endpoints move from returning a bare array to a paginated envelope (items + total count) driven by `page`/`page_size` query params.

## Capabilities

### New Capabilities
(none — this extends existing list/table behavior, it doesn't introduce a new domain capability)

### Modified Capabilities
- `entity-catalog`: list endpoints for ingestible kinds gain `?tags=`, `?page=`, and `?page_size=` query params and return a paginated envelope (items + total) instead of a bare array.
- `catalog-web-ui`: entity list tables (and `EntityTable` usages generally) gain Type/Lifecycle badges, a Tags column, tag filtering, and pagination controls.

## Impact

- **Backend**: `backend/apps/catalog/views.py` list controllers for System/Component/Resource/API (and any other `EntityTable`-backing endpoint, e.g. Group's owned-entities listing if separately paginated) gain `page`/`page_size`/`tags` query-param handling and a paginated response shape. Component/Resource/API lists also accept `system` so System Detail can paginate their owned tables server-side. No new models, no migrations.
- **Frontend**: `frontend/src/components/EntityTable.tsx` gains pagination + tag-filter UI wiring; `frontend/src/lib/entities.ts`'s `fetchList` functions move from returning a raw array to a paginated result; `frontend/src/pages/{Systems,Components,Resources,Apis}ListPage.tsx`, `TeamDetailPage.tsx`, and `SystemDetailPage.tsx` (or wherever `EntityTable` is consumed) update to pass/handle pagination and filter state; new static color-map lookups for Type (per kind) and Lifecycle.
- **Breaking**: the shape of list API responses changes from `T[]` to a paginated envelope — any other consumer of these endpoints (if any exist beyond the frontend) needs to adapt.
