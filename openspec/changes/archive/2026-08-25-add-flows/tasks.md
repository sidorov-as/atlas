## 1. Backend: model & validation

- [x] 1.1 Add `Flow` model in `apps/catalog/models/flow.py` (`system` FK → System, `on_delete=PROTECT`, required; `name`; `description`; `steps` JSONField; unique-together `system`+`name`) and register it in `apps/catalog/models/__init__.py`
- [x] 1.2 Add and run the migration for the `Flow` table
- [x] 1.3 Add step validation (entity-ref resolution via `refs.py`'s `resolve_ref()`, strict-tree check: each step id targeted by at most one `next_step`/`next_steps` entry, transitions must target an id that exists in the same `steps` array) — reject the save with a clear error on violation
- [x] 1.4 Register `Flow` in `apps/catalog/admin.py`

## 2. Backend: API

- [x] 2.1 Add `FlowSerializer`/schema in `apps/catalog/api/schemas.py` (or equivalent) covering `system`, `name`, `description`, `steps`
- [x] 2.2 Add `FlowViewSet` in `apps/catalog/api/views.py` (list/create/read/update/delete)
- [x] 2.3 Add `system` and `team` (via `system__owner`) filters in `apps/catalog/api/filters.py`
- [x] 2.4 Wire routes in `apps/catalog/api/urls.py`
- [x] 2.5 Add API tests: create/update happy path, missing-system rejection, unresolvable entity_ref rejection, reconverging-branch rejection, dangling-transition-target rejection, system-deletion-blocked-by-flow, system/team filtering

## 3. Frontend: dependencies & layout

- [x] 3.1 Add `@gravity-ui/graph` to `frontend/package.json`
- [x] 3.2 Add `frontend/src/lib/flowLayout.ts` — pure function: `steps[]` → `{ blocks, connections }` for `@gravity-ui/graph`, via a two-pass tree layout (DFS subtree sizing, then depth→x / stacked siblings→y); unit-test it directly (no rendering needed)

## 4. Frontend: Flow diagram component

- [x] 4.1 Add `frontend/src/components/FlowGraph.tsx` — renders `@gravity-ui/graph`'s canvas from the output of `flowLayout.ts`
- [x] 4.2 Add `frontend/src/lib/types.ts` entries for `Flow` and `FlowStep`
- [x] 4.3 Add `flowsApi` client functions in `frontend/src/lib/api.ts` / `entities.ts` (list, get, create, update, delete)

## 5. Frontend: pages

- [x] 5.1 Add `frontend/src/pages/FlowsListPage.tsx` — reuse `FilterBar` (search + System `Select` filter + Team `Select` filter) and `EntityTable`
- [x] 5.2 Add `frontend/src/pages/FlowFormPage.tsx` or fold create/edit into the detail page — JSON editor over `steps` (raw textarea/code editor) with a live `FlowGraph` preview pane, validation errors surfaced from the API
- [x] 5.3 Add `frontend/src/pages/FlowDetailPage.tsx` — `FlowGraph` render, step summaries (markdown via `MarkdownDescription`), edit entry point
- [x] 5.4 Add routes for the above in `App.tsx`

## 6. Frontend: navigation

- [x] 6.1 Add "Flows" entry to `NAV_ITEMS` in `AppShell.tsx` with an appropriate icon

## 7. Verification

- [x] 7.1 Manually create a Flow spanning two systems (home system + a step referencing a component from another system), confirm list/filter/detail/edit all work
- [x] 7.2 Confirm deleting a system with an attached Flow is blocked, and succeeds after the Flow is removed
- [x] 7.3 Confirm diagram matches the mockup goal: left-to-right, divergence-only, live preview updates on JSON edit
