## 1. Scaffold the plugin

- [x] 1.1 Create `plugins/flows/backend/atlas_plugin_flows/` (`__init__.py`, `apps.py`, `pyproject.toml`) as a workspace package, not yet wired into `SELECTED_PLUGINS`.
- [x] 1.2 Add `atlas_plugin_flows/plugin.py` with a `PluginDescriptor` (`id='atlas.flows'`, `django_apps=('atlas_plugin_flows',)`, `entry_point='atlas_plugin_flows.plugin:PLUGIN'`, `requires_plugins={'atlas.standard-catalog': '>=0.1 <1'}`) and an empty `register_runtime()`.
- [x] 1.3 Create `plugins/flows/frontend/` (`@atlas/plugin-flows`, `package.json`, `src/index.ts`) with an empty `defineFrontendPlugin({ id: 'atlas.flows', contributions: [] })`.

## 2. Move the backend model and validation

- [x] 2.1 Move `Flow`, `validate_steps()`, `StepValidationError`, `LABEL_THEMES` from `core/backend/server/apps/catalog/models/flow.py` into `atlas_plugin_flows/models.py`, adding an explicit `class Meta: app_label = 'catalog'` (app-label-preserving move — no new migration, no data touched).
- [x] 2.2 Move `FlowAdmin` from `core/backend/server/apps/catalog/admin.py` into `atlas_plugin_flows/admin.py`.
- [x] 2.3 Verify a fresh-database `migrate` and a migrate-from-the-existing-state both succeed, and `Flow`'s table/rows are untouched.

## 3. Move the backend API surface

- [x] 3.1 Move `FlowIn`/`FlowPatch`/`FlowOut`/`FlowListFilters`/`FlowPath` from `core/backend/server/apps/catalog/api/schemas.py` into `atlas_plugin_flows/api/schemas.py`.
- [x] 3.2 Move `_flow_out`/`_get_flow`/`_flow_create`/`_apply_flow_patch`/`FlowListController`/`FlowDetailController` from `core/backend/server/apps/catalog/api/views.py` into `atlas_plugin_flows/api/views.py`, importing `refs`/`KIND_SYSTEM`/`CatalogEntity` from `atlas_plugin_api` instead of `server.apps.catalog` directly.
- [x] 3.3 Move the `flows/` URL routes from `core/backend/server/apps/catalog/api/urls.py` into `atlas_plugin_flows/api/urls.py`, registered by the plugin at the same `flows/` path.
- [x] 3.4 Move (or add, if none exist yet) Flow's API-level tests alongside the moved code; confirm they pass unmodified against the new location.

## 4. Register Flow's permissions

- [x] 4.1 Register `atlas.flows.flow.read` and `atlas.flows.flow.edit` via `register_permission()` in `atlas_plugin_flows.plugin.register_runtime()`.
- [x] 4.2 Replace `EntityWritePermission.check_create(user, instance.system.owner)` (create) and `EntityWritePermission.check_write`-equivalent calls (update, delete) with `get_policy_evaluator().check(user, 'atlas.flows.flow.edit', instance.system)` in the moved controllers.
- [x] 4.3 Port or add tests: non-member create/update/delete under a foreign System is rejected; member create/update/delete under their own System's Flow succeeds; any authenticated user can read regardless of System ownership.

## 5. Move the frontend

