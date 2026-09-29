## 1. Contribution contract

- [x] 1.1 Add `defineFrontendPlugin`, `route`, `navItem`, `entityDetailTab`, `homeWidget`, `routeRef`, `entitySupports` builders as a workspace package.
- [x] 1.2 Add the build-time validator: unique ids, path conflicts, core-reserved paths, unresolved `routeRef`, extension-point cardinality.
- [x] 1.3 Unit-test the validator against synthetic fixture plugins (duplicate id, path conflict, unresolved ref, reserved path) independent of any real page.

## 2. Wrap existing routes

- [x] 2.1 Create `frontend/src/plugins/core/index.ts` declaring every current `App.tsx` route as a `route(...)` contribution.
- [x] 2.2 Convert `App.tsx` to generate `<Routes>` from `installedFrontendPlugins = [corePlugin]`.
- [x] 2.3 Convert `AppShell.tsx`'s `NAV_ITEMS` into `navItem` contributions resolved via `routeRef`; verify sidebar behavior unchanged.

## 3. EntityDetailShell

- [x] 3.1 Build `EntityDetailShell` from `EntityDetailPage.tsx`, adding tab/action/banner contribution rendering with per-contribution error boundaries and shared loading/unavailable/error/permission states.
- [x] 3.2 Convert Resource's detail page (Overview + Relations) to `entityDetailTab` contributions; verify `catalog-web-ui` Resource scenarios.
- [x] 3.3 Convert Component's detail page (Overview, Relations, C4) to contributions, preserving the C4 tab's full-width rendering; verify scenarios.
- [x] 3.4 Convert System's detail page (Overview, Components, Resources, APIs, Docs, Relations, C4 Context, C4 Architecture) to contributions; verify scenarios.
- [x] 3.5 Convert API's detail page (Overview, Relations, Specification) to contributions, preserving the download-before-viewer ordering; verify scenarios.
- [x] 3.6 Convert Team's detail page (Overview, Members, Systems, Components, Resources, APIs) to contributions; verify scenarios.

## 4. Cleanup

- [x] 4.1 Remove now-dead per-page tab-assembly code once every kind is converted.
- [x] 4.2 Add an empty `collection` home-widget extension point on `HomePage.tsx` for later plugins to contribute into.
