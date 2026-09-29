## Why

`frontend/src/App.tsx` hard-codes every route as a literal `<Route>` element with a directly imported page component, and each detail page (`SystemDetailPage.tsx`, `ComponentDetailPage.tsx`, etc.) independently assembles its own tabs — there's a shared `EntityDetailPage.tsx` component but no typed contract a plugin could add a tab or route to without editing `App.tsx` directly. `plugin-architecture.md` requires plugins to export immutable declarative contributions (routes, entity-detail tabs, home widgets, nav items) that a build-time composer validates and assembles into the router and a canonical `EntityDetailShell` (ADR 0003, 0005, 0010, 0011, 0022). This has to exist before any UI-owning plugin (C4, APIs, Database Schema) can be extracted, since extraction means "stop editing `App.tsx`, contribute instead."

## What Changes

- Add `@atlas/plugin-api`-equivalent internal TypeScript package (in this monorepo, a workspace package) exporting `defineFrontendPlugin`, and typed contribution builders: `route(...)`, `navItem(...)`, `entityDetailTab(...)`, `homeWidget(...)`, `routeRef(...)`, `entitySupports(...)`.
- Add a build-time contribution validator: unique route/tab/widget/nav ids, no duplicate or core-reserved paths, all `routeRef` references resolve, extension-point cardinality respected (`collection`/`singleton`/`keyed`).
- Add the canonical `EntityDetailShell` component (header with identity/ownership/action contributions, banner/status contributions, tab contributions, shared loading/unavailable/error/permission states) per `plugin-architecture.md:365-380`, wrapping each contribution in its own `ErrorBoundary`.
- **BREAKING (internal)**: convert `App.tsx`'s literal `<Route>` list into a generator that reads an `installedFrontendPlugins` array and builds routes/nav from contributions. In this change, the *only* contributor is a single in-tree "core" plugin module wrapping the existing System/Component/Resource/API/Team/Flow pages and tabs as contributions — proving the mechanism without yet splitting code into separate packages.
- Convert `AppShell.tsx`'s hard-coded sidebar nav items into `navItem` contributions resolved through `routeRef`.
- Convert the existing per-kind detail pages' tab lists (System: Overview/Components/Resources/APIs/Docs/Relations/C4; Component: Overview/Relations/C4; Resource: Overview/Relations; API: Overview/Relations/Specification) into `entityDetailTab` contributions rendered by `EntityDetailShell`.

## Capabilities

### New Capabilities
- `frontend-plugin-contributions`: a plugin module exports an immutable list of typed contributions (route, nav item, entity-detail tab, home widget); the host validates the full set (unique ids, non-conflicting paths, resolved `routeRef`s, correct cardinality) before constructing the router, and never mutates a global registry as an import side effect.
- `entity-detail-shell`: a core-owned canonical shell renders any entity kind's detail page from header/banner/tab contributions plus shared loading/unavailable/error/permission states; each contribution is isolated in its own error boundary so one failing tab or widget cannot crash the shell.

## Impact

- **Frontend**: `frontend/src/App.tsx` becomes a thin generator over `installedFrontendPlugins`; `AppShell.tsx` nav becomes contribution-driven; `EntityDetailPage.tsx` is replaced/absorbed by the new `EntityDetailShell`; every existing `*DetailPage.tsx` becomes a set of contribution declarations plus the same tab components they already render.
- **Behavior preserved**: every scenario in `catalog-web-ui` (list pages, detail-page tabs, nav shell, right-rail links, preview panel, etc.) must keep passing against the new composition mechanism — this change moves *how* pages are assembled, not what they show.
- **Dependents**: `extract-standard-catalog-plugin`, `extract-apis-plugin`, `extract-c4-plugin`, `introduce-database-schema-facet` each become real consumers of this contract, contributing from separately built packages instead of the one in-tree "core" module this change introduces.