- [x] 5.1 Move `FlowsListPage`/`FlowFormPage`/`FlowDetailPage` from `core/frontend/src/pages/` into `plugins/flows/frontend/src/pages/`.
- [x] 5.2 Move `FlowCanvasEditor`/`FlowGraph`/`FlowNodes`/`FlowEdges`/`FlowTransitionModal`/`FlowStepModal`/`flowSteps.ts` from `core/frontend/src/components/` into `plugins/flows/frontend/src/components/`.
- [x] 5.3 Move `flowLayout.ts`/`flowNodeKind.ts`/`flowDiagramPreferences.ts`/`monacoFlowTheme.ts`/`flowStepSchema.ts` from `core/frontend/src/lib/` into `plugins/flows/frontend/src/lib/` (also moved `flowNodePalette.ts`, a Flow-specific file the task list omitted but which only `FlowNodes.tsx` uses). `FlowStep`/`FlowStepTransition`/`FlowStepLabelTheme` stayed defined in `core/frontend/src/lib/types.ts` instead of moving — `FlowEntity` there needs the same shape independent of whether `atlas.flows` is selected; the plugin's `lib/flowLayout.ts` re-exports them from `frontend/lib/types` for its own internal call sites.
- [x] 5.4 Move each moved file's test (`FlowDetailPage.test.tsx`, `FlowFormPage.test.tsx`, `flowSteps.test.ts`, `flowLayout.test.ts`, etc.) alongside it; confirm they pass unmodified.
- [x] 5.5 Move the four `atlas.core.flows.*` route entries out of `core/frontend/src/plugins/core/routes.ts` into `plugins/flows/frontend/src/routes.ts` (rename ids to `atlas.flows.*`), and the Flows nav item out of `core/frontend/src/plugins/core/navItems.ts` into `plugins/flows/frontend/src/navItems.ts`.
- [x] 5.6 Wire `plugins/flows/frontend/src/index.ts`'s `defineFrontendPlugin` to the moved `routes`/`navItems`; remove the empty placeholder from task 1.3.

## 6. Clean up core

- [x] 6.1 Delete `core/backend/server/apps/catalog/models/flow.py` and confirm no remaining `server.apps.catalog`/`server.apps.catalog.api` module imports it.
- [x] 6.2 Delete the moved page/component/lib files from `core/frontend/src/{pages,components,lib}` and confirm `frontend/src/plugins/core/` no longer imports anything Flow-specific; update its routes.ts comment (the "Flows hasn't been extracted yet" note no longer applies). Also added the missing `core/frontend/package.json` `exports` entries (`FilterBar`, `DocumentationEditor`, `entityRowActions`, `useFillViewportHeight`, `useDebouncedValue`) the moved plugin files need to reach shared core code, and registered the plugin's test path in `core/frontend/vite.config.ts`'s `test.include`.
- [x] 6.3 Run the plugin import-boundary check (`core/backend/server/apps/plugins/tests/test_import_boundaries.py`) and confirm `atlas_plugin_flows` passes with no forbidden imports.

## 7. Wire the plugin into the distribution

- [x] 7.1 Add `atlas_plugin_flows.plugin` to `SELECTED_PLUGINS` (`core/backend/server/settings/selected_plugins.py`) and the corresponding manifest/lock source, as optional (not in `REQUIRED_PLUGINS`).
- [x] 7.2 Add/extend a composition test asserting a distribution without `atlas.flows` composes successfully with no `/flows` route or nav entry present.
- [x] 7.3 Add/extend a composition test asserting `atlas.flows` without `atlas.standard-catalog` fails composition, identifying the unsatisfied dependency.

## 8. Verify

- [x] 8.1 Run the full `flow-management` and `visual-flow-editor` spec-scenario test suites and confirm they pass unmodified. (Backend: 34 flows-plugin tests + full 647-test backend suite green. Frontend: full vitest suite green — 259 passed, 1 pre-existing failure in `TeamsListPage.test.tsx` unrelated to Flow, confirmed present on `main` before this change too.)
- [x] 8.2 Manually exercise: create a Flow, add/edit/delete steps on the canvas, save, reload the detail page — confirm no behavior change from before this extraction. (Verified live via `docker compose -f docker-compose.dev.yml`: list page, preview panel, detail page Overview/Flow/Steps tabs, `FlowGraph` canvas against real seeded data, Add Flow form, `FlowCanvasEditor`/`FlowStepModal` add-step flow with live JSON-rail sync, create → save → reload → step persisted. Also had to add `plugins/flows/backend`/`plugins/flows/frontend` to `docker-compose.dev.yml`'s volumes and both Dockerfiles' `COPY`s — missing there since task 1's scaffolding, caught only by actually booting the stack.)
- [x] 8.3 Confirm `server.apps.catalog` and `frontend/src/plugins/core/` contain zero remaining references to `Flow`. (Only docstring mentions of the historical move remain, matching every other extraction's own docstrings; zero code references.)
